"""Inteligência do DarkClip: escolhe os momentos virais, escreve títulos/descrições
e roteiros de histórias dark. Usa Claude quando há chave; senão, heurística local."""
from __future__ import annotations

import json
import re

from . import config

CLIP_SCHEMA = {
    "type": "object",
    "properties": {
        "clips": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "number", "description": "segundo de início no vídeo original"},
                    "end": {"type": "number", "description": "segundo de fim no vídeo original"},
                    "score": {"type": "integer", "description": "potencial viral de 0 a 100"},
                    "hook": {"type": "string", "description": "texto curto (máx 6 palavras, sem emoji) que aparece no topo nos 3 primeiros segundos, combinando com hook_type"},
                    "title": {"type": "string", "description": "título do Short, até 70 caracteres, curiosidade/mistério"},
                    "description": {"type": "string", "description": "descrição de 1-2 frases + chamada para seguir"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string", "description": "por que esse trecho prende a atenção"},
                    "emphasis": {"type": "array", "items": {"type": "string"},
                                 "description": "3-8 palavras-chave ditas no trecho para destacar em cor na legenda"},
                    "grades": {
                        "type": "object",
                        "description": "notas 0-100 por critério (estilo OpusClip)",
                        "properties": {
                            "hook": {"type": "integer", "description": "os 2 primeiros segundos prendem?"},
                            "flow": {"type": "integer", "description": "a ideia anda sem buracos até o desfecho?"},
                            "value": {"type": "integer", "description": "é útil, engraçado ou emociona?"},
                            "trend": {"type": "integer", "description": "conversa com o nicho/assuntos do momento?"},
                        },
                        "required": ["hook", "flow", "value", "trend"],
                        "additionalProperties": False,
                    },
                    "payoff": {"type": "string", "description": "a frase exata de desfecho/punchline que fecha o clipe"},
                    "hook_type": {"type": "string", "enum": ["previa", "pergunta", "espera", "choque", "pov", "acao"],
                                  "description": "tipo de gancho que mais prende neste trecho"},
                    "teaser_start": {"type": "number", "description": "início do momento mais forte (prévia), 0 se não houver"},
                    "teaser_end": {"type": "number", "description": "fim do momento mais forte (prévia), 0 se não houver"},
                    "loop_ok": {"type": "boolean", "description": "a última frase emenda naturalmente na primeira?"},
                },
                "required": ["start", "end", "score", "hook", "title", "description", "hashtags", "reason", "emphasis",
                             "grades", "payoff", "hook_type", "teaser_start", "teaser_end", "loop_ok"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["clips"],
    "additionalProperties": False,
}

STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string", "description": "frase de abertura, até 6 palavras, aparece no topo"},
        "script": {"type": "string", "description": "narração completa, 110-150 palavras, frases curtas"},
        "description": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "emphasis": {"type": "array", "items": {"type": "string"}, "description": "4-8 palavras do roteiro para destacar"},
    },
    "required": ["title", "hook", "script", "description", "hashtags", "emphasis"],
    "additionalProperties": False,
}

SYSTEM = (
    "Você é editor-chefe de um canal 'dark' (sem rosto) de YouTube Shorts em português do Brasil, "
    "especializado em retenção: gancho forte nos 2 primeiros segundos, curiosidade, mistério, "
    "revelação no final, sem enrolação. Escreva títulos sem clickbait mentiroso."
)


def _client():
    import anthropic
    return anthropic.Anthropic()


_ON_RETRY = None   # pipeline pode registrar aqui uma função para mostrar "Gemini ocupado…" no log


def has_llm() -> bool:
    return config.HAS_CLAUDE or bool(config.OLLAMA_MODEL) or config.HAS_GEMINI


def llm_name() -> str:
    return "claude" if config.HAS_CLAUDE else "ollama" if config.OLLAMA_MODEL else "gemini"


def _ask_ollama(prompt: str, schema: dict) -> dict:
    """IA local (Ollama), sem custo e sem internet. Saída JSON forçada pelo schema."""
    from urllib.request import ProxyHandler, Request, build_opener
    body = {"model": config.OLLAMA_MODEL, "stream": False, "format": schema,
            "options": {"temperature": 0.2, "num_ctx": 32768},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    req = Request(config.OLLAMA_URL.rstrip("/") + "/api/chat", data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json"})
    with build_opener(ProxyHandler({})).open(req, timeout=1800) as r:  # Ollama é local: sem proxy
        data = json.loads(r.read())
    return json.loads(data["message"]["content"])


def _ask_json(prompt: str | list, schema: dict, max_tokens: int = 16000) -> dict:
    if not config.HAS_CLAUDE and config.OLLAMA_MODEL:
        return _ask_ollama(prompt, schema)
    if not config.HAS_CLAUDE and config.HAS_GEMINI:  # sem Claude: o Gemini lê a transcrição e escolhe
        from . import gemini
        if not isinstance(prompt, str):
            prompt = "\n".join(b.get("text", "") for b in prompt if isinstance(b, dict))
        return gemini.ask_text(SYSTEM + "\n\n" + prompt, schema, on_retry=_ON_RETRY)
    client = _client()
    kwargs = dict(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": config.CLAUDE_EFFORT, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
    )
    # Fallback automático do servidor caso o modelo recuse (só modelos 5.x suportam).
    if re.match(r"claude-(opus-5|sonnet-5-5|fable-5)", config.CLAUDE_MODEL):
        resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    else:
        resp = client.messages.create(**kwargs)
    try:  # 💰 registra o consumo real
        from . import costs
        u = resp.usage
        costs.add("claude", getattr(resp, "model", config.CLAUDE_MODEL) or config.CLAUDE_MODEL,
                  (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
                  + (getattr(u, "cache_read_input_tokens", 0) or 0) // 10, u.output_tokens or 0)
    except Exception:
        pass
    if resp.stop_reason == "refusal":
        raise RuntimeError("O modelo recusou o pedido.")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


# ---------------------------------------------------------------- fronteiras do corte
# Muleta de abertura: trecho que só tem isso no começo é enrolação, não gancho.
FILLER = {"e", "mas", "então", "entao", "aí", "ai", "tipo", "né", "ne", "ah", "ahn", "hum", "uhm",
          "bom", "bem", "olha", "assim", "cara", "mano", "velho", "eh", "é", "uh", "um", "hã", "ha",
          "so", "well", "like", "okay", "ok"}


def _clean(text: str) -> str:
    return re.sub(r"\(.*?\)|\[.*?\]|♪", "", text or "").strip()


def _trim_opening(segs: list[dict], start: float, end: float, min_s: float) -> float:
    """Tira a enrolação do começo: pula o primeiro trecho quando ele é só muleta
    ("ah, então...", "tipo assim") e ainda sobra clipe suficiente. Nunca mexe no fim."""
    for _ in range(3):   # no máximo 3 trechos de enrolação seguidos
        idx = [k for k, s in enumerate(segs) if s["end"] > start + 0.05 and s["start"] < end]
        if not idx:
            return start
        first = segs[idx[0]]
        words = [w.lower().strip(".,!?;:\"'…") for w in _clean(first["text"]).split()]
        words = [w for w in words if w]
        if not words or len(words) > 4 or not all(w in FILLER for w in words):
            return start
        if end - first["end"] < min_s:      # cortar isso deixaria o clipe curto demais
            return start
        start = round(first["end"], 2)
    return start


def _extend_tail(energy: list[float] | None, start: float, end: float, limit: float,
                 segs: list[dict] | None = None,
                 hop: float = 0.5, look: float = 3.0, rise: float = 5.0, fall: float = 2.0) -> float:
    """Não corta em cima do desfecho sonoro: se logo depois do fim ainda há um pico de som
    (risada, grito, impacto) acima da mediana DO PRÓPRIO CORTE, estende até o som cair.
    Só aumenta o fim, nunca diminui, e respeita `limit`.

    rise=5 dB é o mesmo limiar que `reacoes.py` usa para achar reação. Medido num vídeo de ação
    real (15 janelas de 25 s): com 3 dB dispara em 14 delas (qualquer barulho serve), com 5 dB em 6
    (média +1,25 s) e com 8 dB em nenhuma.

    Pico que é FALA NOVA (uma frase que começa depois do fim) não conta: quem termina a frase em
    curso é `_finish_sentence`. Sem essa trava, medido no mesmo vídeo, os 6 disparos eram todos
    frase seguinte, e o corte crescia uma frase por vez em vez de pegar a reação.
    """
    if not energy or limit <= end:
        return end
    a, b = int(start / hop), int(end / hop)
    win = energy[a:b]
    if len(win) < 4:
        return end
    med = sorted(win)[len(win) // 2]
    stop = min(len(energy), int(min(limit, end + look) / hop))
    nova_fala = [(s["start"], s["end"]) for s in (segs or []) if s["start"] > end + 0.3]
    last = max((i for i in range(b, stop)
                if energy[i] - med >= rise
                and not any(a0 <= i * hop < b0 for a0, b0 in nova_fala)), default=None)
    if last is None:
        return end
    hard = min(len(energy), int(min(limit, end + look + 2.0) / hop))
    j = last
    while j < hard and energy[j] - med > fall:
        j += 1
    return round(min((j + 1) * hop + 0.2, limit), 2)


def _finish_sentence(segs: list[dict], end: float, limit: float, fwd: float = 4.0) -> float:
    """Termina a frase em curso em vez de cortar no meio dela (vale para os dois motores)."""
    idx = [k for k, s in enumerate(segs) if s["start"] < end <= s["end"] + 0.5]
    b = idx[-1] if idx else None
    if b is None:
        return end
    while (b + 1 < len(segs) and not segs[b]["text"].rstrip().endswith(_ENDS)
           and segs[b + 1]["start"] - segs[b]["end"] < 1.2
           and segs[b + 1]["end"] - end <= fwd and segs[b + 1]["end"] <= limit):
        b += 1
    return round(max(end, min(segs[b]["end"] + 0.25, limit)), 2)


def refine_edges(segs: list[dict], start: float, end: float, energy: list[float] | None,
                 min_s: float, max_s: float) -> tuple[float, float, dict]:
    """Ajusta as duas bordas do corte com os sinais reais, depois que o motor escolheu o trecho.

    Começo: tira a enrolação. Fim: termina a frase e não corta em cima de um pico de som.
    Devolve (início, fim, o que mudou) — o fim nunca encurta.
    """
    limit = start + max_s + 8
    s0, e0 = start, end
    start = _trim_opening(segs, start, end, min_s)
    end = _finish_sentence(segs, end, limit)
    end = max(end, _extend_tail(energy, start, end, limit, segs))
    mudou = {}
    if abs(start - s0) > 0.05:
        mudou["abertura"] = round(start - s0, 2)
    if abs(end - e0) > 0.05:
        mudou["desfecho"] = round(end - e0, 2)
    return start, end, mudou


def _snap(segs: list[dict], start: float, end: float) -> tuple[float, float]:
    """Ajusta início/fim para bordas de frase (não corta palavra no meio)."""
    starts = [s["start"] for s in segs]
    ends = [s["end"] for s in segs]
    if starts:
        start = min(starts, key=lambda t: abs(t - start))
        end = min(ends, key=lambda t: abs(t - end))
    return round(max(0.0, start - 0.15), 2), round(end + 0.25, 2)


# ---------------------------------------------------------------- seleção de clipes
def select_clips(segs: list[dict], n: int = 5, min_s: int = 20, max_s: int = 58, title: str = "",
                 niche: str = "", heatmap=None, energy=None, chapters=None, comments=None,
                 visual=None, request: str = "", hook_mode: str = "auto") -> tuple[list[dict], str]:
    """Escolhe os trechos combinando todos os sinais disponíveis.

    comments: análise de comments.analyze()  · visual: momentos do Gemini (gemini.find_moments)
    request : pedido do usuário ("ache a parte sobre X")
    """
    from . import comments as cm
    from . import signals
    global _NICHE
    _NICHE = niche or ""
    ctx = dict(heatmap=heatmap, energy=energy, chapters=chapters, comments=comments, visual=visual, hook_mode=hook_mode)
    clips, engine = None, "heuristica"
    if has_llm():
        name = llm_name()
        try:
            clips, engine = _select_claude(segs, n, min_s, max_s, title, niche, ctx, request), name
        except Exception as e:  # cai para o próximo motor se a IA falhar
            print(f"[ai] {name} indisponível ({e}).")
            if _ON_RETRY:  # mostra o motivo no "Ver detalhes"
                try:
                    from .config import redact
                    _ON_RETRY(f"⚠️ {name.capitalize()} não conseguiu escolher os cortes ({redact(str(e))[:160]}): "
                              "usando as regras automáticas")
                except Exception:
                    pass
    if clips is None and visual and visual.get("moments"):
        clips, engine = _from_visual(segs, visual, n, min_s, max_s), "gemini"
    if clips is None:
        clips = _select_heuristic(segs, n, min_s, max_s, title, heatmap, energy, comments, request)
    # refino das fronteiras: vale para todos os motores, depois que o trecho já foi escolhido
    ordem = sorted(clips, key=lambda c: c["start"])
    for i, c in enumerate(ordem):
        try:
            s, e, mudou = refine_edges(segs, c["start"], c["end"], energy, min_s, max_s)
            if i + 1 < len(ordem):          # não invade o corte seguinte
                e = min(e, ordem[i + 1]["start"])
            if e - s >= min_s * 0.6:
                c["start"], c["end"] = s, e
                if mudou:
                    c["edges"] = mudou
        except Exception as err:            # borda é opcional: nunca derruba o job
            print(f"[ai] refino de bordas falhou ({err}); usando o trecho original.")
    for c in clips:  # nota final = IA + sinais reais do público e do áudio
        heat = signals.heat_at(heatmap, c["start"], c["end"])
        en = signals.energy_score(energy, c["start"], c["end"])
        talk = cm.attention_at(comments, c["start"], c["end"])
        vis = signals.visual_at(visual, c["start"], c["end"])
        c["signals"] = {"ai": c["score"], "heat": None if heat is None else round(heat, 2), "energy": en,
                        "comments": talk, "visual": vis, **signals.text_signals(segs, c["start"], c["end"])}
        c["score"] = signals.blend_score(c["score"], heat, en, talk, vis, c["signals"].get("wpm"))
        c.setdefault("emphasis", [])
    clips.sort(key=lambda c: -c["score"])
    return clips, engine


def _hook_rules(mode: str | None) -> str:
    try:
        from . import hooks
        return hooks.prompt_rules(mode if mode not in (None, "auto", "nenhum") else None)
    except Exception:
        return ""


def _channel_prefs() -> str:
    try:
        from .central import preferences_for_ai
        pref = preferences_for_ai()
        return ("\n\n" + pref) if pref else ""
    except Exception:
        return ""


def _context_block(ctx: dict) -> str:
    """Resumo dos sinais externos para o prompt."""
    out = []
    chap = "\n".join(f"- {c['start']:.0f}s {c['title']}" for c in (ctx.get("chapters") or []) if c.get("start") is not None)
    if chap:
        out.append(f"CAPÍTULOS:\n{chap}")
    com = ctx.get("comments") or {}
    if com.get("peaks"):
        lines = []
        for p in com["peaks"][:10]:
            ex = " | ".join(c["text"].replace("\n", " ")[:90] for c in p["comments"][:2])
            lines.append(f"- {p['start']:.0f}-{p['end']:.0f}s atenção {int(p['score'] * 100)} "
                         f"({p['mentions']} menções): {ex}")
        out.append("MOMENTOS MAIS CITADOS NOS COMENTÁRIOS (💬):\n" + "\n".join(lines))
    vis = ctx.get("visual") or {}
    if vis.get("moments"):
        lines = [f"- {m['start']:.0f}-{m['end']:.0f}s nota {m['score']}: {m['what']}" for m in vis["moments"][:15]]
        out.append("MOMENTOS QUE A IA DE VÍDEO (Gemini) VIU — imagem + áudio (👁️):\n" + "\n".join(lines))
        if vis.get("summary"):
            out.append(f"RESUMO VISUAL: {vis['summary']}")
    return "\n\n".join(out)


def _select_claude(segs, n, min_s, max_s, title, niche, ctx, request=""):
    from . import signals
    prompt = (
        f"Vídeo: {title}\nNicho do canal: {niche or 'curiosidades, mistérios, histórias'}\n"
        + (f"PEDIDO DO USUÁRIO (prioridade máxima): {request}\n" if request else "")
        + f"\nEscolha os {n} melhores trechos para Shorts. Regras:\n"
        f"- cada trecho entre {min_s} e {max_s} segundos, sem sobreposição;\n"
        "- deve fazer sentido sozinho: nada de 'como eu disse', pronomes sem referente ou ideia pela metade;\n"
        "- os 2 primeiros segundos precisam prender: comece na frase mais forte (pergunta, afirmação chocante, "
        "conflito, número surpreendente), mesmo que isso pule uma introdução;\n"
        "- O FIM PRECISA CONTER O DESFECHO: inclua a punchline/conclusão inteira (escreva-a em 'payoff'). "
        "Cortar antes do desfecho é o pior erro possível; se não couber, escolha outro trecho;\n"
        "- se faltar contexto, recue o INÍCIO; nunca encurte o fim;\n"
        "- não comece com pronome sem referente, conjunção ou muleta (\"e\", \"mas\", \"então\", \"tipo\", \"né\", \"aí\");\n"
        "- ignore introduções, pedidos de inscrição, patrocínio e despedidas;\n"
        "- varie: não escolha dois trechos sobre o mesmo assunto;\n"
        "- o gancho deve combinar com o que aparece na tela e com o que é dito (sem prometer o que o trecho não entrega);\n"
        "- sinais: 🔥 = trecho que o público mais reassistiu; 💬 = trecho citado nos comentários; "
        "👁️ = momento visual forte visto pela IA de vídeo; ⚡ = áudio intenso; 😂 = risada. "
        "Sinais do público (🔥 💬) valem mais que a sua opinião;\n"
        "- grades: hook, flow, value, trend de 0 a 100; score = sua nota geral honesta (90+ só se excepcional);\n"
        "- use os tempos da transcrição; ordene do maior para o menor score.\n\n"
        + _hook_rules(ctx.get("hook_mode")) + _context_block(ctx) + _channel_prefs()
        + f"\n\nTRANSCRIÇÃO (segundos):\n{signals.annotate_transcript(segs, ctx.get('heatmap'), ctx.get('energy'), ctx.get('comments'), ctx.get('visual'))}"
    )
    data = _ask_json(prompt, CLIP_SCHEMA)
    clips = []
    for c in data["clips"]:
        s, e = _snap(segs, float(c["start"]), float(c["end"]))
        e = _extend_to_payoff(segs, e, c.get("payoff", ""), s + max_s + 8)
        if e - s < min_s * 0.6:
            e = s + min_s
        c["start"], c["end"] = s, e
        clips.append(c)
    return _dedupe(clips)[:n]


def _extend_to_payoff(segs: list[dict], end: float, payoff: str, limit: float) -> float:
    """Se a frase de desfecho cair depois do fim escolhido, estende o clipe até ela (sem passar do limite)."""
    from .comments import _words
    pw = set(_words(payoff))
    if len(pw) < 2:
        return end
    for s in segs:
        if s["start"] < end - 15 or s["start"] > limit:
            continue
        if len(pw & set(_words(s["text"]))) / len(pw) >= 0.6 and s["end"] + 0.25 > end:
            return round(min(s["end"] + 0.25, limit), 2)
    return end


def _from_visual(segs, visual, n, min_s, max_s):
    """Sem Claude: usa os momentos do Gemini, ajustados às bordas de frase."""
    out = []
    for m in sorted(visual["moments"], key=lambda m: -m["score"]):
        s, e = _snap(segs, m["start"], max(m["end"], m["start"] + min_s)) if segs else (m["start"], m["end"])
        e = min(e, s + max_s)
        if any(not (e <= o["start"] or s >= o["end"]) for o in out):
            continue
        out.append({"start": s, "end": e, "score": int(m["score"]), "hook": m.get("hook", "")[:60].upper(),
                    "title": m.get("title") or m["what"][:70], "description": m["what"],
                    "hashtags": ["#shorts"], "reason": "IA de vídeo (Gemini): " + m["what"],
                    "emphasis": [], "grades": None, "payoff": ""})
        if len(out) >= n:
            break
    return out


BAD_START = {"e", "mas", "então", "entao", "aí", "ai", "tipo", "né", "porque", "depois", "na", "também", "tambem",
             "ou", "que", "isso", "ele", "ela", "eles", "elas", "and", "but", "so", "because", "then", "um", "uh", "é"}

HOOK_WORDS = {
    "segredo", "nunca", "ninguém", "ninguem", "mistério", "misterio", "verdade", "morte", "morreu", "assustador",
    "estranho", "impossível", "impossivel", "proibido", "desapareceu", "real", "chocante", "incrível", "incrivel",
    "sabia", "descobriu", "escondido", "perigoso", "medo", "sinistro", "bizarro", "inexplicável", "polícia",
    "crime", "fantasma", "caso", "revelou", "ninguém", "dinheiro", "milhões", "bilhões", "primeiro", "último",
    "secret", "never", "nobody", "truth", "died", "creepy", "weird", "impossible", "found", "hidden", "dangerous",
}


_ENDS = (".", "!", "?", "…")


def _with_context(segs: list[dict], start: float, end: float, limit: float,
                  back: float = 8.0, fwd: float = 6.0) -> tuple[float, float]:
    """Dá contexto ao corte: recua até o começo da ideia (se a frase anterior está colada e
    não terminou) e termina a última frase. Evita clipe "caído de paraquedas"."""
    idx = [k for k, sg in enumerate(segs) if sg["end"] > start and sg["start"] < end]
    if not idx:
        return start, end
    a, b = idx[0], idx[-1]
    # recua: enquanto o trecho anterior estiver colado (<1,2 s) e não fechar a frase
    while a > 0 and start - segs[a - 1]["start"] <= back and end - segs[a - 1]["start"] <= limit:
        prev = segs[a - 1]
        cur = re.sub(r"\(.*?\)|\[.*?\]|♪", "", segs[a]["text"]).strip()
        fw = cur.split()[0].lower().strip(",.") if cur.split() else ""
        glued = segs[a]["start"] - prev["end"] < 1.2
        unfinished = not prev["text"].rstrip().endswith(_ENDS) or cur[:1].islower() or fw in BAD_START
        if not (glued and unfinished):
            break
        a -= 1
    new_start = min(start, segs[a]["start"])
    # avança: termina a frase em curso
    while (b + 1 < len(segs) and not segs[b]["text"].rstrip().endswith(_ENDS)
           and segs[b + 1]["start"] - segs[b]["end"] < 1.2 and segs[b + 1]["end"] - end <= fwd
           and segs[b + 1]["end"] - new_start <= limit):
        b += 1
    return round(max(0.0, new_start - 0.15), 2), round(max(end, segs[b]["end"] + 0.25), 2)


def _select_heuristic(segs, n, min_s, max_s, title, heatmap=None, energy=None, comments=None, request=""):
    from . import comments as cm
    from . import signals
    stem = lambda ws: {w[:5] for w in ws}            # radical: desenh(ava/ar/o)
    req = stem(cm._words(request)) if request else set()
    if not segs:
        return []
    target = (min_s + max_s) / 2
    cands = []
    for i, s in enumerate(segs):
        start, j, words = s["start"], i, []
        while j < len(segs) and segs[j]["end"] - start <= max_s:
            words += segs[j]["text"].lower().split()
            j += 1
            dur = segs[j - 1]["end"] - start
            if dur < min_s:
                continue
            first = segs[i]["text"].lower()
            hook = sum(w.strip(".,!?\"'") in HOOK_WORDS for w in words)
            q = first.count("?") * 3 + sum(w.endswith(("?", "!")) for w in words)
            numbers = sum(bool(re.search(r"\d", w)) for w in words)
            density = len(words) / max(dur, 1)  # fala rápida = mais energia
            opener = 4 * sum(w.strip(".,!?") in HOOK_WORDS for w in first.split())
            raw = re.sub(r"\(.*?\)|\[.*?\]|♪", "", segs[i]["text"]).strip()
            fw = raw.split()[0].lower().strip(",.") if raw.split() else ""
            if raw[:1].islower() or fw in BAD_START:  # começo no meio da frase ou com muleta/conjunção
                opener -= 15
            closing = 2 if segs[j - 1]["text"].rstrip().endswith((".", "!", "?")) else 0
            score = hook * 2 + q + numbers * 0.5 + density * 2 + opener + closing - abs(dur - target) * 0.05
            heat = signals.heat_at(heatmap, start, segs[j - 1]["end"])
            if heat is not None:
                score += heat * 12
            en = signals.energy_score(energy, start, segs[j - 1]["end"])
            if en is not None:  # gameplay: os melhores momentos são os mais barulhentos (grito, risada, explosão)
                score += en * 12
            talk = cm.attention_at(comments, start, segs[j - 1]["end"])
            if talk:
                score += talk * 10
            if req:  # pedido do usuário: trechos que falam do assunto pedido valem muito mais
                hits = len(req & stem(cm._words(" ".join(words))))
                score += 25 * hits if hits else -10
            clean = re.sub(r"\(.*?\)|\[.*?\]|♪", "", segs[i]["text"]).strip()
            cands.append((score, start, segs[j - 1]["end"], clean or segs[i]["text"]))
    cands.sort(reverse=True)
    if cands:  # nota relativa ao próprio vídeo (z-score) para não saturar em 99
        vals = [c[0] for c in cands]
        mu = sum(vals) / len(vals)
        sd = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5 or 1.0
    else:
        mu, sd = 0.0, 1.0
    try:  # o dono reclamou de cortes sem contexto? recua mais no começo
        from .feedback import lead_in_seconds
        lead = lead_in_seconds()
    except Exception:
        lead = 8.0
    picked: list[dict] = []
    for score, s, e, first in cands:
        if any(not (e <= p["start"] or s >= p["end"]) for p in picked):
            continue
        s2, e2 = _with_context(segs, *_snap(segs, s, e), max_s + 10, back=lead)
        if any(not (e2 <= p["start"] or s2 >= p["end"]) for p in picked):
            s2, e2 = _snap(segs, s, e)
        hook = " ".join(first.split()[:6]).upper()
        picked.append({
            "start": s2, "end": e2, "score": int(max(30, min(97, 60 + 37 * (score - mu) / ((cands[0][0] - mu) or 1)))), "hook": hook,
            "title": (first[:67] + "...") if len(first) > 70 else first,
            "description": f"Trecho de: {title}. Siga para mais!" if title else "Siga para mais!",
            "hashtags": _niche_tags(title),
            "reason": "heurística: palavras-gancho, perguntas, densidade de fala" + (", heatmap" if heatmap else ""),
            "emphasis": [w for w in first.split() if w.lower().strip(".,!?") in HOOK_WORDS or re.search(r"\d", w)],
        })
        if len(picked) >= n:
            break
    return picked


_NICHE = ""


def _niche_tags(title: str = "") -> list[str]:
    """Hashtags a partir do nicho informado (sem nicho: só #shorts)."""
    from .comments import _words
    words = _words(_NICHE)[:4]
    return ["#shorts"] + [f"#{w}" for w in words]


def _dedupe(clips):
    out = []
    for c in sorted(clips, key=lambda c: -c["score"]):
        if all(c["end"] <= o["start"] or c["start"] >= o["end"] for o in out):
            out.append(c)
    return out


# ---------------------------------------------------------------- roteiro dark
STORY_FORMATS = {
    "livre": "Estrutura: gancho chocante na 1ª frase -> contexto rápido -> 2 detalhes intrigantes -> "
             "revelação/twist -> pergunta final para comentários.",
    "top5": "Formato TOP 5: anuncie o ranking na 1ª frase, conte do 5º ao 1º (1-2 frases por item), "
            "guarde o mais surpreendente para o 1º lugar e termine perguntando qual o público colocaria em 1º.",
    "curiosidades": "Formato 3 CURIOSIDADES: gancho com a mais estranha, depois 3 curiosidades rápidas e "
                    "verificáveis (uma frase de impacto cada) e final pedindo para comentar qual não sabiam.",
    "quiz": "Formato QUIZ: faça a pergunta com 3 alternativas (A, B, C) logo na 1ª frase, diga 'pense rápido', "
            "dê 2 pistas curtas, revele a resposta com uma explicação curta e peça para comentarem se acertaram.",
    "desafio": "Formato DESAFIO: comece com 'só quem presta atenção acerta' ou similar, apresente o desafio, "
               "dê o contexto, faça a revelação e chame o público para marcar um amigo nos comentários.",
}


def write_story(topic: str, script: str | None = None, formato: str = "livre") -> dict:
    """Gera (ou embala) um roteiro de Short dark narrado."""
    if script:
        first = re.split(r"(?<=[.!?])\s", script.strip())[0]
        return {"title": topic or first[:70], "hook": " ".join(first.split()[:6]).upper(), "script": script.strip(),
                "description": topic or first, "hashtags": ["#shorts", "#misterio", "#curiosidades"],
                "emphasis": [w for w in script.split() if w.lower().strip(".,!?") in HOOK_WORDS or re.search(r"\d", w)]}
    if not has_llm():
        raise RuntimeError("Sem IA de texto (chave do Claude ou do Gemini, ou Ollama): cole o roteiro pronto no campo 'Roteiro'.")
    prompt = (
        f"Escreva um Short narrado (45-55 s) sobre: {topic}\n"
        + STORY_FORMATS.get(formato, STORY_FORMATS["livre"])
        + " Fatos verificáveis; se for lenda, diga que é lenda. "
        "Frases curtas para leitura em voz alta. Sem emojis no roteiro."
    )
    return _ask_json(prompt, STORY_SCHEMA, max_tokens=8000)
