"""🔊 Efeitos sonoros gerados por código (ideia do purffle-shorts, MIT): sem arquivos, sem direitos autorais.

- whoosh: ar passando (ruído filtrado com frequência subindo e descendo) — em cada corte/troca de zoom
- hit: impacto grave curto — embaixo do gancho, no início do vídeo
Cada efeito sai levemente diferente (aleatório), como num editor de verdade.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

RATE = 24000
ATTACK = {"whoosh": 0.22, "hit": 0.006, "pop": 0.004}   # onde o efeito é mais forte (s), para cair em cima do evento


def _norm(x: np.ndarray, peak: float = 0.5) -> np.ndarray:
    m = float(np.max(np.abs(x))) or 1.0
    return x * (peak / m)


def whoosh(seconds: float = 0.5, rng: np.random.Generator | None = None) -> np.ndarray:
    rng = rng or np.random.default_rng()
    n = int(seconds * RATE)
    p = np.arange(n) / n
    pk = ATTACK["whoosh"] / seconds
    lo, top = rng.uniform(280, 420), rng.uniform(2200, 3200)
    sweep = np.where(p < pk, p / pk, 1 - (p - pk) / (1 - pk) * 0.85)
    f = 2 * np.sin(np.pi * (lo + (top - lo) * sweep ** 2) / RATE)
    noise = rng.uniform(-1, 1, n)
    low = band = 0.0
    out = np.empty(n)
    for i in range(n):  # filtro passa-faixa com frequência variável (state-variable filter)
        low += f[i] * band
        high = noise[i] - low - 0.55 * band
        band += f[i] * high
        out[i] = band
    env = np.where(p < pk, np.sin(0.5 * np.pi * p / pk) ** 2, np.exp(-4.5 * (p - pk) / (1 - pk)))
    return _norm(out * env)


def hit(seconds: float = 0.65, rng: np.random.Generator | None = None) -> np.ndarray:
    rng = rng or np.random.default_rng()
    t = np.arange(int(seconds * RATE)) / RATE
    f0, f1 = rng.uniform(140, 170), rng.uniform(55, 65)
    fc = f1 + (f0 - f1) * np.exp(-t / 0.06)
    body = np.sin(np.cumsum(2 * np.pi * fc / RATE)) * np.exp(-t / 0.22)
    noise = np.convolve(rng.uniform(-1, 1, t.size), np.ones(12) / 12, mode="same")  # ruído escuro
    return _norm(body + noise * 1.8 * np.exp(-t / 0.035))


def pop(seconds: float = 0.16, rng: np.random.Generator | None = None) -> np.ndarray:
    """"Pop" curtinho e agudo (frequência caindo), para quando a figurinha aparece."""
    rng = rng or np.random.default_rng()
    t = np.arange(int(seconds * RATE)) / RATE
    f0, f1 = rng.uniform(1100, 1400), rng.uniform(450, 600)
    freq = f1 + (f0 - f1) * np.exp(-t * 38)
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    env = np.minimum(1.0, t / 0.004) * np.exp(-t * 26)
    return _norm(np.sin(phase) * env, 0.45)


SOUNDS = {"whoosh": whoosh, "hit": hit, "pop": pop}


def events_for(cuts: list[float], hook: bool, min_gap: float = 1.5) -> list[tuple[float, str]]:
    ev: list[tuple[float, str]] = [(0.05, "hit")] if hook else []
    last = -9.0
    for t in cuts:
        if t - last >= min_gap and t > 0.5:
            ev.append((t, "whoosh"))
            last = t
    return ev


def track(events: list[tuple[float, str]], total: float, dest: Path, volume: float = 0.35) -> Path | None:
    """WAV mono de `total` s com os efeitos posicionados; None se não houver nada."""
    events = [(t, k) for t, k in events if k in SOUNDS and 0 <= t < total]
    if not events:
        return None
    rng = np.random.default_rng()
    pcm = np.zeros(int(total * RATE) + 1)
    for t, kind in events:
        snd = SOUNDS[kind](rng=rng) * volume
        a = int((t - ATTACK[kind]) * RATE)
        s0 = max(0, -a)
        a = max(0, a)
        b = min(pcm.size, a + snd.size - s0)
        pcm[a:b] += snd[s0:s0 + (b - a)]
    data = (np.clip(pcm, -1, 1) * 32767).astype("<i2").tobytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)
    return dest
