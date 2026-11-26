"""🩺 Diagnóstico da instalação: confere programas, bibliotecas e chaves.

  python -m darkclip.doctor        (no Windows: verificar_windows.bat)

Se algo der errado, mande o resultado desta tela para o Claude.
"""
from __future__ import annotations

import importlib
import platform
import shutil
import subprocess
import sys

from . import config

OK, WARN, BAD = "✅", "⚠️ ", "❌"
if sys.platform == "win32":  # o cmd do Windows mostra emoji como quadradinho
    OK, WARN, BAD = "[OK]", "[!] ", "[X] "


def _ver(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return (out.stdout or out.stderr).strip().splitlines()[0] if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return None


def main() -> None:
    probs = 0
    print(f"\n🩺 DarkClip — diagnóstico ({platform.system()} {platform.release()}, Python {sys.version.split()[0]})\n")
    if sys.version_info < (3, 10):
        print(f"{BAD} Python muito antigo: instale o 3.12")
        probs += 1

    print("Programas:")
    for name, cmd, need in [("ffmpeg", ["ffmpeg", "-version"], True), ("ffprobe", ["ffprobe", "-version"], True),
                            ("yt-dlp", [sys.executable, "-m", "yt_dlp", "--version"], True),
                            ("Node.js (YouTube)", ["node", "--version"], False)]:
        v = _ver(cmd)
        print(f"  {OK if v else (BAD if need else WARN)} {name}: {v or 'NÃO encontrado'}")
        probs += 0 if v or not need else 1
    if shutil.which("ffmpeg"):
        filt = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        has_ass = " ass " in filt
        print(f"  {OK if has_ass else BAD} ffmpeg com legendas (filtro ass)")
        probs += 0 if has_ass else 1

    print("\nBibliotecas:")
    for mod, need, why in [("fastapi", True, "app"), ("uvicorn", True, "app"), ("anthropic", True, "Claude"),
                           ("httpx", True, "postar nas redes"), ("edge_tts", True, "voz"), ("numpy", True, "áudio"),
                           ("cv2", False, "seguir rosto"), ("faster_whisper", False, "transcrever vídeos sem legenda")]:
        try:
            importlib.import_module(mod)
            print(f"  {OK} {mod} ({why})")
        except Exception as e:
            print(f"  {BAD if need else WARN} {mod} ({why}): {str(e)[:80]}")
            probs += 1 if need else 0

    print("\nDetector de rostos (enquadramento):")
    try:
        import cv2

        from .reframe import MODEL
        ok = MODEL.exists() and MODEL.stat().st_size > 100_000
        if ok:
            cv2.FaceDetectorYN.create(str(MODEL), "", (320, 320))
        print(f"  {OK if ok else WARN} {'YuNet funcionando (o melhor: acha rosto de lado e em movimento)' if ok else 'YuNet NÃO instalado: usando o detector antigo, que perde rostos. Rode o install_windows.bat de novo'}")
    except Exception as e:
        print(f"  {WARN} YuNet com problema ({str(e)[:100]}): usando o detector antigo. Rode o install_windows.bat de novo")

    print("\nChaves de IA (.env):")
    print(f"  {OK if config.HAS_GEMINI else WARN} Gemini: {'configurado' if config.HAS_GEMINI else 'sem chave (opcional, grátis em aistudio.google.com/apikey)'}")
    if config.HAS_GEMINI:
        from . import gemini
        busy_all, answered = True, None
        for m in gemini._models():
            try:
                orig = config.GEMINI_MODEL
                config.GEMINI_MODEL = m
                r = gemini.ping()
                answered = (m, r)
                break
            except Exception as e:
                last = str(e)
                if not any(b in last for b in gemini.BUSY):
                    busy_all = False
                    break
            finally:
                config.GEMINI_MODEL = orig
        if answered:
            extra = "" if answered[0] == config.GEMINI_MODEL else " (modelo reserva: o principal está lotado agora)"
            print(f"  {OK} Gemini respondeu ({answered[0]}){extra}: {answered[1]}")
        elif busy_all:
            print(f"  {WARN} Google lotado agora (erro 503). Não é problema da sua chave: os cortes saem mesmo assim e o Gemini volta sozinho.")
        else:
            print(f"  {BAD} Gemini NÃO respondeu ({config.GEMINI_MODEL}): {last[:220]}")
            probs += 1
    print(f"  {OK if config.HAS_CLAUDE else WARN} Claude: {'configurado' if config.HAS_CLAUDE else 'sem chave (opcional)'}")
    print(f"  {OK if config.OLLAMA_MODEL else WARN} Ollama (offline): {config.OLLAMA_MODEL or 'não configurado (opcional)'}")
    print(f"  {OK if config.TOKEN else WARN} Senha do app: {'definida' if config.TOKEN else 'sem senha (rode install de novo)'}")

    print("\nTeste rápido de vídeo (ffmpeg + legenda):")
    try:
        import tempfile
        from pathlib import Path

        from .render import build_ass, set_aspect
        tmp = Path(tempfile.mkdtemp(prefix="dc_doc_"))
        set_aspect("9:16")
        build_ass([{"start": 0.1, "end": 0.9, "word": "TESTE"}], "OK", tmp / "t.ass", 1.5)
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1.5",
               "-vf", "ass=t.ass" + (f":fontsdir={config.FONTS_DIR}" if config.FONTS_DIR else ""), "t.mp4"]
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
        ok = r.returncode == 0 and (tmp / "t.mp4").exists()
        print(f"  {OK if ok else BAD} renderização {'funcionando' if ok else 'falhou: ' + r.stderr[-200:]}")
        probs += 0 if ok else 1
    except Exception as e:
        print(f"  {BAD} renderização falhou: {e}")
        probs += 1

    print("\n" + ("🎉 Tudo certo! Dê dois cliques em start_windows.bat (ou rode ./start.sh)." if not probs
                  else f"Encontrei {probs} problema(s) acima (❌). Tire um print desta tela e mande para o Claude."))


if __name__ == "__main__":
    main()
