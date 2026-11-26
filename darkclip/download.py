"""Download de vídeo + legendas com yt-dlp."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def _ytdlp() -> list[str]:
    exe = shutil.which("yt-dlp")
    cmd = [exe] if exe else ["python3", "-m", "yt_dlp"]
    # YouTube exige um runtime JavaScript; o yt-dlp só usa Deno por padrão, então habilitamos o Node se existir
    if not shutil.which("deno") and shutil.which("node"):
        cmd += ["--js-runtimes", "node"]
    # Cookies (opcional) para quando o YouTube pede "confirme que você não é um robô" (comum em servidores/VPS)
    cookies = os.environ.get("DARKCLIP_COOKIES")
    if cookies and Path(cookies).exists():
        cmd += ["--cookies", cookies]
    return cmd


def _err(stderr: str, what: str = "yt-dlp") -> RuntimeError:
    """Mensagem curta e acionável a partir do stderr do yt-dlp."""
    errs = [ln.replace("ERROR: ", "") for ln in stderr.splitlines() if ln.startswith("ERROR")]
    msg = (errs[-1] if errs else stderr.strip().splitlines()[-1] if stderr.strip() else "erro desconhecido")[:300]
    hint = ""
    if "429" in msg:
        hint = " → YouTube limitou pedidos: espere alguns minutos e tente de novo."
    elif "not a bot" in msg or "Sign in" in msg:
        hint = " → YouTube pediu verificação: atualize o yt-dlp ou use DARKCLIP_COOKIES (veja o README)."
    elif "403" in msg:
        hint = " → acesso negado pelo servidor do vídeo: atualize o yt-dlp (pip install -U yt-dlp)."
    return RuntimeError(f"{what}: {msg}{hint}")


def fetch_metadata(url: str) -> dict:
    out = subprocess.run(
        _ytdlp() + ["--dump-single-json", "--no-playlist", "--skip-download", url],
        capture_output=True, text=True, timeout=180,
    )
    if out.returncode != 0:
        raise _err(out.stderr)
    return json.loads(out.stdout)


def pick_sub_lang(meta: dict, lang: str = "pt") -> str | None:
    """Escolhe UMA legenda (pedir várias faz o YouTube responder 429).
    Ordem: manual no idioma pedido > automática no idioma original falado > automática no idioma pedido
    > qualquer manual > inglês."""
    manual = list((meta.get("subtitles") or {}).keys())
    auto = list((meta.get("automatic_captions") or {}).keys())
    rank = lambda k: (k.lower() not in (f"{lang}-br", lang), len(k))  # prefere pt-BR / pt
    m = sorted([k for k in manual if k.lower().split("-")[0] == lang and k != "live_chat"], key=rank)
    if m:
        return m[0]
    orig = [k for k in auto if k.endswith("-orig")]
    if orig:
        return orig[0]
    a = sorted([k for k in auto if k.lower().split("-")[0] == lang], key=rank)
    if a:
        return a[0]
    m = [k for k in manual if k != "live_chat"]
    if m:
        return m[0]
    return next((k for k in auto if k.startswith("en")), None)


def _subs_cmd(sub_lang: str | None) -> list[str]:
    if not sub_lang:
        return []
    return ["--write-subs", "--write-auto-subs", "--sub-langs", sub_lang, "--sub-format", "vtt"]


FMT = "bv*[height<={h}][ext=mp4]+ba[ext=m4a]/b[height<={h}]/b"


def download(url: str, workdir: Path, lang: str = "pt", max_height: int = 1080, subs: bool = True,
             meta: dict | None = None) -> dict:
    """Baixa o vídeo inteiro (mp4) e, se `subs`, uma legenda. Retorna dict com vídeo, legenda e metadados."""
    workdir.mkdir(parents=True, exist_ok=True)
    meta = meta or fetch_metadata(url)
    sub_lang = pick_sub_lang(meta, lang) if subs else None
    cmd = _ytdlp() + ["--no-playlist", "-f", FMT.format(h=max_height), "--merge-output-format", "mp4",
                      *_subs_cmd(sub_lang), "-o", str(workdir / "source.%(ext)s"), url]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    video = next((p for p in workdir.glob("source.*") if p.suffix in (".mp4", ".mkv", ".webm")), None)
    if out.returncode != 0 and not video:  # falha só na legenda não impede usar o vídeo
        raise _err(out.stderr, "download do vídeo")
    if not video:
        raise RuntimeError("Download concluído mas o arquivo de vídeo não foi encontrado.")
    vtts = sorted(workdir.glob("source*.vtt"), key=len_name)
    return {
        "video": video, "subs": vtts[0] if vtts else None, "url": url,
        "title": meta.get("title", ""), "channel": meta.get("channel") or meta.get("uploader", ""),
        "duration": float(meta.get("duration") or 0), "license": meta.get("license"),
        "heatmap": meta.get("heatmap") or None,
        "chapters": [{"start": c.get("start_time"), "title": c.get("title")} for c in (meta.get("chapters") or [])],
    }


def len_name(p: Path) -> int:
    return len(p.name)


def fetch_transcript_only(url: str, workdir: Path, lang: str = "pt") -> dict:
    """Etapa 1 do modo inteligente: metadados + UMA legenda (poucos KB).
    Traz também o heatmap 'Mais repetidos' e os capítulos do YouTube."""
    workdir.mkdir(parents=True, exist_ok=True)
    meta = fetch_metadata(url)
    sub_lang = pick_sub_lang(meta, lang)
    warning = None
    if sub_lang:
        info = workdir / "info.json"
        info.write_text(json.dumps(meta), encoding="utf-8")
        for attempt in range(3):  # reaproveita os metadados (--load-info-json): menos pedidos ao YouTube
            out = subprocess.run(_ytdlp() + ["--skip-download", *_subs_cmd(sub_lang), "--load-info-json", str(info),
                                             "-o", str(workdir / "source.%(ext)s")],
                                 capture_output=True, text=True, timeout=300)
            if out.returncode == 0 or "429" not in out.stderr:
                break
            time.sleep(8 * (attempt + 1))
        if out.returncode != 0:
            warning = str(_err(out.stderr, "legenda"))
    vtts = sorted(workdir.glob("source*.vtt"), key=len_name)
    return {
        "video": None, "subs": vtts[0] if vtts else None, "url": url, "sub_lang": sub_lang,
        "title": meta.get("title", ""), "channel": meta.get("channel") or meta.get("uploader", ""),
        "duration": float(meta.get("duration") or 0), "license": meta.get("license"),
        "heatmap": meta.get("heatmap") or None,
        "chapters": [{"start": c.get("start_time"), "title": c.get("title")} for c in (meta.get("chapters") or [])],
        "warning": warning, "was_live": meta.get("live_status") == "was_live" or bool(meta.get("was_live")),
    }


def download_audio(url: str, workdir: Path) -> Path:
    """Só o áudio (leve), para transcrever com Whisper quando não há legenda."""
    out = subprocess.run(_ytdlp() + ["--no-playlist", "-f", "ba[ext=m4a]/ba", "-o", str(workdir / "audio.%(ext)s"), url],
                         capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise _err(out.stderr, "download do áudio")
    return next(workdir.glob("audio.*"))


def download_section(url: str, workdir: Path, start: float, end: float, name: str,
                     max_height: int = 1080, tries: int = 2) -> Path:
    """Baixa só o trecho [start, end] (corte preciso). O arquivo começa em `start`."""
    workdir.mkdir(parents=True, exist_ok=True)
    for attempt in range(tries):  # 403 do YouTube costuma ser passageiro: tenta de novo com links novos
        out = subprocess.run(_ytdlp() + [
            "--no-playlist", "-f", FMT.format(h=max_height), "--merge-output-format", "mp4",
            "--download-sections", f"*{start:.2f}-{end:.2f}", "--force-keyframes-at-cuts",
            "-o", str(workdir / f"{name}.%(ext)s"), url,
        ], capture_output=True, text=True, timeout=1800)
        f = next((p for p in workdir.glob(f"{name}.*") if p.suffix in (".mp4", ".mkv", ".webm")), None)
        if out.returncode == 0 and f:
            return f
        time.sleep(3)
    raise _err(out.stderr, "download do trecho")


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def probe_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0:s=x", str(path)],
        capture_output=True, text=True,
    )
    try:
        w, h = out.stdout.strip().split("x")[:2]
        return int(w), int(h)
    except ValueError:
        return 0, 0
