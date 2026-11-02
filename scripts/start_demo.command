#!/bin/bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
flutter_bin="$(command -v flutter || true)"
if [ -z "$flutter_bin" ] && [ -x "$project_dir/../../flutter/bin/flutter" ]; then
  flutter_bin="$project_dir/../../flutter/bin/flutter"
fi
if [ ! -x "$project_dir/backend/.venv/bin/python" ] || [ -z "$flutter_bin" ]; then
  echo "Missing backend Python environment or Flutter. See README.md for setup."
  exit 1
fi

for port in 8003 5174; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Stop the previous demo before starting again."
    exit 1
  fi
done

log_dir="$(mktemp -d "${TMPDIR:-/tmp}/voice-demo.XXXXXX")"
backend_pid=''
frontend_pid=''
cleanup() {
  for service_pid in "$backend_pid" "$frontend_pid"; do
    if [ -n "$service_pid" ]; then
      kill "$service_pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

echo "Starting Voice Notes demo. Logs: $log_dir"
(
  cd "$project_dir/backend"
  exec .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8003 --no-access-log
) >"$log_dir/backend.log" 2>&1 &
backend_pid=$!
(
  cd "$project_dir/frontend"
  exec "$flutter_bin" run -d web-server --web-hostname 127.0.0.1 --web-port 5174 --no-pub
) >"$log_dir/frontend.log" 2>&1 &
frontend_pid=$!

ready=false
for ((attempt=0; attempt<180; attempt++)); do
  if ! kill -0 "$backend_pid" 2>/dev/null || ! kill -0 "$frontend_pid" 2>/dev/null; then
    echo "Startup failed. Check $log_dir/backend.log and $log_dir/frontend.log."
    exit 1
  fi
  if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:8003/health >/dev/null 2>&1 &&
     curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:5174/ >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [ "$ready" != true ]; then
  echo "Startup timed out. Check logs in $log_dir."
  exit 1
fi

echo "Demo ready: http://127.0.0.1:5174"
echo "Connection settings: http://127.0.0.1:8003"
echo "Enter your local APP_ACCESS_TOKEN in the app. Keep this terminal open; Ctrl+C stops both services."
open http://127.0.0.1:5174 || true
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 2
done
echo "A service stopped. Check logs in $log_dir."
exit 1
