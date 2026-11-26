"""😂 Momentos de reação: onde colocar figurinha e dar zoom no rosto.

Padrão dos vídeos de referência (docs/ESTUDO_EDICAO.md): figurinhas de reação nos 4 vídeos estudados
e close/zoom no rosto em 3 de 4. Aqui achamos esses momentos sem IA:
- pico de som bem acima do normal do próprio corte (grito, susto, explosão, risada alta);
- risada na fala ("kkkk", "haha", "(Risos)").
Cada momento ganha um humor: risada, susto ou hype. As figurinhas vêm da pasta figurinhas/<humor>/
do projeto (as suas) ou, se ela não existir, dos emojis Twemoji incluídos (licença CC-BY 4.0).
"""
from __future__ import annotations

import random
import re
from pathlib import Path

from . import config

MOODS = ["risada", "susto", "hype", "fail", "raiva"]
LAUGH = re.compile(r"k{3,}|haha|hehe|risos|risadas|laughter", re.I)
ASSETS = Path(__file__).parent / "assets" / "figurinhas"
MINE = config.ROOT / "figurinhas"
EXTS = (".png", ".webp", ".jpg", ".jpeg")


def detect(energy: list[float] | None, start: float, end: float, words: list[dict] | None,
           e_off: float = 0.0, hop: float = 0.5, min_gap: float = 4.0, every: float = 12.0) -> list[dict]:
    """Momentos de reação do corte: [{t, kind, forca}], com t relativo ao início do corte
    (antes dos cortes de silêncio). Cerca de 1 a cada `every` segundos, nunca mais perto que `min_gap`."""
    dur = end - start
    max_n = max(1, int(dur / every) + 1)
    laughs = [w["start"] for w in (words or []) if LAUGH.search(w.get("word", ""))]
    cands: list[tuple[float, float, str]] = []
    if energy:
        a, b = int(max(0.0, start - e_off) / hop), min(len(energy), int((end - e_off) / hop))
        seg = energy[a:b]
        if len(seg) >= 8:
            med = sorted(seg)[len(seg) // 2]
            for i in range(1, len(seg) - 1):
                v = seg[i]
                if v - med >= 5 and v >= seg[i - 1] and v >= seg[i + 1]:
                    t = i * hop
                    kind = "risada" if any(abs(t - x) <= 1.5 for x in laughs) else ("susto" if v - med >= 9 else "hype")
                    cands.append((v - med, t, kind))
    cands += [(8.0, t, "risada") for t in laughs]
    cands.sort(reverse=True)
    picked: list[dict] = []
    for forca, t, kind in cands:
        if t < 1.0 or t > dur - 1.0 or any(abs(t - p["t"]) < min_gap for p in picked):
            continue
        picked.append({"t": round(t, 2), "kind": kind, "forca": round(forca, 1)})
        if len(picked) >= max_n:
            break
    return sorted(picked, key=lambda p: p["t"])


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.glob("*") if p.suffix.lower() in EXTS) if folder.is_dir() else []


def sticker_for(kind: str, seed: float) -> Path | None:
    """Figurinha para o humor: primeiro as suas (pasta figurinhas/<humor>), senão os emojis incluídos."""
    files = _files(MINE / kind) or _files(ASSETS / kind)
    return random.Random(seed).choice(files) if files else None


def catalog() -> dict:
    return {k: {"suas": len(_files(MINE / k)), "padrao": len(_files(ASSETS / k))} for k in MOODS}
