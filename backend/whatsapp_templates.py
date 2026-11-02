"""Verify the sending account and approved template without sending a message."""

import os
import re

import httpx
from fastapi import HTTPException


def check_meta_response(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        payload = response.json()
    except ValueError:
        payload = None
    error = payload.get('error') if isinstance(payload, dict) else None
    code = error.get('code') if isinstance(error, dict) else None
    if type(code) is not int:
        code = None
    # Do not expose provider messages: they can contain credentials or numbers.
    messages = {
        190: 'Meta rejected WHATSAPP_ACCESS_TOKEN. Update the expired or invalid token and restart FastAPI.',
        10: 'Meta denied access. Check the token permissions and its access to the sending WhatsApp account.',
        200: 'Meta denied access. Check the token permissions and its access to the sending WhatsApp account.',
        131030: 'Meta does not allow this test recipient. Add and verify the recipient in WhatsApp API Setup.',
        132001: 'Meta could not find this template in the sending account for the requested language.',
        132000: 'The template parameter count does not match the approved template. Create a fresh draft.',
        132012: 'The template parameter format does not match the approved template. Create a fresh draft.',
        132015: 'Meta has paused this template. Check its status in WhatsApp Manager.',
        132016: 'Meta has disabled this template. Choose an active approved template.',
        131042: 'Meta reported a billing or payment eligibility problem. Check WhatsApp account payment settings.',
        131031: 'Meta has restricted this WhatsApp account. Check its status in WhatsApp Manager.',
    }
    message = messages.get(code)
    if not message:
        message = ('Meta denied access. Check the token permissions for the sending WhatsApp account.'
                   if response.status_code == 403 else
                   'Meta rejected the request. Check the sending account and template in WhatsApp Manager.')
    suffix = f' (Meta code {code}.)' if code is not None else f' (HTTP {response.status_code}.)'
    raise HTTPException(502, message + suffix)


async def verify_template(language: str) -> dict:
    """Return a supported, approved template from the actual sending account."""
    settings = {key: os.getenv(key, '').strip() for key in (
        'WHATSAPP_ACCESS_TOKEN', 'WHATSAPP_PHONE_NUMBER_ID', 'WHATSAPP_WABA_ID',
        'WHATSAPP_GRAPH_VERSION', 'WHATSAPP_FOLLOWUP_TEMPLATE_NAME')}
    if not all(settings.values()):
        raise HTTPException(503, 'Configure the WhatsApp token, sending phone, WABA, Graph version, and template name.')
    name = settings['WHATSAPP_FOLLOWUP_TEMPLATE_NAME']
    if not re.fullmatch(r'[a-z0-9_]{1,512}', name):
        raise HTTPException(503, 'Configure a valid WHATSAPP_FOLLOWUP_TEMPLATE_NAME in backend/.env.')
    if language not in {'en', 'fr'}:
        raise HTTPException(400, 'Choose English or French as the contact language.')
    base = f"https://graph.facebook.com/{settings['WHATSAPP_GRAPH_VERSION']}"
    headers = {'Authorization': f"Bearer {settings['WHATSAPP_ACCESS_TOKEN']}"}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            # Verify membership instead of assuming a configured WABA owns the phone.
            phone_params = {'fields': 'id', 'limit': 100}
            found_phone = False
            while True:
                response = await client.get(
                    f"{base}/{settings['WHATSAPP_WABA_ID']}/phone_numbers",
                    params=phone_params, headers=headers)
                check_meta_response(response)
                page = response.json()
                if any(item.get('id') == settings['WHATSAPP_PHONE_NUMBER_ID'] for item in page['data']):
                    found_phone = True
                    break
                paging = page.get('paging', {})
                after = paging.get('cursors', {}).get('after')
                if not paging.get('next') or not after or after == phone_params.get('after'):
                    break
                phone_params['after'] = after
            if not found_phone:
                raise HTTPException(503,
                    'WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_WABA_ID belong to different accounts. '
                    'Select the sending phone and template from the same WhatsApp account.')
            response = await client.get(
                f"{base}/{settings['WHATSAPP_WABA_ID']}/message_templates",
                params={'name': name, 'fields': 'name,status,language,components', 'limit': 100},
                headers=headers)
            check_meta_response(response)
            templates = response.json()['data']
    except httpx.RequestError:
        raise HTTPException(503, 'Could not verify the WhatsApp template with Meta. Try creating the draft again.') from None
    except (ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(502, 'Meta returned an unreadable template configuration. Try again.') from None
    matches = [item for item in templates if item.get('name') == name and item.get('language') == language]
    if not matches:
        raise HTTPException(503,
            f'Template "{name}" in language "{language}" was not found in the sending WhatsApp account. '
            'A template approved in another account cannot be sent by this phone. '
            'Select the matching account, or create and approve the template in the sending account.')
    template = matches[0]
    if template.get('status') != 'APPROVED':
        raise HTTPException(503, f'Template "{name}" is not approved for language "{language}". Check WhatsApp Manager.')
    components = template.get('components', [])
    bodies = [item for item in components if item.get('type') == 'BODY']
    if len(bodies) != 1:
        raise HTTPException(503, 'The follow-up template must have one text body.')
    body = bodies[0].get('text', '')
    parameters = re.findall(r'\{\{\s*([^{}]+?)\s*\}\}', body)
    if not body or parameters not in ([], ['1']):
        raise HTTPException(503, 'Use a follow-up template with no variables or one body variable {{1}} for the contact name.')
    text_parts = []
    for item in components:
        kind = item.get('type')
        text = item.get('text', '')
        if (kind not in {'HEADER', 'BODY', 'FOOTER'}
                or (kind == 'HEADER' and item.get('format') != 'TEXT')
                or (kind != 'BODY' and '{{' in text)):
            raise HTTPException(503, 'This assistant supports text templates without buttons or media, with at most one contact-name body variable.')
        if text:
            text_parts.append(text)
    return {'name': name, 'language': language, 'body': body,
            'parameter_count': len(parameters), 'preview': '\n\n'.join(text_parts)}


def template_payload(template: dict, contact_name: str) -> dict:
    result = {'name': template['name'], 'language': {'code': template['language']}}
    if template['parameter_count']:
        result['components'] = [{'type': 'body', 'parameters': [
            {'type': 'text', 'text': contact_name.split()[0]}]}]
    return result


def template_preview(template: dict, contact_name: str) -> str:
    return re.sub(r'\{\{\s*1\s*\}\}', lambda _match: contact_name.split()[0], template['preview'])
