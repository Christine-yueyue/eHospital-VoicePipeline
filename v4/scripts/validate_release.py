"""Capture local verification evidence. Does not call real external providers.

Run with v4/backend/.venv/bin/python v4/scripts/validate_release.py.
Flutter/Xcode need their normal local cache permissions. Evidence excludes .env.
"""
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STAMP = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT = ROOT / 'docs' / 'evidence' / STAMP
OUT.mkdir(parents=True, exist_ok=False)
SKIP = {'.venv', '.env', 'data', 'build', '.dart_tool', '.git', '__pycache__',
        '.pytest_cache', 'ephemeral', '.symlinks', 'Pods', 'docs'}
SUFFIXES = {'.py', '.dart', '.yaml', '.lock', '.plist', '.pbxproj', '.xcconfig', '.txt'}


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()
            and not any(part in SKIP for part in p.relative_to(root).parts)
            and (p.suffix in SUFFIXES or p.name == '.env.example')
            and p.name not in {'Generated.xcconfig'}}


v3_before = manifest(ROOT.parent / 'v3')
source_before = manifest(ROOT)
(OUT / 'source-manifest.json').write_text(json.dumps(source_before, indent=2) + '\n')
flutter = shutil.which('flutter') or str(Path.home() / 'Documents/flutter/bin/flutter')
records = []


def run(name, command, cwd):
    start = dt.datetime.now(dt.timezone.utc).isoformat()
    tick = time.monotonic()
    try:
        with (OUT / f'{name}.log').open('w') as log:
            completed = subprocess.run(command, cwd=cwd, stdout=log,
                                       stderr=subprocess.STDOUT, timeout=600)
        code = completed.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        code = -1
        with (OUT / f'{name}.log').open('a') as log:
            log.write(f'\nVerification runner: {type(exc).__name__}\n')
    records.append({'name': name, 'command': command, 'cwd': str(cwd.relative_to(ROOT)),
                    'started_utc': start, 'duration_seconds': round(time.monotonic() - tick, 2),
                    'exit_code': code, 'log': f'{name}.log'})
    print(f'{name}: exit={code}, duration={records[-1]["duration_seconds"]}s', flush=True)
    (OUT / 'run.json').write_text(json.dumps(records, indent=2) + '\n')


environment = {'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
               'platform': platform.platform(), 'machine': platform.machine(),
               'python': sys.version, 'packages': {name: importlib.metadata.version(name)
               for name in ['fastapi', 'starlette', 'httpx', 'openai', 'pytest', 'uvicorn']}}
(OUT / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
run('toolchain', [flutter, '--version'], ROOT / 'frontend')
run('xcode', ['xcodebuild', '-version'], ROOT / 'frontend')
run('ffmpeg', ['ffmpeg', '-version'], ROOT / 'backend')
run('backend-tests', [sys.executable, '-m', 'pytest', '-q',
                     f'--junitxml={OUT / "backend-junit.xml"}'], ROOT / 'backend')
run('flutter-analyze', [flutter, 'analyze', '--no-pub'], ROOT / 'frontend')
run('flutter-tests', [flutter, 'test', '--no-pub', '--machine'], ROOT / 'frontend')
run('ios-build', [flutter, 'build', 'ios', '--simulator', '--debug', '--no-pub'], ROOT / 'frontend')
preservation = {'v3_files_checked': len(v3_before),
                'v3_unchanged': v3_before == manifest(ROOT.parent / 'v3'),
                'v4_source_unchanged': source_before == manifest(ROOT)}
(OUT / 'preservation.json').write_text(json.dumps(preservation, indent=2) + '\n')
print(f'Evidence: {OUT}', flush=True)
print(json.dumps(preservation), flush=True)
sys.exit(0 if all(r['exit_code'] == 0 for r in records) and all(
    preservation[k] for k in ('v3_unchanged', 'v4_source_unchanged')) else 1)
