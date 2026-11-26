"""Configuração central do DarkClip (lida de variáveis de ambiente / .env)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #", 1)[0].strip().strip('"').strip("'")  # remove comentário na linha
        if v:
            os.environ.setdefault(k.strip(), v)


_load_dotenv()

DATA_DIR = Path(os.environ.get("DARKCLIP_DATA", ROOT / "data"))
JOBS_DIR = DATA_DIR / "jobs"
UPLOADS_DIR = DATA_DIR / "uploads"
for d in (JOBS_DIR, UPLOADS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Claude (seleção de momentos virais, títulos, roteiros). Sem chave -> heurística local.
CLAUDE_MODEL = os.environ.get("DARKCLIP_MODEL", "claude-opus-5-5")
CLAUDE_EFFORT = os.environ.get("DARKCLIP_EFFORT", "medium")
HAS_CLAUDE = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))

# IA local e grátis (100% offline) via Ollama: https://ollama.com  ex.: DARKCLIP_OLLAMA_MODEL=qwen3:8b
OLLAMA_MODEL = os.environ.get("DARKCLIP_OLLAMA_MODEL", "")
OLLAMA_URL = os.environ.get("DARKCLIP_OLLAMA_URL", "http://127.0.0.1:11434")
# Transcrição local (vídeos sem legenda): tiny | base | small | medium | large-v3
WHISPER_MODEL = os.environ.get("DARKCLIP_WHISPER_MODEL", "small")

# Gemini (assiste o vídeo: imagem + áudio). Chave grátis: https://aistudio.google.com/apikey
GEMINI_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
HAS_GEMINI = bool(GEMINI_KEY)
GEMINI_MODEL = os.environ.get("DARKCLIP_GEMINI_MODEL", "gemini-4-hydrogen")
# Vídeo do YouTube por link no Gemini: "prévia sem custo" segundo a documentação (pode mudar) — 0 desliga
GEMINI_YT_FREE = os.environ.get("DARKCLIP_GEMINI_YT_FREE", "1") != "0"
# Quem "assiste" o vídeo: auto (Gemini se tiver chave, senão Claude por quadros) | gemini | claude | off
VISION = os.environ.get("DARKCLIP_VISION", "auto")

# Vídeo de saída
OUT_W, OUT_H = 1080, 1920
IS_TERMUX = "com.termux" in os.environ.get("PREFIX", "")
# No Android não há DejaVu: usa a Roboto do próprio sistema (/system/fonts)
import sys as _sys
FONT = os.environ.get("DARKCLIP_FONT", "Roboto" if IS_TERMUX else "Arial" if os.name == "nt" or _sys.platform == "darwin"
                      else "DejaVu Sans")
FONTS_DIR = os.environ.get("DARKCLIP_FONTS_DIR", "/system/fonts" if IS_TERMUX and Path("/system/fonts").is_dir() else "")
VOICE = os.environ.get("DARKCLIP_VOICE", "pt-BR-AntonioNeural")
X264_PRESET = os.environ.get("DARKCLIP_PRESET", "veryfast")  # celular: ultrafast
# Encoder de vídeo: libx264 (padrão) | h264_mediacodec (Android/Termux, usa o chip do celular)
# | h264_videotoolbox (Mac) | h264_nvenc (NVIDIA)
ENCODER = os.environ.get("DARKCLIP_ENCODER", "libx264")

# Servidor
TOKEN = os.environ.get("DARKCLIP_TOKEN", "")  # se definido, o app exige este token
POSTIZ_ENABLED = os.environ.get("POSTIZ_API_KEY") is not None


# 🔒 Nunca deixar chaves e tokens em registros, erros ou arquivos de job
import re as _re

_SECRET_PATTERNS = [
    _re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),            # Anthropic
    _re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),               # Google / Gemini
    _re.compile(r"EAA[A-Za-z0-9]{20,}"),                    # Meta (Facebook/Instagram)
    _re.compile(r"ya29\.[A-Za-z0-9_\-]{20,}"),             # Google OAuth (YouTube)
    _re.compile(r"1//[A-Za-z0-9_\-]{20,}"),                 # Google refresh token
]
_SECRET_PARAM = _re.compile(r"((?:access_token|api_key|apikey|key|token|client_secret|refresh_token)=)([^&\s\"']{12,})",
                            _re.I)


def redact(text: str) -> str:
    """Troca chaves e tokens por ••• (só segredos longos; não mexe em textos comuns)."""
    if not text:
        return text
    for env in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GEMINI_API_KEY", "GOOGLE_API_KEY", "POSTIZ_API_KEY"):
        v = os.environ.get(env, "")
        if len(v) >= 16:
            text = text.replace(v, "•••")
    for p in _SECRET_PATTERNS:
        text = p.sub("•••", text)
    return _SECRET_PARAM.sub(r"\1•••", text)
