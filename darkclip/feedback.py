"""👍/👎 Avaliações dos clipes: o DarkClip aprende o gosto do dono.

Cada nota fica em data/feedback.json com o motivo e um trecho da fala. As notas viram exemplos
no pedido para a IA ("corte assim", "evite isso"), e alguns motivos ajustam regras automáticas,
por exemplo "Começa sem contexto" faz o corte recuar mais no começo.
"""
from __future__ import annotations

import json
import threading
import time
from collections import Counter

from . import config

FILE = config.DATA_DIR / "feedback.json"
_lock = threading.Lock()

GOOD = ["Boa reação", "Engraçado", "Gancho forte", "Bem editado", "História completa"]
BAD = ["Começa sem contexto", "Termina antes do fim", "Sem graça", "Enquadramento ruim",
       "Legenda errada", "Muito longo", "Muito curto"]


def load() -> list[dict]:
    if FILE.exists():
        try:
            return json.loads(FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return []


def _save(rows: list[dict]) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows[-500:], ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def _excerpt(job, clip: dict, words: int = 30) -> str:
    try:
        segs = json.loads((job.dir / "transcript.json").read_text(encoding="utf-8"))
    except Exception:
        return ""
    txt = " ".join(s["text"] for s in segs if s["end"] > clip.get("start", 0) and s["start"] < clip.get("end", 0))
    w = txt.split()
    return " ".join(w[:words]) + ("…" if len(w) > words else "")


def rate(job, idx: int, rating: int, reason: str = "") -> dict:
    """rating: 1 (gostei), -1 (não gostei) ou 0 (apagar a nota)."""
    clip = job.data["clips"][idx]
    reason = (reason or "").strip()[:160]
    with _lock:
        rows = [r for r in load() if not (r["job"] == job.id and r["clip"] == idx)]
        if rating:
            rows.append({
                "job": job.id, "clip": idx, "rating": 1 if rating > 0 else -1, "reason": reason,
                "title": clip.get("title", ""), "hook": clip.get("hook", ""),
                "duration": clip.get("duration"), "layout": (clip.get("render") or {}).get("layout"),
                "niche": (job.data.get("params") or {}).get("niche", ""),
                "excerpt": _excerpt(job, clip), "ts": time.time(),
            })
        _save(rows)
    if rating:
        clip["rating"], clip["rating_reason"] = (1 if rating > 0 else -1), reason
    else:
        clip.pop("rating", None)
        clip.pop("rating_reason", None)
    job.save()
    return clip


def reasons(rows: list[dict] | None = None) -> Counter:
    rows = load() if rows is None else rows
    return Counter(r["reason"] for r in rows if r.get("reason"))


def summary() -> dict:
    rows = load()
    good = sum(r["rating"] > 0 for r in rows)
    return {"total": len(rows), "good": good, "bad": len(rows) - good,
            "top_reasons": reasons(rows).most_common(6), "good_reasons": GOOD, "bad_reasons": BAD}


def examples_for_ai(limit: int = 5) -> str:
    """Bloco para o prompt da IA: exemplos recentes do que o dono gostou e do que não gostou."""
    rows = sorted(load(), key=lambda r: -r.get("ts", 0))
    if not rows:
        return ""
    out = ["GOSTO DO DONO (notas que ele deu a cortes anteriores; imite o que ganhou 👍 e evite o que ganhou 👎):"]
    for sign, label in ((1, "👍"), (-1, "👎")):
        for r in [r for r in rows if r["rating"] == sign][:limit]:
            why = f" — motivo: {r['reason']}" if r.get("reason") else ""
            ex = f" — fala: \"{r['excerpt'][:160]}\"" if r.get("excerpt") else ""
            out.append(f"{label} \"{r.get('title', '')[:70]}\" ({r.get('duration') or '?'}s){why}{ex}")
    bad = Counter(r["reason"] for r in rows if r["rating"] < 0 and r.get("reason"))
    if bad:
        out.append("Problemas mais apontados: " + ", ".join(f"{k} ({v}x)" for k, v in bad.most_common(4)))
    return "\n".join(out)


def lead_in_seconds(default: float = 8.0) -> float:
    """Se o dono reclama muito de "Começa sem contexto", os cortes recuam mais no começo."""
    rows = load()
    bad = [r for r in rows if r["rating"] < 0]
    n = sum(r.get("reason") == "Começa sem contexto" for r in bad)
    return default + 4.0 if n >= 2 and n / max(1, len(bad)) >= 0.25 else default
