#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -d .venv ] && . .venv/bin/activate
HOST=${HOST:-0.0.0.0}; PORT=${PORT:-8787}
[ "$HOST" != "127.0.0.1" ] && python3 -m darkclip.setup_env --url
[ -z "$NO_WINDOW" ] && [ -n "$DISPLAY$WAYLAND_DISPLAY" -o "$(uname)" = "Darwin" ] && (python3 -m darkclip.launch &)
exec python3 -m uvicorn server:app --host "$HOST" --port "$PORT"
