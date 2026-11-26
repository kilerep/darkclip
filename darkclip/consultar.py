"""🤝 Ponte Claude ↔ Gemini: o Claude Code (ou você) faz uma pergunta e o Gemini responde, inclusive
ASSISTINDO um vídeo (link do YouTube ou arquivo do PC). Usa a chave GEMINI_API_KEY do seu .env.

    python -m darkclip.consultar "sua pergunta"
    python -m darkclip.consultar "que técnicas de edição esse vídeo usa?" --video "https://youtu.be/..."
    python -m darkclip.consultar "critique essas regras" --arquivo darkclip/hooks.py --arquivo docs/ESTUDO_EDICAO.md

Cada conversa fica salva em docs/CONVERSAS_GEMINI.md (pergunta + resposta), para o Claude ler e usar.
O Gemini dá opinião; quem decide e testa as mudanças no DarkClip é você com o Claude.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import config, gemini

LOG = config.ROOT / "docs" / "CONVERSAS_GEMINI.md"
CONTEXT = ("Você está ajudando a melhorar o DarkClip, um sistema local (Python + ffmpeg) que transforma vídeos longos "
           "em Shorts/Reels de gameplay para um canal brasileiro de cortes. Responda em português do Brasil, de forma "
           "objetiva e prática. Quando falar de um vídeo, cite o segundo exato (mm:ss) do que você viu ou ouviu. "
           "Separe o que você VIU/OUVIU do que é sua OPINIÃO. Se não tiver certeza, diga.")


def ask(question: str, video: str | None = None, files: list[str] | None = None, on_retry=None) -> str:
    parts = [CONTEXT, "", "PERGUNTA:", question]
    for f in files or []:
        p = Path(f)
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="ignore")[:60_000]
            parts += ["", f"--- ARQUIVO {p.name} ---", txt]
    prompt = config.redact("\n".join(parts))      # nunca manda chaves por engano
    if not video:
        return gemini.ask(None, prompt, agentic=False, schema=None, timeout=600, on_retry=on_retry, raw=True)
    uploaded = None
    if gemini.is_youtube(video):
        vid = {"uri": video}
    else:
        uploaded = gemini.upload(Path(video))
        vid = {"uri": uploaded["uri"], "mime_type": uploaded["mime_type"]}
    try:
        return gemini.ask(vid, prompt, agentic=True, schema=None, timeout=900, on_retry=on_retry, raw=True)
    finally:
        if uploaded:
            try:
                gemini.delete(uploaded["name"])
            except Exception:
                pass


def save(question: str, answer: str, video: str | None, files: list[str] | None) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    head = "" if LOG.exists() else ("# 🤝 Conversas com o Gemini\n\nPerguntas feitas pelo `python -m darkclip.consultar` "
                                    "(ou pela skill `/consultar-gemini`) e as respostas do Gemini.\n")
    meta = " · ".join(x for x in (f"vídeo: {video}" if video else "", f"arquivos: {', '.join(files)}" if files else "") if x)
    block = (f"\n---\n\n## {time.strftime('%d/%m/%Y %H:%M')} · {getattr(config, 'GEMINI_MODEL_USED', config.GEMINI_MODEL)}\n"
             + (f"_{meta}_\n" if meta else "") + f"\n**Pergunta:** {question}\n\n**Gemini:**\n\n{answer.strip()}\n")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(head + block)


def main() -> None:
    ap = argparse.ArgumentParser(description="Pergunte ao Gemini (com vídeo opcional)")
    ap.add_argument("pergunta")
    ap.add_argument("--video", help="link do YouTube ou caminho de um vídeo no PC")
    ap.add_argument("--arquivo", action="append", default=[], help="arquivo para o Gemini ler junto (pode repetir)")
    a = ap.parse_args()
    if not config.HAS_GEMINI:
        sys.exit("❌ Falta a chave do Gemini: coloque GEMINI_API_KEY no arquivo .env")
    print("🤝 Perguntando ao Gemini" + (" (ele vai assistir o vídeo, pode levar alguns minutos)…" if a.video else "…"), flush=True)
    try:
        answer = ask(a.pergunta, a.video, a.arquivo, on_retry=lambda m: print("   " + m, flush=True))
    except gemini.GeminiError as e:
        sys.exit(f"❌ O Gemini não respondeu: {e}\n   Se for 'ocupado (503)', tente de novo em alguns minutos.")
    save(a.pergunta, answer, a.video, a.arquivo)
    print("\n" + answer.strip() + f"\n\n✅ Conversa salva em {LOG}")


if __name__ == "__main__":
    main()
