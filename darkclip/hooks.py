"""🎣 Ganchos e finais: o que prende a pessoa no começo e faz ela assistir de novo no fim.

Tipos de gancho (os primeiros 1-3 segundos) e de final que a IA conhece e que o DarkClip sabe montar:
- ⏩ Prévia (flash-forward): abre com 2-3 s do melhor momento e volta ao começo ("como ele chegou nisso?").
- ❓ Pergunta, ⏳ Espera até o fim, 😱 Afirmação chocante, 🎬 POV/situação: muda o texto do gancho no topo.
- 🎮 Começa na ação: sem texto; o corte já abre no meio da ação.
- 🔁 Loop: o fim se mistura com o primeiro quadro; o replay não parece recomeço.
Fontes da pesquisa em docs/GANCHOS.md.
"""
from __future__ import annotations

import random
import re

HOOK_TYPES: dict[str, dict] = {
    "previa": {"nome": "⏩ Prévia do melhor momento",
               "quando": "o desfecho é forte e acontece no fim (explosão, falha, susto, reação)",
               "textos": ["COMO ELE CHEGOU NISSO?", "COMO ISSO ACONTECEU?", "VOLTA UM POUCO…", "ATÉ CHEGAR AQUI…"]},
    "pergunta": {"nome": "❓ Pergunta",
                 "quando": "o trecho responde algo que dá curiosidade",
                 "textos": ["VOCÊ FARIA ISSO?", "O QUE ELE VAI FAZER?", "ADIVINHA O QUE ACONTECE", "VAI DAR CERTO?"]},
    "espera": {"nome": "⏳ Espera até o fim",
               "quando": "a graça está no final e o começo é mais calmo",
               "textos": ["ESPERA O FINAL…", "NÃO PULA O FINAL", "O FINAL É O MELHOR", "PRESTA ATENÇÃO NO FINAL"]},
    "choque": {"nome": "😱 Afirmação chocante",
               "quando": "aconteceu algo absurdo que dá para dizer numa frase",
               "textos": ["ISSO NÃO DEVIA ACONTECER", "ELE FEZ O IMPOSSÍVEL", "NINGUÉM ESPERAVA ISSO", "DEU TUDO ERRADO"]},
    "pov": {"nome": "🎬 POV / situação",
            "quando": "a cena é uma situação com a qual o público se identifica",
            "textos": ["POV: VOCÊ TENTANDO AJUDAR", "QUANDO VOCÊ ACHA QUE DEU CERTO", "POV: PRIMEIRO DIA NO JOGO"]},
    "acao": {"nome": "🎮 Começa na ação",
             "quando": "o trecho já começa com algo acontecendo; texto só atrapalharia",
             "textos": []},
}
HOOK_MODES = ["auto", *HOOK_TYPES, "nenhum"]
ENDINGS = {"auto": "🤖 Automático (loop quando o fim emenda bem)", "loop": "🔁 Loop (o fim emenda no começo)",
           "normal": "⏹️ Normal"}


def catalog() -> dict:
    return {"hooks": [{"id": k, "nome": v["nome"], "quando": v["quando"], "exemplos": v["textos"][:3]}
                      for k, v in HOOK_TYPES.items()],
            "endings": [{"id": k, "nome": v} for k, v in ENDINGS.items()]}


def prompt_rules(forced: str | None = None) -> str:
    """Bloco para o pedido da IA: ensina os tipos de gancho e de final."""
    tipos = "\n".join(f"  · {k}: {v['nome']}, quando {v['quando']}" for k, v in HOOK_TYPES.items())
    txt = ("\nGANCHO E FINAL (retenção):\n"
           f"- hook_type: escolha o gancho que mais prende para CADA trecho:\n{tipos}\n"
           "- hook: o texto do gancho, combinando com o hook_type (até 6 palavras, sem emoji; vazio se 'acao');\n"
           "- teaser_start/teaser_end: o momento MAIS forte do trecho (1,5 a 3 s, em segundos do vídeo original, "
           "dentro do trecho e depois de 30% dele) para abrir o vídeo como prévia; use 0 e 0 se não houver;\n"
           "- loop_ok: true se a última frase emenda naturalmente na primeira (o replay parece continuação);\n"
           "- prefira 'previa' quando o clímax está no fim; 'acao' quando o trecho já abre agitado; "
           "varie os tipos entre os trechos.\n")
    if forced and forced in HOOK_TYPES:
        txt += f"- O DONO PEDIU o gancho '{forced}' ({HOOK_TYPES[forced]['nome']}) em todos os trechos.\n"
    return txt


def heuristic_text(hook_type: str, fallback: str = "", seed: float | None = None) -> str:
    texts = HOOK_TYPES.get(hook_type, {}).get("textos") or []
    return random.Random(seed).choice(texts) if texts else ("" if hook_type == "acao" else fallback)


def decide(clip: dict, mode: str, ending: str, loud, words, hook_on: bool = True, energy=None,
           e_off: float = 0.0) -> dict:
    """Escolhe o gancho e o final de um corte. Devolve {hook_type, hook, teaser, teaser_text, loop}."""
    start, end = clip["start"], clip["end"]
    dur = end - start
    ai_type = clip.get("hook_type")
    ai_hook = clip.get("hook") or ""
    seed = round(start, 1)
    if mode == "nenhum" or not hook_on:
        htype = "nenhum"
    elif mode in HOOK_TYPES:
        htype = mode
    else:
        htype = ai_type
    teaser = None
    if htype in (None, "previa"):
        teaser = (valid_teaser(clip.get("teaser_start"), clip.get("teaser_end"), start, end)
                  or peak_window(energy, start - e_off, end - e_off) or pick_teaser(dur, loud, words))
        if htype is None:  # sem IA: prévia só quando há um momento forte num corte mais longo
            htype = "previa" if teaser and dur >= 25 else "texto"
        elif not teaser:
            htype = "espera"  # pediu prévia, mas não há momento forte: "espera o final" no lugar
    out = {"hook_type": htype, "hook": None, "teaser": None, "teaser_text": None}
    if htype == "previa":
        out["teaser"] = teaser
        out["teaser_text"] = ai_hook if ai_type == "previa" and ai_hook else heuristic_text("previa", seed=seed)
    elif htype in ("pergunta", "espera", "choque", "pov"):
        out["hook"] = ai_hook if ai_type == htype and ai_hook else heuristic_text(htype, ai_hook, seed=seed)
    elif htype == "texto":
        out["hook"] = ai_hook or None
    out["loop"] = ending == "loop" or (ending == "auto" and bool(clip.get("loop_ok")))
    return out


def peak_window(energy: list[float] | None, start: float, end: float, hop: float = 0.5,
                length: float = 2.4, min_db: float = 3.0) -> tuple[float, float] | None:
    """Janela mais alta da parte final do corte, comparada ao próprio corte (não ao vídeo todo:
    numa live de horas o volume muda muito). Tempo relativo ao corte; None se nada se destaca."""
    if not energy:
        return None
    a, b = int(start / hop), min(len(energy), int(end / hop))
    seg = energy[a:b]
    w = max(2, int(length / hop))
    if len(seg) < w * 3:
        return None
    med = sorted(seg)[len(seg) // 2]
    lo = int(len(seg) * 0.35)
    best, at = None, None
    for i in range(lo, len(seg) - w + 1):
        m = sum(seg[i:i + w]) / w
        if best is None or m > best:
            best, at = m, i
    if best is None or best - med < min_db:
        return None
    return round(at * hop, 2), round(at * hop + w * hop, 2)


def pick_teaser(dur: float, loud: list[tuple[float, float]] | None, words: list[dict] | None = None,
                length: float = 2.4) -> tuple[float, float] | None:
    """Melhor momento para a prévia (tempo relativo ao corte): o som mais intenso na parte final;
    senão, uma frase exclamada ou risada perto do fim. None se não achar nada forte."""
    if dur < 12:
        return None
    lo = dur * 0.35
    cands = [(b - a, a, b) for a, b in (loud or []) if b > lo and a < dur - 0.5]
    if cands:
        _, a, b = max(cands)
        mid = (max(a, lo) + min(b, dur)) / 2
    else:
        strong = [w for w in (words or []) if w["start"] > lo and (w["word"].endswith("!") or
                  re.search(r"k{3,}|haha|risos", w["word"].lower()))]
        if not strong:
            return None
        mid = strong[-1]["start"]
    s = max(lo, min(mid - length / 2, dur - length - 0.2))
    return (round(s, 2), round(s + length, 2)) if s + length <= dur else None


def valid_teaser(t0: float | None, t1: float | None, start: float, end: float) -> tuple[float, float] | None:
    """Confere a prévia sugerida pela IA (segundos do vídeo original) e devolve relativo ao corte."""
    if not t0 or not t1 or t1 <= t0:
        return None
    a, b = t0 - start, t1 - start
    dur = end - start
    if a < dur * 0.25 or b > dur or not 1.0 <= b - a <= 4.0:
        return None
    return round(a, 2), round(b, 2)
