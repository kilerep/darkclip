"""Servidor do app DarkClip (API + PWA para celular).

  uvicorn server:app --host 0.0.0.0 --port 8787
Abra no celular: http://IP-DO-PC:8787  (ou http://127.0.0.1:8787 no Termux)
"""
from __future__ import annotations

import queue
import re
import threading
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from darkclip import central, config, publish, social
from darkclip.pipeline import Job, render_styled, rerender, run
from darkclip.tts import VOICES

app = FastAPI(title="DarkClip")


@app.on_event("startup")
async def _quiet_windows_resets() -> None:
    """No Windows, quando o navegador pula o vídeo (ou fecha a aba), aparece
    "ConnectionResetError [WinError 10054]" no cmd. É inofensivo: escondemos."""
    import asyncio
    loop = asyncio.get_running_loop()
    default = loop.get_exception_handler()

    def handler(lp, ctx):
        if isinstance(ctx.get("exception"), (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return
        if default:
            default(lp, ctx)
        else:
            lp.default_exception_handler(ctx)

    loop.set_exception_handler(handler)
WEB = Path(__file__).parent / "web"
_q: "queue.Queue[str]" = queue.Queue()


def _worker() -> None:
    while True:
        task = _q.get()
        try:
            if task.count(":") == 2:  # versão do corte com um modelo visual
                jid, idx, tpl = task.split(":")
                render_styled(Job(jid), int(idx), tpl)
            elif ":" in task:  # re-render de um clipe (editor)
                jid, idx = task.split(":")
                rerender(Job(jid), int(idx))
            else:
                run(Job(task))
        finally:
            _q.task_done()


threading.Thread(target=_worker, daemon=True).start()
# Retoma jobs que ficaram na fila se o servidor reiniciou
for f in sorted(config.JOBS_DIR.glob("*/job.json")):
    j = Job(f.parent.name)
    for i, c in enumerate(j.data.get("clips", [])):
        if c.get("status") in ("queued", "rendering"):
            _q.put(f"{j.id}:{i}")
        for tname, v in (c.get("styled") or {}).items():
            if v.get("status") in ("queued", "rendering"):
                _q.put(f"{j.id}:{i}:{tname}")
    if j.data.get("status") in ("queued", "running"):
        j.data["status"] = "queued"
        j.save()
        _q.put(j.id)


def auth(x_token: str | None = Header(None), token: str | None = Query(None)) -> None:
    if config.TOKEN and config.TOKEN not in (x_token, token):
        raise HTTPException(401, "Token inválido")


class JobIn(BaseModel):
    mode: str = "clip"
    url: str | None = None
    upload: str | None = None
    upload_subs: str | None = None
    n_clips: int = 4
    min_s: int = 20
    max_s: int = 58
    crop: str = "auto"
    style: str = "amarelo"
    jumpcut: bool = True
    zoom: bool = True
    progress: bool = True
    smart: bool = True
    comments: bool = True
    visual: bool = True
    request: str = ""
    max_comments: int = 600
    aspect: str = "9:16"
    distance: str = "padrao"
    captions: bool = True
    range_start: float = 0
    range_end: float = 0
    part_min: float = 0
    vision: str | None = None
    sfx: bool = True
    lang: str = "pt"
    niche: str = ""
    stickers: bool = False      # figurinhas de reação (desligado: o dono preferiu sem)
    react_zoom: bool = True     # 🔍 zoom no rosto / close da webcam na reação
    hook_mode: str = "auto"     # 🎣 auto | previa | pergunta | espera | choque | pov | acao | nenhum
    ending: str = "auto"        # auto | loop | normal
    grade: bool = True
    hook: bool = True
    music: str | None = None
    topic: str = ""
    formato: str = "livre"
    script: str | None = None
    voice: str = config.VOICE
    bg_url: str | None = None
    bg_upload: str | None = None


class EditIn(BaseModel):
    start: float | None = None
    end: float | None = None
    hook: str | None = None
    title: str | None = None
    description: str | None = None
    emphasis: list[str] | None = None
    crop: str | None = None
    style: str | None = None
    aspect: str | None = None
    distance: str | None = None
    captions: bool | None = None
    sfx: bool | None = None
    jumpcut: bool | None = None
    zoom: bool | None = None
    progress: bool | None = None
    stickers: bool | None = None
    react_zoom: bool | None = None
    hook_mode: str | None = None
    ending: str | None = None


class PublishIn(BaseModel):
    title: str
    description: str = ""
    hashtags: list[str] = []
    when: str | None = None
    privacy: str = "public"


@app.get("/api/info", dependencies=[Depends(auth)])
def info():
    return {"claude": config.HAS_CLAUDE, "model": config.CLAUDE_MODEL, "postiz": publish.available(),
            "gemini": config.HAS_GEMINI, "gemini_model": config.GEMINI_MODEL, "ollama": config.OLLAMA_MODEL,
            "voices": VOICES, "queue": _q.qsize()}


@app.post("/api/upload", dependencies=[Depends(auth)])
async def upload(file: UploadFile = File(...)):
    safe = re.sub(r"[^\w.\-]", "_", file.filename or "arquivo")
    name = f"{uuid.uuid4().hex[:6]}_{safe}"
    dst = config.UPLOADS_DIR / name
    with dst.open("wb") as f:
        while chunk := await file.read(1 << 20):
            f.write(chunk)
    return {"name": name}


@app.post("/api/jobs", dependencies=[Depends(auth)])
def create_job(body: JobIn):
    p = body.model_dump()
    if p["mode"] in ("clip", "legendar", "silencios", "analisar") and not (p["url"] or p["upload"]):
        raise HTTPException(400, "Informe um link ou envie um vídeo.")
    if p["mode"] == "story" and not (p["topic"] or p["script"]):
        raise HTTPException(400, "Informe um tema ou um roteiro.")
    job = Job.create(p)
    _q.put(job.id)
    return job.data


@app.get("/api/jobs", dependencies=[Depends(auth)])
def list_jobs():
    jobs = [Job(f.parent.name).data for f in config.JOBS_DIR.glob("*/job.json")]
    return sorted(jobs, key=lambda j: j.get("created", 0), reverse=True)[:50]


@app.get("/api/jobs/{jid}", dependencies=[Depends(auth)])
def get_job(jid: str):
    j = Job(_safe(jid))
    if not j.data:
        raise HTTPException(404)
    return j.data


@app.delete("/api/jobs/{jid}", dependencies=[Depends(auth)])
def delete_job(jid: str):
    import shutil
    shutil.rmtree(config.JOBS_DIR / _safe(jid), ignore_errors=True)
    return {"ok": True}


@app.get("/files/{jid}/{name}", dependencies=[Depends(auth)])
def get_file(jid: str, name: str, dl: int = 0):
    path = config.JOBS_DIR / _safe(jid) / _safe(name)
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, filename=name if dl else None)


@app.post("/api/jobs/{jid}/clips/{idx}/publish", dependencies=[Depends(auth)])
def publish_clip(jid: str, idx: int, body: PublishIn):
    j = Job(_safe(jid))
    clip = j.data["clips"][idx]
    try:
        res = publish.publish_youtube(j.dir / clip["file"], body.title, body.description, body.hashtags,
                                      body.when, body.privacy)
    except Exception as e:
        raise HTTPException(400, str(e))
    clip["published"] = res
    j.save()
    return res


@app.post("/api/jobs/{jid}/clips/{idx}/edit", dependencies=[Depends(auth)])
def edit_clip(jid: str, idx: int, body: EditIn):
    j = Job(_safe(jid))
    if not j.data or idx >= len(j.data["clips"]):
        raise HTTPException(404)
    clip = j.data["clips"][idx]
    clip["edit"] = {**clip.get("edit", {}), **body.model_dump(exclude_none=True)}
    clip["status"] = "queued"
    j.save()
    _q.put(f"{j.id}:{idx}")
    return clip


class RateIn(BaseModel):
    rating: int = 0          # 1 = gostei, -1 = não gostei, 0 = apagar
    reason: str = ""


@app.post("/api/jobs/{jid}/clips/{idx}/rate", dependencies=[Depends(auth)])
def rate_clip(jid: str, idx: int, body: RateIn):
    from darkclip import feedback
    j = Job(_safe(jid))
    if not j.data or idx >= len(j.data["clips"]):
        raise HTTPException(404)
    return feedback.rate(j, idx, body.rating, body.reason)


@app.get("/api/feedback", dependencies=[Depends(auth)])
def feedback_summary():
    from darkclip import feedback
    return feedback.summary()


# ------------------------------------------------------------------ 🎨 Modelos visuais e versões por rede
class BrandIn(BaseModel):
    templates: dict[str, str] | None = None   # rede -> modelo
    handle: str | None = None                 # @ do canal
    bg_image: str | None = None               # nome do arquivo enviado em /api/upload ("" remove)


class StyledIn(BaseModel):
    templates: list[str] | None = None        # vazio = os modelos escolhidos para as redes


@app.get("/api/hooks", dependencies=[Depends(auth)])
def hooks_info():
    from darkclip import hooks
    return hooks.catalog()


@app.get("/api/templates", dependencies=[Depends(auth)])
def templates_info():
    from darkclip import templates
    st = central.load()["settings"]
    return {"catalog": templates.catalog(), "platforms": templates.PLATFORMS,
            "by_platform": {p: central.template_for(p, {"settings": st}) for p in templates.PLATFORMS},
            "handle": st.get("handle", ""), "bg_image": st.get("bg_image", "")}


@app.get("/api/templates/{name}/preview.jpg", dependencies=[Depends(auth)])
def template_preview(name: str):
    from darkclip import templates
    if name not in templates.TEMPLATES:
        raise HTTPException(404)
    try:
        return FileResponse(templates.preview(name, central.load()["settings"], config.DATA_DIR), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(500, str(e)[:300])


@app.post("/api/central/brand", dependencies=[Depends(auth)])
def central_brand(body: BrandIn):
    central.set_brand(body.templates, body.handle, body.bg_image)
    return templates_info()


def _queue_styled(j: Job, idx: int, names: list[str] | None) -> list[str]:
    from darkclip import templates
    clip = j.data["clips"][idx]
    if not clip.get("file"):
        return []
    if not names:
        names = [central.template_for(p) for p in templates.PLATFORMS]
    names = [n for n in dict.fromkeys(names) if templates.get(n)]   # sem repetir; "tela cheia" usa o corte normal
    styled = clip.setdefault("styled", {})
    for n in names:
        styled[n] = {**styled.get(n, {}), "template": n, "status": "queued"}
    return names


@app.post("/api/jobs/{jid}/clips/{idx}/styled", dependencies=[Depends(auth)])
def styled_clip(jid: str, idx: int, body: StyledIn):
    j = Job(_safe(jid))
    if not j.data or idx >= len(j.data["clips"]):
        raise HTTPException(404)
    names = _queue_styled(j, idx, body.templates)
    j.save()  # salva antes de pôr na fila
    for n in names:
        _q.put(f"{j.id}:{idx}:{n}")
    return {"queued": names}


@app.post("/api/jobs/{jid}/styled", dependencies=[Depends(auth)])
def styled_all(jid: str, body: StyledIn):
    j = Job(_safe(jid))
    if not j.data:
        raise HTTPException(404)
    names = [_queue_styled(j, i, body.templates) for i in range(len(j.data["clips"]))]
    j.save()  # salva antes de pôr na fila
    for i, ns in enumerate(names):
        for n in ns:
            _q.put(f"{j.id}:{i}:{n}")
    return {"queued": names}


# ------------------------------------------------------------------ 📅 Central do Canal
class ChannelIn(BaseModel):
    url: str = ""
    slots: list[str] | None = None
    per_day: int | None = None
    brief: str | None = None


class PlanIn(BaseModel):
    job: str
    clip: int
    when: str | None = None
    platform: str = "youtube"
    account: str | None = None
    auto: bool = False


class PostIn(BaseModel):
    account: str | None = None
    auto: bool | None = None
    planned_at: str | None = None
    platform: str | None = None
    title: str | None = None
    url: str | None = None
    status: str | None = None


_sync = {"running": False, "error": None}


@app.get("/api/central", dependencies=[Depends(auth)])
def central_get():
    return {**central.summary(), "sync": _sync}


@app.post("/api/central/channel", dependencies=[Depends(auth)])
def central_channel(body: ChannelIn):
    central.set_channel(body.url, body.slots, body.per_day, body.brief)
    return central.summary()


@app.post("/api/central/sync", dependencies=[Depends(auth)])
def central_sync():
    if _sync["running"]:
        return {"ok": True, "running": True}

    def job():
        _sync.update(running=True, error=None)
        try:
            central.sync()
        except Exception as e:
            _sync["error"] = str(e)[:400]
        finally:
            _sync["running"] = False
    threading.Thread(target=job, daemon=True).start()
    return {"ok": True, "running": True}


@app.post("/api/central/plan", dependencies=[Depends(auth)])
def central_plan(body: PlanIn):
    return central.plan(_safe(body.job), body.clip, body.when, body.platform, body.account, body.auto)


@app.post("/api/central/posts/{pid}", dependencies=[Depends(auth)])
def central_post(pid: str, body: PostIn):
    return central.update_post(_safe(pid), **body.model_dump())


@app.delete("/api/central/posts/{pid}", dependencies=[Depends(auth)])
def central_del(pid: str):
    central.delete_post(_safe(pid))
    return {"ok": True}


class PlanAllIn(BaseModel):
    job: str
    account: str | None = None
    auto: bool = False
    platform: str = "youtube"
    every_hours: float | None = None
    min_score: int = 0


@app.post("/api/central/plan_all", dependencies=[Depends(auth)])
def central_plan_all(body: PlanAllIn):
    return central.plan_all(_safe(body.job), body.account, body.auto, body.platform, body.every_hours, body.min_score)


@app.post("/api/central/posts/{pid}/publish", dependencies=[Depends(auth)])
def central_publish(pid: str):
    threading.Thread(target=central.publish_post, args=(_safe(pid),), daemon=True).start()
    return {"ok": True}


# ------------------------------------------------------------------ 🔗 Contas
class MetaIn(BaseModel):
    app_id: str
    app_secret: str
    user_token: str


class YTIn(BaseModel):
    client_id: str
    client_secret: str


@app.get("/api/contas", dependencies=[Depends(auth)])
def contas():
    return social.public_view()


@app.post("/api/contas/meta", dependencies=[Depends(auth)])
def contas_meta(body: MetaIn):
    try:
        return social.meta_connect(body.app_id.strip(), body.app_secret.strip(), body.user_token.strip())
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/contas/youtube", dependencies=[Depends(auth)])
def contas_youtube(body: YTIn):
    # cliente OAuth "App para computador": o Google aceita qualquer porta em 127.0.0.1
    return {"auth_url": social.youtube_auth_url(body.client_id, body.client_secret,
                                                "http://127.0.0.1:8787/api/contas/youtube/callback")}


@app.get("/api/contas/youtube/callback")
def contas_youtube_cb(code: str = "", state: str = "", error: str = ""):
    from fastapi.responses import HTMLResponse
    try:
        if error:
            raise RuntimeError(error)
        social.youtube_callback(code, state)
        msg = "✅ YouTube conectado! Pode fechar esta aba e voltar ao DarkClip."
    except Exception as e:
        msg = f"❌ Não deu certo: {e}"
    return HTMLResponse(f"<meta name=viewport content='width=device-width'><body style='background:#0b0b10;color:#eee;"
                        f"font:18px system-ui;padding:40px'>{msg}</body>")


@app.delete("/api/contas/{account}", dependencies=[Depends(auth)])
def contas_remove(account: str):
    return social.remove(account)


def _scheduler() -> None:
    """Publica os posts automáticos na hora marcada (o PC precisa estar ligado com o DarkClip aberto)."""
    while True:
        try:
            central.run_due()
        except Exception as e:
            print(f"[agendador] {e}")
        time.sleep(60)


threading.Thread(target=_scheduler, daemon=True).start()


# ------------------------------------------------------------------ 💡 Em alta / ideias
class IdeasIn(BaseModel):
    niche: str = ""
    subthemes: list[str] = []
    n: int = 10


@app.get("/api/trends", dependencies=[Depends(auth)])
def trends_get(geo: str = "BR"):
    from darkclip import trends
    try:
        return {"trends": trends.fetch(geo)}
    except Exception as e:
        raise HTTPException(502, f"Google Trends indisponível: {e}")


@app.post("/api/ideas", dependencies=[Depends(auth)])
def ideas_post(body: IdeasIn):
    from darkclip import trends
    try:
        return trends.ideas(body.niche, body.subthemes, max(3, min(20, body.n)))
    except Exception as e:
        raise HTTPException(400, str(e))


def _safe(s: str) -> str:
    if not re.fullmatch(r"[\w.\-]+", s):
        raise HTTPException(400, "nome inválido")
    return s


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
