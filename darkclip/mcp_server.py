"""🤖 Servidor MCP do DarkClip: o Claude (Code ou Desktop) usa o DarkClip direto, sem você apertar botões.

Ele conversa com o DarkClip que já está aberto no PC (start_windows.bat), então a fila de trabalhos é a mesma
do app. Só usa a biblioteca padrão do Python.

Registrar no Claude Code (na pasta do DarkClip, com o .venv ativo):
    claude mcp add darkclip -- python -m darkclip.mcp_server

Depois é só pedir: "corta este vídeo em 3 Shorts longos e me mostra os melhores".
"""
from __future__ import annotations

import json
import mimetypes
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from . import config

BASE = (__import__("os").environ.get("DARKCLIP_URL") or "http://127.0.0.1:8787").rstrip("/")
_open = build_opener(ProxyHandler({})).open     # localhost: nunca passa por proxy
PROTOCOL = "2025-06-18"

DURACOES = {"auto": (20, 60), "curtos": (15, 30), "longos": (45, 90), "facebook": (60, 180), "podcast": (540, 960)}
ENQUADRAMENTOS = ["auto", "track", "split", "gamer", "blur", "center"]


class DarkClipError(Exception):
    pass


# ------------------------------------------------------------------ acesso à API do DarkClip
def _api(method: str, path: str, body: dict | None = None, data: bytes | None = None,
         ctype: str = "application/json", timeout: float = 60) -> dict | list:
    headers = {"X-Token": config.TOKEN} if config.TOKEN else {}
    if body is not None:
        data = json.dumps(body).encode()
    if data is not None:
        headers["Content-Type"] = ctype
    try:
        with _open(Request(BASE + path, data=data, method=method, headers=headers), timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        try:
            detail = json.loads(detail).get("detail", detail)
        except Exception:
            pass
        raise DarkClipError(f"O DarkClip respondeu erro {e.code}: {detail}") from None
    except URLError:
        raise DarkClipError(f"Não encontrei o DarkClip em {BASE}. Abra o start_windows.bat (ou ./start.sh) e tente de novo.") from None


def _upload(path: str) -> str:
    p = Path(path).expanduser()
    if not p.is_file():
        raise DarkClipError(f"Arquivo não encontrado: {p}")
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    data = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{p.name}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n").encode() + p.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return _api("POST", "/api/upload", data=data, ctype=f"multipart/form-data; boundary={boundary}", timeout=600)["name"]


def _clip_n(job: dict, n: int) -> int:
    clips = job.get("clips") or []
    if not 1 <= n <= len(clips):
        raise DarkClipError(f"O job tem {len(clips)} corte(s); use um número de 1 a {len(clips)}.")
    return n - 1


def _job_view(j: dict, full: bool = True) -> dict:
    clips = []
    for i, c in enumerate(j.get("clips") or [], 1):
        item = {"corte": i, "titulo": c.get("title"), "nota": c.get("score"), "duracao_s": c.get("duration"),
                "gancho": c.get("hook"), "status": c.get("status") or ("pronto" if c.get("file") else "sem arquivo")}
        if c.get("start") is not None:
            item["trecho_original"] = f"{c['start']:.1f}s–{c['end']:.1f}s"
        if c.get("file"):
            item["arquivo_local"] = str(config.JOBS_DIR / j["id"] / c["file"])
        if c.get("retention"):
            r = c["retention"]
            item["gancho"] = {"tipo": r.get("hook_type"), "texto": r.get("hook") or r.get("teaser_text"),
                              "previa": r.get("teaser"), "loop": r.get("loop")}
        if c.get("styled"):
            item["versoes"] = {k: (str(config.JOBS_DIR / j["id"] / v["file"]) if v.get("status") == "done" else v.get("status"))
                               for k, v in c["styled"].items()}
        if c.get("rating"):
            item["sua_nota"] = ("👍 " if c["rating"] > 0 else "👎 ") + (c.get("rating_reason") or "")
        if full and c.get("reason"):
            item["por_que"] = c["reason"]
        if c.get("error"):
            item["erro"] = c["error"]
        clips.append(item)
    out = {"job_id": j["id"], "status": j.get("status"), "progresso": j.get("progress"),
           "fonte": (j.get("source") or {}).get("title") or (j.get("params") or {}).get("url"),
           "motor": j.get("engine"), "cortes": clips}
    if full:
        out["ultimos_passos"] = (j.get("log") or [])[-6:]
    if j.get("error"):
        out["erro"] = j["error"]
    return out


# ------------------------------------------------------------------ ferramentas
def t_status(_a: dict) -> dict:
    info = _api("GET", "/api/info")
    return {"darkclip": "aberto ✅", "endereco": BASE, "claude": info.get("claude"), "gemini": info.get("gemini"),
            "modelo_gemini": info.get("gemini_model"), "trabalhos_na_fila": info.get("queue")}


def t_cortar(a: dict) -> dict:
    if not (a.get("url") or a.get("arquivo")):
        raise DarkClipError("Informe 'url' (link do vídeo) ou 'arquivo' (caminho de um vídeo no PC).")
    mn, mx = DURACOES.get(a.get("duracao", "auto"), DURACOES["auto"])
    body = {"mode": "clip", "n_clips": int(a.get("quantidade", 3)), "min_s": mn, "max_s": mx,
            "crop": a.get("enquadramento", "auto"), "request": a.get("pedido", ""), "niche": a.get("nicho", ""),
            "aspect": a.get("proporcao", "9:16"), "visual": bool(a.get("gemini", True)),
            "hook_mode": a.get("gancho", "auto"), "ending": a.get("final", "auto")}
    if a.get("url"):
        body["url"] = a["url"]
    else:
        body["upload"] = _upload(a["arquivo"])
    j = _api("POST", "/api/jobs", body)
    return {"job_id": j["id"], "status": j["status"],
            "proximo_passo": "Use esperar_job com este job_id para acompanhar até ficar pronto."}


def t_esperar(a: dict) -> dict:
    limit = min(float(a.get("max_segundos", 240)), 600)
    t0 = time.time()
    while True:
        j = _api("GET", f"/api/jobs/{a['job_id']}")
        busy = any(c.get("status") in ("queued", "rendering")
                   or any(v.get("status") in ("queued", "rendering") for v in (c.get("styled") or {}).values())
                   for c in j.get("clips") or [])
        if j.get("status") in ("done", "error") and not busy:
            return _job_view(j)
        if time.time() - t0 > limit:
            v = _job_view(j, full=True)
            v["aviso"] = "Ainda processando. Chame esperar_job de novo para continuar acompanhando."
            return v
        time.sleep(5)


def t_ver(a: dict) -> dict:
    return _job_view(_api("GET", f"/api/jobs/{a['job_id']}"))


def t_listar(a: dict) -> list:
    jobs = _api("GET", "/api/jobs")[: int(a.get("limite", 5))]
    return [_job_view(j, full=False) for j in jobs]


def t_avaliar(a: dict) -> dict:
    j = _api("GET", f"/api/jobs/{a['job_id']}")
    idx = _clip_n(j, int(a["corte"]))
    rating = {"gostei": 1, "nao_gostei": -1, "apagar": 0}.get(a.get("nota", ""), None)
    if rating is None:
        raise DarkClipError("nota deve ser 'gostei', 'nao_gostei' ou 'apagar'.")
    c = _api("POST", f"/api/jobs/{a['job_id']}/clips/{idx}/rate", {"rating": rating, "reason": a.get("motivo", "")})
    return {"corte": idx + 1, "nota": c.get("rating"), "motivo": c.get("rating_reason"),
            "efeito": "A IA vai usar essa nota como exemplo do seu gosto nos próximos cortes."}


def t_editar(a: dict) -> dict:
    j = _api("GET", f"/api/jobs/{a['job_id']}")
    idx = _clip_n(j, int(a["corte"]))
    body = {k2: a[k1] for k1, k2 in (("inicio", "start"), ("fim", "end"), ("gancho", "hook"), ("titulo", "title"),
                                    ("enquadramento", "crop"), ("legenda", "captions"), ("tipo_gancho", "hook_mode"),
                                    ("final", "ending")) if a.get(k1) is not None}
    if not body:
        raise DarkClipError("Diga o que mudar: inicio, fim, gancho, titulo, enquadramento ou legenda.")
    _api("POST", f"/api/jobs/{a['job_id']}/clips/{idx}/edit", body)
    return {"corte": idx + 1, "mudancas": body, "status": "refazendo",
            "proximo_passo": "Use esperar_job para saber quando o corte novo ficou pronto."}


def t_agendar(a: dict) -> dict:
    j = _api("GET", f"/api/jobs/{a['job_id']}")
    idx = _clip_n(j, int(a["corte"]))
    body = {"job": a["job_id"], "clip": idx, "platform": a.get("plataforma", "youtube"),
            "when": a.get("quando"), "account": a.get("conta"), "auto": bool(a.get("postar_sozinho", False))}
    return _api("POST", "/api/central/plan", body)


def t_versoes(a: dict) -> dict:
    body = {"templates": a.get("modelos") or None}
    if a.get("corte"):
        j = _api("GET", f"/api/jobs/{a['job_id']}")
        idx = _clip_n(j, int(a["corte"]))
        r = _api("POST", f"/api/jobs/{a['job_id']}/clips/{idx}/styled", body)
    else:
        r = _api("POST", f"/api/jobs/{a['job_id']}/styled", body)
    return {"gerando": r.get("queued"), "proximo_passo": "Use esperar_job: cada versão aparece em 'versoes' do corte."}


def t_canal(_a: dict) -> dict:
    s = _api("GET", "/api/central")
    up = [{"quando": p.get("planned_at"), "plataforma": p.get("platform"), "titulo": p.get("title"),
           "status": p.get("status")} for p in (s.get("upcoming") or [])[:10]]
    return {"perfil_do_canal": (s.get("settings") or {}).get("brief", ""), "horarios": (s.get("settings") or {}).get("slots"),
            "proximos_posts": up, "o_que_funciona": s.get("insights"), "notas": _api("GET", "/api/feedback")}


def t_perfil(a: dict) -> dict:
    _api("POST", "/api/central/channel", {"url": "", "brief": a.get("texto", "")})
    return {"perfil_do_canal": a.get("texto", ""), "efeito": "Vale para todos os próximos cortes."}


TOOLS = {
    "status": (t_status, "Confere se o DarkClip está aberto e quais IAs estão configuradas.", {}),
    "cortar_video": (t_cortar, "Cria cortes (Shorts/Reels) de um vídeo. Use 'url' para links (YouTube, Facebook, TikTok, Kick) ou 'arquivo' para um vídeo do PC.", {
        "url": {"type": "string", "description": "Link do vídeo ou da live"},
        "arquivo": {"type": "string", "description": "Caminho de um vídeo no PC (alternativa ao link)"},
        "quantidade": {"type": "integer", "minimum": 1, "maximum": 30, "default": 3},
        "duracao": {"type": "string", "enum": list(DURACOES), "default": "auto",
                    "description": "auto 20–60s · curtos 15–30s · longos 45–90s · facebook 1–3min · podcast 9–16min"},
        "enquadramento": {"type": "string", "enum": ENQUADRAMENTOS, "default": "auto"},
        "proporcao": {"type": "string", "enum": ["9:16", "4:5", "1:1", "original"], "default": "9:16"},
        "pedido": {"type": "string", "description": "O que procurar no vídeo, ex.: 'a parte do susto'"},
        "nicho": {"type": "string"},
        "gemini": {"type": "boolean", "default": True, "description": "Deixar o Gemini assistir o vídeo"},
        "gancho": {"type": "string", "enum": ["auto", "previa", "pergunta", "espera", "choque", "pov", "acao", "nenhum"], "default": "auto",
                   "description": "previa = abre com o melhor momento e volta ao começo; auto = a IA escolhe por corte"},
        "final": {"type": "string", "enum": ["auto", "loop", "normal"], "default": "auto",
                  "description": "loop = o fim se dissolve no 1º quadro (replay sem emenda)"},}),
    "esperar_job": (t_esperar, "Acompanha um trabalho até ficar pronto (ou até max_segundos) e devolve os cortes.", {
        "job_id": {"type": "string"}, "max_segundos": {"type": "integer", "default": 240, "maximum": 600}}, ["job_id"]),
    "ver_job": (t_ver, "Mostra o estado de um trabalho, os passos e os cortes com nota e arquivo.", {
        "job_id": {"type": "string"}}, ["job_id"]),
    "listar_jobs": (t_listar, "Lista os trabalhos mais recentes.", {"limite": {"type": "integer", "default": 5}}),
    "avaliar_corte": (t_avaliar, "Dá 👍/👎 a um corte com motivo. A IA aprende o gosto do dono com isso.", {
        "job_id": {"type": "string"}, "corte": {"type": "integer", "description": "Número do corte (1, 2, 3…)"},
        "nota": {"type": "string", "enum": ["gostei", "nao_gostei", "apagar"]},
        "motivo": {"type": "string", "description": "ex.: 'Começa sem contexto', 'Boa reação'"}}, ["job_id", "corte", "nota"]),
    "editar_corte": (t_editar, "Refaz um corte mudando início/fim (segundos do vídeo original), gancho, título, enquadramento ou legenda.", {
        "job_id": {"type": "string"}, "corte": {"type": "integer"},
        "inicio": {"type": "number"}, "fim": {"type": "number"}, "gancho": {"type": "string"}, "titulo": {"type": "string"},
        "enquadramento": {"type": "string", "enum": ENQUADRAMENTOS}, "legenda": {"type": "boolean"},
        "tipo_gancho": {"type": "string", "enum": ["auto", "previa", "pergunta", "espera", "choque", "pov", "acao", "nenhum"]},
        "final": {"type": "string", "enum": ["auto", "loop", "normal"]}}, ["job_id", "corte"]),
    "agendar_corte": (t_agendar, "Coloca um corte no calendário da Central do Canal (e, se quiser, posta sozinho na hora).", {
        "job_id": {"type": "string"}, "corte": {"type": "integer"},
        "plataforma": {"type": "string", "enum": ["youtube", "instagram", "facebook", "tiktok", "kwai"], "default": "youtube"},
        "quando": {"type": "string", "description": "Data e hora ISO (ex.: 2026-11-26T18:00). Vazio = próximo horário livre"},
        "conta": {"type": "string", "description": "Conta conectada na aba Contas (para postar sozinho)"},
        "postar_sozinho": {"type": "boolean", "default": False}}, ["job_id", "corte"]),
    "gerar_versoes": (t_versoes, "Gera versões do corte com modelos visuais diferentes por rede (fundo, cartão, título, @). Ao postar, cada rede recebe a sua.", {
        "job_id": {"type": "string"}, "corte": {"type": "integer", "description": "Vazio = todos os cortes"},
        "modelos": {"type": "array", "items": {"type": "string", "enum": ["manchete", "cartao", "neon", "minimal", "meu_fundo"]},
                    "description": "Vazio = os modelos escolhidos para cada rede na aba Canal"}}, ["job_id"]),
    "ver_canal": (t_canal, "Mostra o perfil do canal, os horários, os próximos posts, o que funciona e o resumo das notas 👍/👎.", {}),
    "definir_perfil_do_canal": (t_perfil, "Salva o que é um bom corte para o canal (vale para todos os cortes).", {
        "texto": {"type": "string", "maxLength": 800}}, ["texto"]),
}


def _tool_list() -> list[dict]:
    out = []
    for name, spec in TOOLS.items():
        props = spec[2]
        schema = {"type": "object", "properties": props}
        if len(spec) > 3:
            schema["required"] = spec[3]
        out.append({"name": name, "description": spec[1], "inputSchema": schema})
    return out


# ------------------------------------------------------------------ protocolo (JSON-RPC por stdin/stdout)
def handle(msg: dict) -> dict | None:
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:                       # notificação (ex.: notifications/initialized): não responde
        return None
    if method == "initialize":
        result = {"protocolVersion": params.get("protocolVersion") or PROTOCOL,
                  "capabilities": {"tools": {"listChanged": False}},
                  "serverInfo": {"name": "darkclip", "version": "1.0"},
                  "instructions": "Fábrica de cortes do DarkClip. Fluxo comum: cortar_video → esperar_job → "
                                  "avaliar_corte/editar_corte → agendar_corte. Responda ao usuário em português simples."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": _tool_list()}
    elif method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Ferramenta desconhecida: {name}"}}
        try:
            data = TOOLS[name][0](args)
            result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=1)}]}
        except DarkClipError as e:
            result = {"content": [{"type": "text", "text": str(e)}], "isError": True}
        except Exception as e:  # nunca derruba o servidor MCP
            result = {"content": [{"type": "text", "text": config.redact(f"Erro inesperado: {e}")}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Método não suportado: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
