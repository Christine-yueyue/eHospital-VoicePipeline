"""Meta Calling API transcript events and JSON documents (no audio transcription).

Contract: https://developers.facebook.com/documentation/business-messaging/whatsapp/calling/call-transcription/
"""

import base64
import hashlib
import json
import math
import os
import re
import time
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

import inbox

MAX_DOCUMENT_BYTES = 8_000_000
MAX_TRANSCRIPT_CHARS = 100_000
MAX_SEGMENTS = 5000


def call_events(payload: dict) -> list[dict]:
    events = []
    if payload.get('object') != 'whatsapp_business_account':
        return events
    allowed = {s.strip() for s in os.getenv('WHATSAPP_ALLOWED_SENDERS', '').split(',') if s.strip()}
    for entry in payload.get('entry', []):
        if entry.get('id') != os.getenv('WHATSAPP_WABA_ID'):
            continue
        for change in entry.get('changes', []):
            if change.get('field') != 'calls':
                continue
            value = change.get('value', {})
            if value.get('metadata', {}).get('phone_number_id') != os.getenv('WHATSAPP_PHONE_NUMBER_ID'):
                continue
            for call in value.get('calls', []):
                if not isinstance(call, dict) or call.get('event') != 'call_transcription_available':
                    continue
                call_id = call.get('id')
                transcript = call.get('call_transcript')
                document = transcript.get('document') if isinstance(transcript, dict) else None
                if not isinstance(document, dict):
                    continue
                media_id, digest = document.get('id'), document.get('sha256')
                # A phone number can be absent when the user has adopted a username.
                identities = [call.get(k) for k in ('from', 'from_user_id', 'from_parent_user_id')]
                identities = [v for v in identities if isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9._-]{5,128}', v)]
                if (not isinstance(call_id, str) or not re.fullmatch(r'wacid\.[A-Za-z0-9._=+/-]{1,480}', call_id)
                        or not isinstance(media_id, str) or not re.fullmatch(r'[0-9]{1,100}', media_id)
                        or document.get('mime_type') != 'application/json'
                        or not isinstance(digest, str) or not valid_digest(digest)
                        or not identities or (allowed and not allowed.intersection(identities))):
                    continue
                try:
                    timestamp = int(call['timestamp'])
                except (KeyError, TypeError, ValueError):
                    continue
                if not -300 <= time.time() - timestamp <= inbox.RETENTION_SECONDS:
                    continue
                # One result per call, including across Meta retries/reissued media IDs.
                # Never persist the short-lived URL or raw webhook.
                events.append({'id': f'call:{call_id}', 'kind': 'call_transcript',
                               'call_id': call_id, 'media_id': media_id,
                               'media_sha256': digest, 'sender': identities[0],
                               'event_at': timestamp})
    return events


def valid_digest(value: str) -> bool:
    try:
        return len(value) == 44 and len(base64.b64decode(value, validate=True)) == 32
    except ValueError:
        return False


def trusted_media_url(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        url = urlparse(value)
        host = url.hostname or ''
        return (url.scheme == 'https' and not url.username and not url.password
                and url.port in (None, 443) and not url.fragment
                and (host == 'lookaside.fbsbx.com' or host.endswith('.fbcdn.net')))
    except ValueError:
        return False


async def download_transcript(media_id: str, expected_hash: str) -> bytes:
    """Resolve a fresh authenticated URL on every attempt, then check the signed hash."""
    headers = {'Authorization': f"Bearer {os.environ['WHATSAPP_ACCESS_TOKEN']}"}
    version = os.environ['WHATSAPP_GRAPH_VERSION']
    async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
        response = await client.get(f'https://graph.facebook.com/{version}/{media_id}',
                                   params={'phone_number_id': os.environ['WHATSAPP_PHONE_NUMBER_ID']},
                                   headers=headers)
        response.raise_for_status()
        try:
            metadata = response.json()
            url = metadata['url']
            mime = metadata['mime_type'].split(';')[0].strip().lower()
            size = int(metadata.get('file_size', 0))
        except (KeyError, ValueError, TypeError, AttributeError):
            raise HTTPException(502, 'Meta returned invalid transcript media metadata.') from None
        if not trusted_media_url(url):
            raise HTTPException(502, 'Meta returned an unexpected transcript address.')
        if mime != 'application/json':
            raise HTTPException(415, 'Meta call transcripts must be JSON documents.')
        if size > MAX_DOCUMENT_BYTES:
            raise HTTPException(413, 'The Meta transcript document is too large.')
        data = bytearray()
        async with client.stream('GET', url, headers=headers) as media:
            media.raise_for_status()
            async for chunk in media.aiter_bytes(64 * 1024):
                data.extend(chunk)
                if len(data) > MAX_DOCUMENT_BYTES:
                    raise HTTPException(413, 'The Meta transcript document is too large.')
        if not data:
            raise HTTPException(422, 'Meta returned an empty transcript document.')
        digest = hashlib.sha256(data)
        if base64.b64encode(digest.digest()).decode() != expected_hash:
            raise HTTPException(502, 'The Meta transcript failed its integrity check. Retry the call.')
        if metadata.get('sha256') and metadata['sha256'] not in (
                expected_hash, digest.hexdigest()):
            raise HTTPException(502, 'The Meta transcript metadata failed its integrity check.')
        return bytes(data)


def number(value, *, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0 or (maximum is not None and value > maximum)):
        raise ValueError('Invalid numeric metadata')
    return value


def parse_transcript(data: bytes) -> tuple[str, dict]:
    """Parse documented transcript.text and speaker segments; never flatten arbitrary JSON."""
    if len(data) > MAX_DOCUMENT_BYTES:
        raise HTTPException(413, 'The Meta transcript document is too large.')
    try:
        document = json.loads(data)
        transcript = document['transcript']
        text = transcript.get('text', '')
        if not isinstance(text, str):
            raise ValueError('Invalid text')
        raw_segments = transcript.get('segments', [])
        if not isinstance(raw_segments, list) or len(raw_segments) > MAX_SEGMENTS:
            raise ValueError('Invalid segments')
        segments = []
        total = 0
        for segment in raw_segments:
            content = segment['text']
            if not isinstance(content, str):
                raise ValueError('Invalid segment text')
            total += len(content)
            if total > MAX_TRANSCRIPT_CHARS:
                raise HTTPException(413, 'The call transcript is too long to translate.')
            speaker = segment.get('speaker')
            channel = segment.get('channel')
            if speaker not in ('Business', 'Customer'):
                if type(channel) is not int or channel not in (0, 1):
                    raise ValueError('Missing speaker')
                speaker = ('Business', 'Customer')[channel]
            start, end = number(segment['start']), number(segment['end'])
            if end < start:
                raise ValueError('Invalid segment interval')
            segments.append({'speaker': speaker, 'start': start, 'end': end, 'text': content.strip()})
        text = text.strip() or '\n'.join(f"[{s['speaker']}] {s['text']}" for s in segments if s['text'])
        if not text:
            raise HTTPException(422, 'Meta returned no speech. The call may be silent or its language unsupported.')
        if len(text) > MAX_TRANSCRIPT_CHARS:
            raise HTTPException(413, 'The call transcript is too long to translate.')
        language = transcript.get('language', '')
        if not isinstance(language, str) or (language and not re.fullmatch(r'[A-Za-z-]{2,20}', language)):
            raise ValueError('Invalid language')
        details = {'language': language, 'segments': segments}
        for key in ('duration', 'confidence'):
            if key in transcript:
                details[key] = number(transcript[key], maximum=1 if key == 'confidence' else None)
        return text, details
    except (KeyError, ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise HTTPException(422, 'Meta returned an invalid transcript JSON document.') from None


def translation_chunks(text: str, limit=6000) -> list[str]:
    """Bound each translation request, preferring speaker/line/word boundaries."""
    chunks = []
    while len(text) > limit:
        end = max(text.rfind('\n', limit // 2, limit), text.rfind(' [', limit // 2, limit))
        if end < 0:
            end = text.rfind(' ', limit // 2, limit)
        if end < 0:
            end = limit
        chunks.append(text[:end])
        text = text[end:]
    if text:
        chunks.append(text)
    return chunks
