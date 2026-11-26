#!/data/data/com.termux/files/usr/bin/bash
# Abre o DarkClip no celular: mantém o Termux acordado, sobe o servidor e abre o navegador.
cd "$(dirname "$0")"
termux-wake-lock 2>/dev/null || true          # impede o Android de pausar o processamento
(sleep 4 && termux-open-url "http://127.0.0.1:8787") &
echo "DarkClip rodando em http://127.0.0.1:8787  —  para parar: Ctrl+C (ou feche a sessão do Termux)"
HOST=127.0.0.1 PORT=8787 bash ./start.sh
termux-wake-unlock 2>/dev/null || true
