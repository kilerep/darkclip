"""👁️ Gemini assiste o vídeo (imagem + áudio) e aponta os melhores momentos.

- Links do YouTube vão direto (sem baixar nada; gratuito em preview, até 8 h/dia no plano free).
- Arquivos locais sobem pela Files API (apagados logo depois; o Google expira em 48 h de qualquer forma).
- Vídeos longos (> 10 min) usam o modo "agentic": o modelo navega pela linha do tempo e gasta menos tokens.
- Saída em JSON estruturado (response_format).

Só biblioteca padrão (funciona no PC e no Termux). Chave grátis: https://aistudio.google.com/apikey
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config

API = "https://generativelanguage.googleapis.com"
INTERACTIONS = f"{API}/v1beta/interactions"
_YT = re.compile(r"^https?://(?:(?:www\.|m\.|music\.)?youtube\.com/(?:watch\?\S*\bv=|shorts/|live/)|youtu\.be/)\S+$", re.I)

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "resumo do vídeo em 2-3 frases"},
        "moments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "início no formato MM:SS ou H:MM:SS"},
                    "end": {"type": "string", "description": "fim no formato MM:SS ou H:MM:SS"},
                    "score": {"type": "integer", "description": "potencial de viralizar como Short, 0-100"},
                    "what": {"type": "string", "description": "o que acontece: o que se VÊ e o que se OUVE"},
                    "why": {"type": "string", "description": "por que prende (reação, ação, revelação, humor, emoção)"},
                    "hook": {"type": "string", "description": "gancho de até 6 palavras para o topo do Short"},
                    "title": {"type": "string", "description": "título curto para o Short"},
                    "visual": {"type": "string", "description": "dica de enquadramento: rosto, 2 pessoas, tela, ação, texto"},
                },
                "required": ["start", "end", "score", "what", "why", "hook", "title", "visual"],
            },
        },
    },
    "required": ["summary", "moments"],
}


class GeminiError(RuntimeError):
    pass


def is_youtube(url: str | None) -> bool:
    return bool(url and _YT.match(url))


def _call(method: str, url: str, *, data=None, headers=None, timeout: float = 120.0):
    key = config.GEMINI_KEY
    req = Request(url, data=data, method=method, headers={"x-goog-api-key": key, **(headers or {})})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            d = json.loads(body)
            msg = (d[0] if isinstance(d, list) else d)["error"]["message"]
        except Exception:
            msg = body[:300]
        hint = {401: "chave inválida", 403: "chave sem permissão", 429: "cota do Gemini esgotada; espere ou use outra chave"}
        raise GeminiError(f"HTTP {e.code}: {msg.replace(key, '***')} {('→ ' + hint[e.code]) if e.code in hint else ''}") from None
    except (URLError, TimeoutError, OSError) as e:
        raise GeminiError(f"sem conexão com o Gemini: {getattr(e, 'reason', e)}") from None


def upload(path: Path, max_wait: float = 900) -> dict:
    """Envia um vídeo local para a Files API e espera ficar ACTIVE."""
    size = path.stat().st_size
    mime = mimetypes.guess_type(path.name)[0] or "video/mp4"
    _, headers, _ = _call("POST", f"{API}/upload/v1beta/files",
                          data=json.dumps({"file": {"display_name": "darkclip"}}).encode(),
                          headers={"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                                   "X-Goog-Upload-Header-Content-Length": str(size),
                                   "X-Goog-Upload-Header-Content-Type": mime, "Content-Type": "application/json"})
    session = {k.lower(): v for k, v in headers.items()}.get("x-goog-upload-url")
    if not session:
        raise GeminiError("a Files API não devolveu a URL de upload")
    with path.open("rb") as f:
        _, _, body = _call("POST", session, data=f, timeout=3600,
                           headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                                    "X-Goog-Upload-Command": "upload, finalize"})
    info = json.loads(body)["file"]
    waited = 0.0
    while info.get("state") == "PROCESSING" and waited < max_wait:
        time.sleep(3)
        waited += 3
        info = json.loads(_call("GET", f"{API}/v1beta/{info['name']}")[2])
    if info.get("state") != "ACTIVE":
        delete(info["name"])
        raise GeminiError(f"o vídeo não ficou pronto no Gemini (estado {info.get('state')})")
    return {"name": info["name"], "uri": info["uri"], "mime_type": info.get("mimeType") or mime}


def delete(name: str) -> None:
    try:
        _call("DELETE", f"{API}/v1beta/{name}")
    except GeminiError:
        pass  # o Google apaga sozinho em 48 h


def _text(data: dict) -> str:
    if data.get("output_text"):
        return data["output_text"]
    parts = [p.get("text", "") for st in data.get("steps", []) if st.get("type") == "model_output"
             for p in st.get("content", []) if p.get("type") == "text"]
    return "\n".join(x for x in parts if x).strip()


def _json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)  # modo sem schema: extrai o primeiro objeto JSON
        if not m:
            raise GeminiError("o Gemini não devolveu JSON") from None
        return json.loads(m.group(0))


BUSY = ("HTTP 503", "HTTP 500", "HTTP 502", "HTTP 504", "HTTP 429", "high demand", "overloaded", "UNAVAILABLE",
        "sem conexão com o Gemini", "10054", "timed out", "Connection reset")   # quedas de conexão também são passageiras


def _models() -> list[str]:
    """Modelo principal + reservas (usados quando o principal está sobrecarregado)."""
    extra = [m.strip() for m in os.environ.get("DARKCLIP_GEMINI_FALLBACKS",
                                               "gemini-3.8-flash,gemini-3.5-flash-lite").split(",") if m.strip()]
    return [config.GEMINI_MODEL] + [m for m in extra if m != config.GEMINI_MODEL]


def _send(model: str, video: dict, prompt: str, processing, schema, timeout: float) -> bytes:
    parts = [{"type": "video", **video, "processing": processing}] if video else []
    payload = {"model": model, "input": parts + [{"type": "text", "text": prompt}]}
    if schema:
        payload["response_format"] = {"type": "text", "mime_type": "application/json", "schema": schema}
    return _call("POST", INTERACTIONS, data=json.dumps(payload).encode(),
                 headers={"Content-Type": "application/json"}, timeout=timeout)[2]


def ask(video: dict | None, prompt: str, *, agentic: bool, schema: dict | None = SCHEMA, timeout: float = 900,
        on_retry=None, waits: tuple = (15, 45), raw: bool = False) -> dict | str:
    """Pergunta sobre o vídeo. Se o Google estiver sobrecarregado (503/429), espera e tenta de novo;
    se continuar, passa para um modelo reserva (DARKCLIP_GEMINI_FALLBACKS)."""
    processing = "agentic" if agentic else {"type": "static"}
    say = on_retry or (lambda msg: None)
    body, last_err = None, None
    models = _models()
    for i, model in enumerate(models):
        pauses = list(waits)
        while body is None:
            try:
                body = _send(model, video, prompt, processing, schema, timeout)
            except GeminiError as e:
                last_err, msg = e, str(e)
                if schema and "HTTP 400" in msg:
                    schema = None  # alguns modos não aceitam schema: pede JSON no texto
                    prompt += "\n\nResponda SOMENTE com o JSON pedido."
                elif any(b in msg for b in BUSY) and pauses:
                    w = pauses.pop(0)
                    say(f"Gemini ocupado ({model}); tentando de novo em {w} s…")
                    time.sleep(w)
                elif any(b in msg for b in BUSY) or "HTTP 404" in msg or "not found" in msg.lower():
                    if i + 1 < len(models):
                        say(f"Gemini {model} indisponível agora; trocando para {models[i + 1]}…")
                    break  # próximo modelo
                else:
                    raise
        if body is not None:
            config.GEMINI_MODEL_USED = model
            break
    if body is None:
        raise last_err or GeminiError("Gemini indisponível")
    data = json.loads(body)
    try:  # 💰 consumo real (link do YouTube: grátis durante a prévia do Google)
        from . import costs
        u = data.get("usage") or {}
        tin = u.get("total_input_tokens") or u.get("input_tokens") or u.get("prompt_token_count") or 0
        tout = (u.get("total_output_tokens") or u.get("output_tokens") or 0) + (u.get("total_thought_tokens") or 0)
        if not (tin or tout) and u.get("total_tokens"):
            tin = u["total_tokens"]
        yt = bool(video) and is_youtube(video.get("uri"))
        costs.add("gemini", getattr(config, "GEMINI_MODEL_USED", config.GEMINI_MODEL), tin, tout, free=yt and config.GEMINI_YT_FREE,
                  note="link do YouTube (prévia grátis)" if yt else "")
    except Exception:
        pass
    return _text(data) if raw else _json(_text(data))


def _sec(t) -> float:
    if isinstance(t, (int, float)):
        return float(t)
    parts = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(t))]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def find_moments(*, url: str | None = None, path: Path | None = None, duration: float = 0, niche: str = "",
                 request: str = "", n: int = 12, hints: list[str] | None = None, on_retry=None) -> dict:
    """Retorna {"summary", "moments": [{start, end (s), score, what, why, hook, title, visual}]}."""
    if not config.HAS_GEMINI:
        raise GeminiError("defina GEMINI_API_KEY no .env")
    uploaded = None
    if is_youtube(url):
        video = {"uri": url}
    elif path and Path(path).exists():
        uploaded = upload(Path(path))
        video = {"uri": uploaded["uri"], "mime_type": uploaded["mime_type"]}
    else:
        raise GeminiError("o Gemini precisa de um link do YouTube ou do arquivo de vídeo")
    prompt = (
        f"Você é editor de Shorts virais{(' para um canal de ' + niche) if niche else ''}. "
        f"Assista ao vídeo inteiro, imagem E áudio, e aponte os {n} melhores momentos para virar Shorts de 20 a 60 s.\n"
        + (f"PEDIDO DO USUÁRIO (prioridade): {request}\n" if request else "")
        + ("PISTAS DO PÚBLICO — verifique cada uma: diga se ali existe um clipe que se sustenta sozinho, "
           "com início e fim exatos, e proponha também momentos fora desta lista:\n"
           + "\n".join(f"- {h}" for h in hints) + "\n" if hints else "")
        + "Procure: reações fortes, risadas, sustos, revelações, ação intensa, frases de impacto, conflitos, "
        "momentos engraçados ou emocionantes, coisas visualmente marcantes (que a transcrição sozinha não mostraria).\n"
        "Cada momento precisa ter começo forte e terminar no desfecho (não corte antes da punchline).\n"
        "Use timestamps reais no formato MM:SS (ou H:MM:SS). Score honesto de 0 a 100. Escreva em português do Brasil."
    )
    try:
        data = ask(video, prompt, agentic=duration == 0 or duration > 600, on_retry=on_retry)
    finally:
        if uploaded:
            delete(uploaded["name"])
    moments = []
    for m in data.get("moments", []):
        s, e = _sec(m.get("start")), _sec(m.get("end"))
        if e <= s or (duration and s >= duration):
            continue
        moments.append({**m, "start": s, "end": min(e, duration) if duration else e,
                        "score": max(0, min(100, int(m.get("score") or 0)))})
    return {"summary": data.get("summary", ""), "moments": moments,
            "model": getattr(config, "GEMINI_MODEL_USED", config.GEMINI_MODEL)}


def ask_text(prompt: str, schema: dict | None, on_retry=None) -> dict:
    """Só texto (sem vídeo): usado para escolher os cortes pela transcrição quando não há Claude.
    Bem mais leve que assistir o vídeo, então costuma passar mesmo quando o Gemini está lotado."""
    return ask(None, prompt, agentic=False, schema=schema, timeout=300, on_retry=on_retry)


def ping() -> str:
    """Pergunta curtíssima só de texto: confirma que a chave e o modelo funcionam."""
    body = _call("POST", INTERACTIONS, timeout=60, headers={"Content-Type": "application/json"},
                 data=json.dumps({"model": config.GEMINI_MODEL,
                                  "input": [{"type": "text", "text": "Responda apenas: ok"}]}).encode())[2]
    return _text(json.loads(body))[:40] or "(resposta vazia)"
