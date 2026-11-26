"""💡 O que está "na boca do povo" agora (Google Trends do Brasil) → ideias de vídeo para o seu nicho.

- Fonte: feed RSS público do Google Trends (sem chave), atualizado ao longo do dia.
- Com IA (Claude ou Ollama): filtra o que combina com a sua página e devolve ideias prontas
  (título, gancho, ângulo, formato, subtema). Sem IA: lista os assuntos com ângulos-modelo.
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

NS = {"ht": "https://trends.google.com/trending/rss"}
_cache: dict[str, tuple[float, list[dict]]] = {}

IDEAS_SCHEMA = {
    "type": "object",
    "properties": {"ideas": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "título do vídeo, até 60 caracteres, curiosidade sem mentir"},
            "hook": {"type": "string", "description": "primeira frase falada (gancho de 2 segundos)"},
            "angle": {"type": "string", "description": "o ângulo ORIGINAL: o que você explica/conta que a notícia não conta"},
            "format": {"type": "string", "description": "ex.: Entenda em 60s, Você sabia?, Lista de 5, História real, Série Parte 1"},
            "subtheme": {"type": "string", "description": "qual dos subtemas da página"},
            "trend": {"type": "string", "description": "assunto em alta que inspirou (ou vazio se for ideia perene)"},
            "risk": {"type": "string", "description": "cuidado (tragédia recente, pessoa real, direito autoral) ou vazio"},
        },
        "required": ["title", "hook", "angle", "format", "subtheme", "trend", "risk"],
        "additionalProperties": False}}},
    "required": ["ideas"],
    "additionalProperties": False,
}

TEMPLATES = ["Entenda em 60 segundos: {t}", "O que ninguém te contou sobre {t}", "{t}: 3 fatos que explicam tudo",
             "Por que todo mundo está falando de {t}?"]


def fetch(geo: str = "BR", ttl: int = 900) -> list[dict]:
    """Assuntos em alta: [{topic, traffic, news:[{title,url,source}], picture}] (cache de 15 min)."""
    hit = _cache.get(geo)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    req = Request(f"https://trends.google.com/trending/rss?geo={geo}", headers={"User-Agent": "Mozilla/5.0 DarkClip"})
    with urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    items = []
    for it in root.iter("item"):
        news = [{"title": n.findtext("ht:news_item_title", default="", namespaces=NS).strip(),
                 "url": n.findtext("ht:news_item_url", default="", namespaces=NS),
                 "source": n.findtext("ht:news_item_source", default="", namespaces=NS)}
                for n in it.findall("ht:news_item", NS)]
        traffic = it.findtext("ht:approx_traffic", default="", namespaces=NS)
        items.append({"topic": it.findtext("title", default="").strip(), "traffic": traffic,
                      "traffic_n": int(re.sub(r"\D", "", traffic) or 0), "news": news[:3],
                      "picture": it.findtext("ht:picture", default="", namespaces=NS)})
    items.sort(key=lambda x: -x["traffic_n"])
    _cache[geo] = (time.time(), items)
    return items


def ideas(niche: str, subthemes: list[str] | None = None, n: int = 10, geo: str = "BR") -> dict:
    """Ideias de vídeo combinando os assuntos do dia com a identidade da página."""
    from . import ai
    try:
        trends = fetch(geo)
    except Exception as e:  # sem internet / Google fora: segue só com ideias perenes
        trends, err = [], str(e)
    else:
        err = None
    if not ai.has_llm():
        out = [{"title": TEMPLATES[i % len(TEMPLATES)].format(t=t["topic"]), "hook": "", "angle":
                (t["news"][0]["title"] if t["news"] else ""), "format": "Entenda em 60s", "subtheme": "",
                "trend": t["topic"], "risk": ""} for i, t in enumerate(trends[:n])]
        return {"ideas": out, "trends": trends, "engine": "modelos", "error": err}
    lines = "\n".join(f"- {t['topic']} ({t['traffic']} buscas): " + " | ".join(x["title"] for x in t["news"][:2])
                      for t in trends[:25])
    prompt = (
        f"Minha página/canal dark: {niche or 'curiosidades e histórias'}.\n"
        f"Subtemas da página (mesma identidade): {', '.join(subthemes or []) or 'escolha 3 subtemas coerentes'}.\n\n"
        f"ASSUNTOS EM ALTA HOJE NO BRASIL (Google Trends):\n{lines or '(indisponível)'}\n\n"
        f"Crie {n} ideias de vídeo curto (30–90 s, narrado, sem aparecer). Regras:\n"
        "- pelo menos metade aproveita um assunto em alta que COMBINE com a página; não force assunto que não combina;\n"
        "- o restante são ideias perenes do nicho (funcionam em qualquer época);\n"
        "- conteúdo ORIGINAL: explicar, contextualizar, contar a história por trás — nunca só repostar a notícia;\n"
        "- nada de inventar fatos; tragédia recente e pessoas reais pedem respeito (marque em 'risk');\n"
        "- varie os formatos e distribua entre os subtemas."
    )
    data = ai._ask_json(prompt, IDEAS_SCHEMA, max_tokens=8000)
    return {"ideas": data.get("ideas", []), "trends": trends,
            "engine": "claude" if ai.config.HAS_CLAUDE else "ollama", "error": err}
