"""Meta Cloud API voice-message and call-transcript inbox."""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

import inbox
from call_transcripts import call_events, download_transcript, parse_transcript, translation_chunks
from services import LANGUAGES, transcribe_audio, translate_text

router = APIRouter()
logger = logging.getLogger(__name__)
REQUIRED = ('WHATSAPP_ACCESS_TOKEN', 'WHATSAPP_APP_SECRET', 'WHATSAPP_VERIFY_TOKEN',
            'WHATSAPP_PHONE_NUMBER_ID', 'WHATSAPP_WABA_ID', 'WHATSAPP_GRAPH_VERSION')
MAX_MEDIA_BYTES = 16_000_000
MAX_WEBHOOK_BYTES = 1_000_000
AUDIO_EXTENSIONS = {'audio/ogg': '.ogg', 'audio/opus': '.opus', 'audio/mpeg': '.mp3',
                    'audio/mp4': '.m4a', 'audio/aac': '.aac', 'audio/amr': '.amr',
                    'audio/wav': '.wav', 'audio/x-wav': '.wav'}


def settings() -> dict:
    missing = [name for name in REQUIRED if not os.getenv(name, '').strip()]
    version = os.getenv('WHATSAPP_GRAPH_VERSION', '')
    target = os.getenv('WHATSAPP_TARGET_LANGUAGE', 'fr')
    invalid = []
    if version and not re.fullmatch(r'v\d+\.\d+', version):
        invalid.append('WHATSAPP_GRAPH_VERSION')
    for name in ('WHATSAPP_PHONE_NUMBER_ID', 'WHATSAPP_WABA_ID'):
        value = os.getenv(name, '')
        if value and not re.fullmatch(r'[0-9]+', value):
            invalid.append(name)
    if target not in LANGUAGES:
        invalid.append('WHATSAPP_TARGET_LANGUAGE')
    return {'configured': not missing and not invalid, 'missing': missing, 'invalid': invalid,
            'target_language': target, 'retention_hours': 24,
            'supported_events': ['audio', 'call_transcription_available']}


def require_settings():
    if not settings()['configured']:
        raise HTTPException(503, 'Complete the WhatsApp settings in the backend .env file.')


@router.get('/webhooks/whatsapp', response_class=PlainTextResponse)
async def verify(request: Request):
    expected = os.getenv('WHATSAPP_VERIFY_TOKEN', '')
    params = request.query_params
    if (not expected or params.get('hub.mode') != 'subscribe'
            or not hmac.compare_digest(params.get('hub.verify_token', '').encode(), expected.encode())):
        raise HTTPException(403, 'Webhook verification failed.')
    challenge = params.get('hub.challenge', '')
    if not challenge or len(challenge) > 256:
        raise HTTPException(400, 'Missing or invalid challenge.')
    return challenge


def audio_events(payload: dict) -> list[dict]:
    """Filter by WABA and phone ID; signed events can still target another number."""
    events = []
    if payload.get('object') != 'whatsapp_business_account':
        return events
    for entry in payload.get('entry', []):
        if entry.get('id') != os.getenv('WHATSAPP_WABA_ID'):
            continue
        for change in entry.get('changes', []):
            if change.get('field') != 'messages':
                continue
            value = change.get('value', {})
            if value.get('metadata', {}).get('phone_number_id') != os.getenv('WHATSAPP_PHONE_NUMBER_ID'):
                continue
            for message in value.get('messages', []):
                if message.get('type') != 'audio':
                    continue
                message_id, media_id, sender = message.get('id'), message.get('audio', {}).get('id'), message.get('from')
                if (not isinstance(message_id, str) or not 1 <= len(message_id) <= 512
                        or not isinstance(media_id, str) or not re.fullmatch(r'[0-9]{1,100}', media_id)
                        or not isinstance(sender, str) or not re.fullmatch(r'[0-9]{5,20}', sender)):
                    continue
                allowed = {v.strip() for v in os.getenv('WHATSAPP_ALLOWED_SENDERS', '').split(',') if v.strip()}
                if allowed and sender not in allowed:
                    continue
                # Don't resurrect old messages after the deduplication window.
                timestamp = message.get('timestamp')
                if timestamp is not None:
                    try:
                        age = time.time() - int(timestamp)
                    except (ValueError, TypeError):
                        continue
                    if age > inbox.RETENTION_SECONDS or age < -300:
                        continue
                events.append({'id': message_id, 'media_id': media_id, 'sender': sender})
    return events


@router.post('/webhooks/whatsapp')
async def receive(request: Request):
    require_settings()
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_WEBHOOK_BYTES:
            raise HTTPException(413, 'Webhook body too large.')
    expected = 'sha256=' + hmac.new(os.environ['WHATSAPP_APP_SECRET'].encode(), raw, hashlib.sha256).hexdigest()
    actual = request.headers.get('x-hub-signature-256', '')
    if not hmac.compare_digest(expected.encode(), actual.encode()):
        raise HTTPException(403, 'Invalid webhook signature.')
    try:
        payload = json.loads(raw)
        events = audio_events(payload) + call_events(payload)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, 'Invalid webhook payload.') from None
    # The SQLite transaction commits BEFORE acknowledgement. Slow media/model
    # work is handled by the worker, including recovery after a server restart.
    count = inbox.enqueue(events, settings()['target_language'])
    return {'received': True, 'queued': count}


async def download_audio(media_id: str, directory: Path) -> Path:
    token = os.environ['WHATSAPP_ACCESS_TOKEN']
    version = os.environ['WHATSAPP_GRAPH_VERSION']
    headers = {'Authorization': f'Bearer {token}'}
    async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
        response = await client.get(f'https://graph.facebook.com/{version}/{media_id}',
            params={'phone_number_id': os.environ['WHATSAPP_PHONE_NUMBER_ID']}, headers=headers)
        response.raise_for_status()
        metadata = response.json()
        url = urlparse(metadata['url'])
        hostname = url.hostname or ''
        if (url.scheme != 'https' or url.username or url.password or url.port not in (None, 443)
                or not (hostname == 'lookaside.fbsbx.com' or hostname.endswith('.fbcdn.net'))):
            raise HTTPException(502, 'Meta returned an unexpected media address.')
        mime = metadata.get('mime_type', '').split(';')[0].strip().lower()
        extension = AUDIO_EXTENSIONS.get(mime)
        if extension is None:
            raise HTTPException(415, 'This WhatsApp audio format is not supported.')
        if int(metadata.get('file_size', 0)) > MAX_MEDIA_BYTES:
            raise HTTPException(413, 'WhatsApp audio must be under 16 MB.')
        path = directory / f'audio{extension}'
        size = 0
        digest = hashlib.sha256()
        async with client.stream('GET', metadata['url'], headers=headers) as media:
            media.raise_for_status()
            with path.open('wb') as output:
                async for chunk in media.aiter_bytes(64 * 1024):
                    size += len(chunk)
                    if size > MAX_MEDIA_BYTES:
                        raise HTTPException(413, 'WhatsApp audio must be under 16 MB.')
                    digest.update(chunk)
                    output.write(chunk)
        if not size:
            raise HTTPException(422, 'The WhatsApp audio file is empty.')
        expected_hash = metadata.get('sha256')
        valid_hashes = (digest.hexdigest(), base64.b64encode(digest.digest()).decode())
        if expected_hash and expected_hash not in valid_hashes:
            raise HTTPException(502, 'The WhatsApp audio download was incomplete. Retry the message.')
        return path


async def process_once() -> bool:
    message = inbox.claim()
    if not message:
        return False
    transcript = message['transcript']
    try:
        is_call = message['kind'] == 'call_transcript'
        async with asyncio.timeout(600 if is_call else 240):
            if not transcript:
                if is_call:
                    if not inbox.checkpoint(message, 'fetching_transcript'):
                        return True
                    data = await download_transcript(message['media_id'], message['media_sha256'])
                    if not inbox.checkpoint(message, 'parsing_transcript'):
                        return True
                    transcript, details = parse_transcript(data)
                    if not inbox.checkpoint(message, 'translating', transcript=transcript, details=details):
                        return True
                else:
                    with TemporaryDirectory(prefix='voice-whatsapp-') as directory:
                        path = await download_audio(message['media_id'], Path(directory))
                        transcript = await transcribe_audio(str(path))
            if not inbox.checkpoint(message, 'translating', transcript=transcript):
                return True
            chunks = translation_chunks(transcript) if is_call else [transcript]
            translated = [await translate_text(chunk, message['target']) for chunk in chunks]
            translation = '\n'.join(translated)
        inbox.finish(message, status='completed', transcript=transcript, translation=translation)
    except HTTPException as exc:
        inbox.finish(message, status='partial' if transcript else 'failed', transcript=transcript,
                     error=str(exc.detail), retry=exc.status_code == 429 or exc.status_code >= 500)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        inbox.finish(message, status='partial' if transcript else 'failed', transcript=transcript,
                     error='Meta could not provide this media. Check token, permissions and media availability, then retry.',
                     retry=code in (408, 429) or code >= 500)
    except (httpx.HTTPError, TimeoutError):
        inbox.finish(message, status='partial' if transcript else 'failed', transcript=transcript,
                     error='Could not process this message. Check provider access and retry.', retry=True)
    except Exception:
        # Do not record provider responses, media URLs, tokens or voice content.
        logger.warning('WhatsApp processing failed; private details omitted.')
        inbox.finish(message, status='partial' if transcript else 'failed', transcript=transcript,
                     error='Message processing failed. Check backend settings and retry.')
    return True


async def worker():
    next_cleanup = 0
    while True:
        try:
            if time.time() >= next_cleanup:
                inbox.expire_results()
                next_cleanup = time.time() + 60
            if not settings()['configured'] or not await process_once():
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning('WhatsApp inbox worker unavailable; retrying.')
            await asyncio.sleep(5)


@router.get('/api/whatsapp/messages')
async def messages():
    return {'messages': inbox.list_messages(), 'whatsapp': settings()}


class MessageAction(BaseModel):
    id: str = Field(min_length=1, max_length=512)


@router.post('/api/whatsapp/retry')
async def retry(action: MessageAction):
    require_settings()
    inbox.retry_message(action.id)
    return {'success': True}


@router.post('/api/whatsapp/delete')
async def delete(action: MessageAction):
    inbox.delete_message(action.id)
    return {'success': True}
