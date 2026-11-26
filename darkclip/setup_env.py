"""Prepara o .env (cria a partir do exemplo e gera a senha do app) e mostra o endereço para o celular.

  python -m darkclip.setup_env          # usado pelos instaladores
  python -m darkclip.setup_env --url    # só imprime o endereço/senha (usado ao iniciar)
"""
from __future__ import annotations

import secrets
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV, EXAMPLE = ROOT / ".env", ROOT / ".env.example"


def lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # não envia nada; só descobre a interface de rede usada
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "IP-DO-PC"


def ensure_env() -> str:
    if not ENV.exists():
        ENV.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    lines = ENV.read_text(encoding="utf-8").splitlines()
    token = ""
    for i, ln in enumerate(lines):
        if ln.startswith("DARKCLIP_TOKEN="):
            token = ln.split("=", 1)[1].split(" #", 1)[0].strip()
            if not token:
                token = secrets.token_hex(3)
                lines[i] = f"DARKCLIP_TOKEN={token}"
    if not token:
        token = secrets.token_hex(3)
        lines.append(f"DARKCLIP_TOKEN={token}")
    new = "\n".join(lines) + "\n"
    if new != ENV.read_text(encoding="utf-8"):  # só regrava se mudou, guardando uma cópia antes
        backup = ENV.with_name(".env.bak")
        backup.write_text(ENV.read_text(encoding="utf-8"), encoding="utf-8")
        ENV.write_text(new, encoding="utf-8")
    return token


def main() -> None:
    token = ensure_env()
    port = 8787
    print("\n" + "=" * 54)
    print("  No celular (mesmo Wi-Fi), abra este endereço:")
    print(f"     http://{lan_ip()}:{port}/?token={token}")
    print(f"  (a senha {token} fica salva no app automaticamente)")
    print("=" * 54 + "\n")
    if "--url" not in sys.argv:
        print("Chaves de IA: edite o arquivo .env (GEMINI_API_KEY e ANTHROPIC_API_KEY).")


if __name__ == "__main__":
    main()
