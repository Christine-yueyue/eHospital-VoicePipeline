"""Create private v4 settings without overwriting or modifying v3."""

import argparse
import os
import secrets
from pathlib import Path

from dotenv import dotenv_values

parser = argparse.ArgumentParser()
parser.add_argument('--reuse-v3-settings', action='store_true', help='Reuse v3 provider settings; generate new app and webhook verification tokens')
args = parser.parse_args()
version_root = Path(__file__).resolve().parents[1]
destination = version_root / 'backend/.env'
if destination.exists():
    print('v4/backend/.env already exists; no changes made.')
    raise SystemExit(0)

values = {
    'APP_ACCESS_TOKEN': secrets.token_urlsafe(32),
    'WHATSAPP_VERIFY_TOKEN': secrets.token_urlsafe(32),
}
if args.reuse_v3_settings:
    original = dotenv_values(version_root.parent / 'v3/backend/.env', interpolate=False)
    for name in ('OPENAI_API_KEY', 'TRANSCRIPTION_MODEL', 'TRANSLATION_MODEL',
                 'REALTIME_TRANSLATION_MODEL', 'REALTIME_TRANSCRIPTION_SESSION_MODEL',
                 'REALTIME_TRANSCRIPTION_MODEL', 'WHATSAPP_ACCESS_TOKEN', 'WHATSAPP_APP_SECRET',
                 'WHATSAPP_PHONE_NUMBER_ID', 'WHATSAPP_WABA_ID', 'WHATSAPP_GRAPH_VERSION',
                 'WHATSAPP_TARGET_LANGUAGE', 'WHATSAPP_ALLOWED_SENDERS'):
        if original.get(name):
            values[name] = original[name]

lines = []
for line in (version_root / 'backend/.env.example').read_text().splitlines():
    name = line.split('=', 1)[0]
    if name in values:
        # Double-quoted dotenv strings preserve special characters safely.
        value = values[name].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        line = f'{name}="{value}"'
    lines.append(line)
descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, 'w') as output:
    output.write('\n'.join(lines) + '\n')
print('Created private v4/backend/.env with new app and verify tokens. No secrets printed; v3 unchanged.')
