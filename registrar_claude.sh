#!/usr/bin/env bash
# DarkClip - liga o DarkClip ao Claude Code (servidor MCP). Rode uma vez só.
cd "$(dirname "$0")"
command -v claude >/dev/null || { echo "Instale o Claude Code primeiro (claude.com/claude-code)."; exit 1; }
[ -x .venv/bin/python ] || { echo "Rode primeiro o ./install.sh"; exit 1; }
claude mcp add darkclip -s user -e PYTHONPATH="$PWD" -- "$PWD/.venv/bin/python" -m darkclip.mcp_server
echo "Pronto! Abra o DarkClip (./start.sh) e peça ao Claude: \"corta este vídeo em 3 Shorts longos: LINK\""
