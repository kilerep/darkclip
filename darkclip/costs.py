"""💰 Medidor de custo das IAs: soma o consumo REAL (tokens) devolvido pelas APIs em cada tarefa.

Preços em US$ por 1 milhão de tokens (entrada, saída). Atualize aqui se mudarem — fontes em docs/CUSTOS_IA.md.
"""
from __future__ import annotations

import threading

PRICES = {
    # Claude (tabela oficial cacheada em 2026-11)
    "claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50),
    "claude-fable-5-2": (8.00, 40.00),
    # Gemini (página de preços, 2026-11; 3.8 Flash dobra a partir de 2027-01-01)
    "gemini-4-hydrogen": (1.50, 7.50), "gemini-4-neon": (3.00, 15.00), "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.6-flash": (0.75, 3.75), "gemini-3.5-flash-lite": (0.30, 2.50), "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}
USD_BRL = 5.5  # só para exibir em reais (aproximado)

_lock = threading.Lock()
_usage: list[dict] = []


def reset() -> None:
    with _lock:
        _usage.clear()


def add(provider: str, model: str, input_tokens: int = 0, output_tokens: int = 0, free: bool = False,
        note: str = "") -> None:
    pin, pout = PRICES.get(model, (0.0, 0.0))
    usd = 0.0 if free else (input_tokens * pin + output_tokens * pout) / 1e6
    with _lock:
        _usage.append({"provider": provider, "model": model, "in": int(input_tokens or 0),
                       "out": int(output_tokens or 0), "usd": round(usd, 5), "free": free, "note": note})


def summary() -> dict:
    with _lock:
        items = list(_usage)
    by: dict[str, float] = {}
    for u in items:
        by[u["provider"]] = by.get(u["provider"], 0.0) + u["usd"]
    total = sum(by.values())
    return {"usd": round(total, 4), "brl": round(total * USD_BRL, 2), "by_provider": {k: round(v, 4) for k, v in by.items()},
            "calls": items}


def human(s: dict) -> str:
    if not s["calls"]:
        return "💰 Sem custo de IA (só sinais gratuitos)"
    parts = [f"{k.capitalize()} US$ {v:.3f}" for k, v in s["by_provider"].items()]
    free = [c for c in s["calls"] if c["free"]]
    if free:
        parts.append(f"{len(free)} análise(s) grátis")
    return f"💰 Custo de IA desta tarefa: US$ {s['usd']:.3f} (≈ R$ {s['brl']:.2f}) — " + " · ".join(parts)
