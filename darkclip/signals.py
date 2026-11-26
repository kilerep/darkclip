"""Sinais objetivos de viralidade, combinados com a análise da IA.

- heatmap "Mais repetidos" do YouTube (o que o público realmente reassiste)
- capítulos do vídeo
- energia do áudio (picos de volume, risadas, gritos)
- ritmo de fala, perguntas, marcadores de risada na legenda
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

LAUGH = re.compile(r"\[(risos|risadas|laughter|laughs|aplausos|applause)\]|\b(k{4,}|(ha){3,}|(rs){3,})\b", re.I)


def heat_at(heatmap: list[dict] | None, start: float, end: float) -> float | None:
    """Média normalizada (0-1) do 'mais repetidos' no intervalo."""
    if not heatmap:
        return None
    vals, tot = 0.0, 0.0
    for h in heatmap:
        a, b = max(start, h["start_time"]), min(end, h["end_time"])
        if b > a:
            vals += h["value"] * (b - a)
            tot += b - a
    return vals / tot if tot else None


def audio_energy(media: Path, hop: float = 0.5) -> list[float] | None:
    """Loudness (dB RMS) a cada `hop` segundos. Requer numpy; retorna None se faltar."""
    try:
        import numpy as np
    except ImportError:
        return None
    sr = 8000
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-vn", "-ac", "1", "-ar", str(sr),
                        "-f", "s16le", "-"], capture_output=True)
    if p.returncode != 0 or not p.stdout:
        return None
    x = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768
    n = int(sr * hop)
    frames = x[: len(x) // n * n].reshape(-1, n)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-9)
    return (20 * np.log10(rms)).round(1).tolist()


def energy_score(energy: list[float] | None, start: float, end: float, hop: float = 0.5) -> float | None:
    """0-1: quão "animado" é o trecho. Mistura duas visões:
    - global: percentil do pico em relação ao vídeo todo;
    - local (técnica do VoXCluTcH): pico vs. a mediana do som ao redor (±45 s, sem o próprio trecho),
      15 dB acima do entorno = 1,0. Em lives o volume muda a noite toda; o pico relativo é o que importa."""
    if not energy:
        return None
    a, b = int(start / hop), max(int(start / hop) + 1, int(end / hop))
    win = energy[a:b]
    if not win:
        return None
    ref = sorted(energy)
    peak = sorted(win)[int(len(win) * 0.9) - 1 if len(win) > 1 else 0]
    rank = sum(v <= peak for v in ref) / len(ref)
    pad, gap = int(45 / hop), int(5 / hop)
    around = energy[max(0, a - pad):max(0, a - gap)] + energy[min(len(energy), b + gap):b + pad]
    if len(around) >= 6:
        ambient = sorted(around)[len(around) // 2]
        local = max(0.0, min(1.0, (max(win) - ambient) / 15.0))
        return round(0.5 * rank + 0.5 * local, 3)
    return round(rank, 3)


def audio_peaks(energy: list[float] | None, hop: float = 0.5, bin_s: float = 15.0, z_min: float = 2.0,
                gap: float = 45.0, top: int = 12) -> list[float]:
    """Instantes (s) de picos SUSTENTADOS de áudio — média em blocos de 15 s, z-score contra ~10 min ao redor
    (técnica do autoclipnew). Usado para transcrever só os trechos promissores de lives longas."""
    if not energy:
        return []
    k = max(1, int(bin_s / hop))
    bins = [sum(energy[i:i + k]) / len(energy[i:i + k]) for i in range(0, len(energy), k)]
    half = max(2, int(300 / bin_s))
    med = sorted(bins)[len(bins) // 2]
    peaks = []
    for i, v in enumerate(bins):
        w = bins[max(0, i - half):i + half + 1]
        mean = sum(w) / len(w)
        sd = (sum((x - mean) ** 2 for x in w) / len(w)) ** 0.5 or 1.0
        z = (v - mean) / sd
        if z >= z_min and v - med >= 4.0:   # precisa ser alto de verdade (≥ 4 dB acima do normal do vídeo)
            peaks.append((z, i * bin_s + bin_s / 2))
    out: list[float] = []
    for z, t in sorted(peaks, reverse=True):
        if all(abs(t - o) >= gap for o in out):
            out.append(t)
        if len(out) >= top:
            break
    return sorted(out)


def text_signals(segs: list[dict], start: float, end: float) -> dict:
    words, text = 0, []
    for s in segs:
        if s["end"] > start and s["start"] < end:
            text.append(s["text"])
            words += len(s["text"].split())
    t = " ".join(text)
    dur = max(end - start, 1)
    return {"wpm": round(words / dur * 60), "questions": t.count("?"), "laughs": len(LAUGH.findall(t))}


def visual_at(visual: dict | None, start: float, end: float) -> float | None:
    """0-1: maior nota (Gemini) entre os momentos visuais que se sobrepõem ao intervalo."""
    if not visual or not visual.get("moments"):
        return None
    best = 0.0
    for m in visual["moments"]:
        if m["end"] > start and m["start"] < end:
            best = max(best, m["score"] / 100)
    return round(best, 2)


def annotate_transcript(segs: list[dict], heatmap: list[dict] | None, energy: list[float] | None,
                        comments: dict | None = None, visual: dict | None = None,
                        limit_chars: int = 400_000) -> str:
    """Transcrição com marcadores: 🔥 reassistido · 💬 citado nos comentários · 👁️ momento visual · ⚡ áudio · 😂."""
    from .comments import attention_at
    lines = []
    for s in segs:
        tags = []
        h = heat_at(heatmap, s["start"], s["end"])
        if h is not None and h >= 0.55:
            tags.append(f"🔥{h:.2f}")
        c = attention_at(comments, s["start"], s["end"])
        if c is not None and c >= 0.35:
            tags.append(f"💬{c:.2f}")
        v = visual_at(visual, s["start"], s["end"])
        if v is not None and v >= 0.7:
            tags.append("👁️")
        e = energy_score(energy, s["start"], s["end"])
        if e is not None and e >= 0.93:
            tags.append("⚡")
        if LAUGH.search(s["text"]):
            tags.append("😂")
        tag = (" " + " ".join(tags)) if tags else ""
        lines.append(f"[{s['start']:.1f}-{s['end']:.1f}{tag}] {s['text']}")
    return "\n".join(lines)[:limit_chars]


def blend_score(ai_score: float, heat: float | None, energy: float | None,
                comments: float | None = None, visual: float | None = None, wpm: float | None = None) -> int:
    """Nota final ponderada pelos sinais disponíveis (os ausentes não pesam).
    IA 50% · heatmap do público 20% · comentários 15% · visual 10% · energia 5%.
    Trecho com pouca fala (gameplay, corrida, ação): o peso passa da IA (que lê a fala) para visual e áudio
    — ideia do Clips Kitty."""
    quiet = wpm is not None and wpm < 70
    # sinais independentes que concordam = momento quase certo (técnica do autoclipnew): +3 por sinal extra
    strong = sum(1 for v in (heat, comments, visual, energy) if v is not None and v >= 0.6)
    bonus = min(8, 3 * max(0, strong - 1))
    parts = [(0.30 if quiet else 0.50, ai_score)]
    for w, v in ((0.20, heat), (0.15, comments), (0.25 if quiet else 0.10, visual), (0.15 if quiet else 0.05, energy)):
        if v is not None:
            parts.append((w, v * 100))
    return int(min(99, round(sum(w * v for w, v in parts) / sum(w for w, _ in parts)) + bonus))
