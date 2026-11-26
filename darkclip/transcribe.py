"""Transcrição com timestamps por palavra.

Ordem: legendas do YouTube (VTT, inclusive automáticas com tempo por palavra)
-> faster-whisper local (se instalado) -> erro explicativo.

Formato: lista de segmentos {"start","end","text","words":[{"start","end","word"}]}.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

_TS = r"(\d+):(\d{2}):(\d{2})[.,](\d{3})"
_CUE = re.compile(_TS + r"\s+-->\s+" + _TS)
_INLINE = re.compile(r"<" + _TS + r">")


def _sec(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _clean(t: str) -> str:
    t = re.sub(r"</?c[^>]*>", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t).replace("​", "").strip()


def parse_vtt(path: Path) -> list[dict]:
    """Converte VTT em segmentos com palavras, removendo a duplicação típica
    das legendas automáticas do YouTube (linhas que "rolam")."""
    text = path.read_text(encoding="utf-8", errors="ignore").replace("\r", "")
    # Leitura linha a linha: cada linha "00:00 --> 00:01" abre um cue (há VTTs sem linha em branco entre cues)
    cues: list[tuple[float, float, list[str]]] = []
    for ln in text.split("\n"):
        m = _CUE.search(ln)
        if m:
            cues.append((_sec(*m.groups()[:4]), _sec(*m.groups()[4:]), []))
        elif cues and ln.strip() and not ln.startswith(("NOTE", "STYLE", "WEBVTT")):
            cues[-1][2].append(ln)
    words: list[dict] = []
    plain_cues: list[tuple[float, float, str]] = []
    for start, end, body_lines in cues:
        timed = [ln for ln in body_lines if _INLINE.search(ln)]
        if timed:  # legenda automática com tempo por palavra
            for ln in timed:
                parts = re.split(r"(<\d+:\d{2}:\d{2}[.,]\d{3}>)", ln)
                t = start
                for p in parts:
                    mm = _INLINE.fullmatch(p)
                    if mm:
                        t = _sec(*mm.groups())
                        continue
                    for w in _clean(p).split():
                        words.append({"start": t, "end": t, "word": w})
        else:
            cue = _clean(" ".join(body_lines))
            if cue:
                plain_cues.append((start, end, cue))

    if words:
        words.sort(key=lambda w: w["start"])
        for i, w in enumerate(words):
            nxt = words[i + 1]["start"] if i + 1 < len(words) else w["start"] + 0.5
            w["end"] = max(w["start"] + 0.08, min(nxt, w["start"] + 1.2))
        return [dict(g, timed=True) for g in group_words(words)]   # tempo por palavra (legenda automática)

    # Legenda manual: remove linhas repetidas e distribui palavras no tempo do cue
    segs, last = [], ""
    for start, end, cue in plain_cues:
        if cue == last:
            continue
        if last and cue.startswith(last):
            cue = cue[len(last):].strip()
        last = cue if cue else last
        toks = cue.split()
        if not toks:
            continue
        dur = max(end - start, 0.2) / len(toks)
        ws = [{"start": start + i * dur, "end": start + (i + 1) * dur, "word": t} for i, t in enumerate(toks)]
        segs.append({"start": start, "end": end, "text": " ".join(toks), "words": ws, "timed": False})
    return segs


def group_words(words: list[dict], max_gap: float = 0.8, max_len: float = 8.0) -> list[dict]:
    segs, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > max_gap or w["end"] - cur[0]["start"] > max_len
                    or cur[-1]["word"].endswith((".", "?", "!"))):
            segs.append(cur)
            cur = []
        cur.append(w)
    if cur:
        segs.append(cur)
    return [{"start": s[0]["start"], "end": s[-1]["end"], "text": " ".join(w["word"] for w in s), "words": s}
            for s in segs]


_MODEL_CACHE: dict = {}


def _whisper_model(model: str | None = None):
    from . import config
    model = model or config.WHISPER_MODEL
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "Vídeo sem legendas e faster-whisper não instalado. "
            "Instale com: pip install faster-whisper (PC/servidor) ou envie um vídeo com legenda."
        ) from e
    if model not in _MODEL_CACHE:
        _MODEL_CACHE[model] = WhisperModel(model, device="cpu", compute_type="int8")
    return _MODEL_CACHE[model]


def _load_audio(media: Path, start: float = 0.0, dur: float | None = None):
    """Áudio 16 kHz mono via ffmpeg (evita incompatibilidades do PyAV usado pelo faster-whisper)."""
    import subprocess

    import numpy as np
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", f"{start:.2f}"] if start else []) + ["-i", str(media)]
    cmd += (["-t", f"{dur:.2f}"] if dur else []) + ["-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    if not raw:
        raise RuntimeError("não consegui extrair o áudio do vídeo para transcrever")
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def _run_whisper(audio, lang: str | None, offset: float = 0.0, model: str | None = None, progress=None) -> list[dict]:
    segments, _ = _whisper_model(model).transcribe(audio, language=lang, word_timestamps=True, vad_filter=True)
    total = len(audio) / 16000 or 1.0
    out, last = [], -1
    for s in segments:  # o Whisper entrega aos poucos: dá para mostrar o progresso
        pct = int(min(100, s.end / total * 100))
        if progress and pct >= last + 5:
            progress(pct, s.end, total)
            last = pct
        ws = [{"start": w.start + offset, "end": w.end + offset, "word": w.word.strip()} for w in (s.words or [])]
        out.append({"start": s.start + offset, "end": s.end + offset, "text": s.text.strip(), "words": ws})
    return out


def whisper_transcribe(media: Path, lang: str | None = None, model: str | None = None, progress=None) -> list[dict]:
    """Transcreve o arquivo inteiro (progress(pct, feito_s, total_s) é chamado a cada ~5%)."""
    return _run_whisper(_load_audio(media), lang, 0.0, model, progress)


def whisper_windows(media: Path, windows: list[tuple[float, float]], lang: str | None = None,
                    model: str | None = None, progress=None) -> list[dict]:
    """Transcreve SÓ os trechos indicados (técnica do autoclipnew): numa live de 4 h, minutos em vez de horas."""
    out: list[dict] = []
    for k, (a, b) in enumerate(windows, 1):
        if progress:
            progress(k, len(windows))
        try:
            out += _run_whisper(_load_audio(media, a, b - a), lang, a, model)
        except RuntimeError:
            continue
    return sorted(out, key=lambda s: s["start"])


def merge_windows(centers: list[float], before: float = 50, after: float = 50, duration: float | None = None,
                  limit: int = 14) -> list[tuple[float, float]]:
    """Janelas em volta dos pontos promissores, unidas quando se encostam."""
    iv = sorted((max(0.0, c - before), (min(duration, c + after) if duration else c + after)) for c in centers[:limit * 2])
    merged: list[list[float]] = []
    for a, b in iv:
        if merged and a <= merged[-1][1] + 5:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged][:limit]


def transcribe(video: Path, subs: Path | None, lang: str = "pt", progress=None) -> tuple[list[dict], str]:
    if subs and subs.exists():
        segs = parse_vtt(subs)
        if segs:
            return segs, f"legenda:{subs.name}"
    return whisper_transcribe(video, lang, progress=progress), "faster-whisper"


def slice_words(segs: list[dict], start: float, end: float) -> list[dict]:
    """Palavras dentro de [start, end], com tempo relativo ao início do corte."""
    out = []
    for s in segs:
        for w in s["words"]:
            if w["end"] > start and w["start"] < end:
                out.append({"start": max(0.0, w["start"] - start), "end": min(end, w["end"]) - start,
                            "word": w["word"]})
    return out


def _norm(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower())


def estimate_offset(media: Path, segs: list[dict], lang: str | None, at: float | None = None,
                    dur: float = 45.0, model: str | None = None) -> float | None:
    """Quanto a legenda está adiantada (+) ou atrasada (−) em relação à fala real, em segundos.
    Transcreve ~45 s do áudio com o Whisper e compara palavra por palavra. None se não der para medir."""
    words = [w for s in segs for w in s["words"]]
    if len(words) < 30:
        return None
    if at is None:
        at = words[int(len(words) * 0.4)]["start"]
    heard = _run_whisper(_load_audio(media, max(0.0, at), dur), lang, max(0.0, at), model)
    sub = [(_norm(w["word"]), w["start"]) for w in words if at - 15 <= w["start"] <= at + dur + 15]
    deltas = []
    for seg in heard:
        for w in seg["words"]:
            n = _norm(w["word"])
            if len(n) < 4:
                continue
            near = [w["start"] - t for m, t in sub if m == n and abs(w["start"] - t) <= 10]
            if near:
                deltas.append(min(near, key=abs))
    if len(deltas) < 6:
        return None
    deltas.sort()
    med = deltas[len(deltas) // 2]
    good = [d for d in deltas if abs(d - med) <= 0.7]
    if len(good) < max(6, len(deltas) * 0.5):
        return None
    return round(sum(good) / len(good), 2)


def shift(segs: list[dict], d: float) -> list[dict]:
    """Move todos os tempos da transcrição em `d` segundos."""
    out = []
    for s in segs:
        ws = [{**w, "start": max(0.0, w["start"] + d), "end": max(0.0, w["end"] + d)} for w in s["words"]]
        out.append({**s, "start": max(0.0, s["start"] + d), "end": max(0.0, s["end"] + d), "words": ws})
    return out


def whisper_words(media: Path, start: float, end: float, lang: str | None, model: str | None = None) -> list[dict]:
    """Palavras exatas (fala real) entre start e end do arquivo, com tempo relativo a `start`."""
    pad = 0.3
    a = max(0.0, start - pad)
    segs = _run_whisper(_load_audio(media, a, end - a + pad), lang, a, model)
    out = []
    for s in segs:
        for w in s["words"]:
            if w["end"] > start and w["start"] < end and w["word"]:
                out.append({"start": max(0.0, w["start"] - start), "end": min(end, w["end"]) - start, "word": w["word"]})
    return out
