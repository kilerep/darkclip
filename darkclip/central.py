"""📅 Central do Canal — o "Metricool" grátis do DarkClip.

- Calendário: fila de Shorts planejados (data/hora/rede), "postar agora", marcar como postado.
- Números do canal (YouTube) via yt-dlp, sem API paga: inscritos, views por Short, crescimento.
- Progresso da monetização (estimativa): 1.000 inscritos + 10 milhões de views de Shorts em 90 dias.
- Aprendizado: compara os Shorts postados (duração, estilo, layout, horário, nota) com as views reais
  e devolve dicas — que também entram no prompt da IA na hora de escolher novos clipes.

Dados em data/central.json.
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from . import config

FILE = config.DATA_DIR / "central.json"
_lock = threading.Lock()
YPP_SUBS, YPP_VIEWS = 1000, 10_000_000
DEFAULT_SLOTS = ["12:00", "18:00", "21:00"]


# ------------------------------------------------------------------ estado
def load() -> dict:
    if FILE.exists():
        try:
            return json.loads(FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"channel": None, "posts": [], "snapshots": [], "settings": {"slots": DEFAULT_SLOTS, "per_day": 2}}


def save(st: dict) -> None:
    tmp = FILE.with_suffix(".tmp")
    from . import config
    tmp.write_text(config.redact(json.dumps(st, ensure_ascii=False, indent=1)), encoding="utf-8")
    tmp.replace(FILE)


def _now() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


# ------------------------------------------------------------------ calendário
def next_slot(st: dict, after: datetime | None = None) -> str:
    """Próximo horário livre segundo a configuração (ex.: 12:00, 18:00, 21:00; até N por dia)."""
    slots = st["settings"].get("slots") or DEFAULT_SLOTS
    per_day = int(st["settings"].get("per_day") or len(slots))
    taken = {p["planned_at"] for p in st["posts"] if p.get("planned_at")}
    day = (after or _now()).date()
    for _ in range(60):
        used = sum(1 for t in taken if t.startswith(day.isoformat()))
        for hhmm in slots[:per_day]:
            cand = datetime.fromisoformat(f"{day.isoformat()}T{hhmm}")
            iso = cand.isoformat(timespec="minutes")
            if cand > (after or _now()) and iso not in taken and used < per_day:
                return iso
        day += timedelta(days=1)
    return ((after or _now()) + timedelta(hours=1)).isoformat(timespec="minutes")


def plan(job_id: str, clip_idx: int, when: str | None = None, platform: str = "youtube",
         account: str | None = None, auto: bool = False) -> dict:
    from .pipeline import Job
    job = Job(job_id)
    clip = job.data["clips"][clip_idx]
    with _lock:
        st = load()
        post = {
            "id": uuid.uuid4().hex[:8], "job": job_id, "clip": clip_idx,
            "platform": (account.split(":")[0] if account else platform),
            "title": clip.get("title", ""), "planned_at": when or next_slot(st), "status": "planejado",
            "url": None, "posted_at": None, "account": account, "auto": bool(account and auto), "error": None,
            "meta": {"duration": clip.get("duration"), "score": clip.get("score"),
                     "style": (clip.get("edit") or {}).get("style") or job.data["params"].get("style", "amarelo"),
                     "layout": (clip.get("render") or {}).get("layout"), "niche": job.data["params"].get("niche", ""),
                     "hook": clip.get("hook", ""), "mode": job.data["params"].get("mode", "clip")},
            "stats": None,
        }
        st["posts"].append(post)
        save(st)
    return post


def update_post(post_id: str, **fields) -> dict:
    with _lock:
        st = load()
        post = next(p for p in st["posts"] if p["id"] == post_id)
        for k in ("planned_at", "platform", "title", "url", "status", "account", "auto"):
            if fields.get(k) is not None:
                post[k] = fields[k]
        if fields.get("status") == "postado" and not post.get("posted_at"):
            post["posted_at"] = _now().isoformat(timespec="minutes")
        save(st)
    return post


def delete_post(post_id: str) -> None:
    with _lock:
        st = load()
        st["posts"] = [p for p in st["posts"] if p["id"] != post_id]
        save(st)


def set_channel(url: str, slots: list[str] | None = None, per_day: int | None = None,
                brief: str | None = None) -> dict:
    with _lock:
        st = load()
        if brief is not None:  # perfil do canal: o que o dono considera um bom corte (vale para todos os cortes)
            st["settings"]["brief"] = brief.strip()[:800]
        if url:
            url = url.strip().rstrip("/")
            if re.fullmatch(r"@?[\w.\-]+", url):  # só o @ do canal
                url = "https://www.youtube.com/" + (url if url.startswith("@") else "@" + url)
            st["channel"] = {"url": url}
        if slots:
            st["settings"]["slots"] = slots
        if per_day:
            st["settings"]["per_day"] = per_day
        save(st)
    return st


# ------------------------------------------------------------------ 🎨 modelos visuais por rede
def set_brand(templates_map: dict | None = None, handle: str | None = None, bg_image: str | None = None) -> dict:
    from . import templates
    with _lock:
        st = load()
        if templates_map is not None:
            st["settings"]["templates"] = {k: v for k, v in templates_map.items()
                                           if k in templates.PLATFORMS and v in templates.TEMPLATES}
        if handle is not None:
            st["settings"]["handle"] = handle.strip().lstrip("@")[:40]
        if bg_image is not None:
            st["settings"]["bg_image"] = Path(bg_image).name if bg_image else ""
        save(st)
    return st["settings"]


def template_for(platform: str, st: dict | None = None) -> str:
    from . import templates
    st = st or load()
    return (st["settings"].get("templates") or {}).get(platform) or templates.DEFAULT_BY_PLATFORM.get(platform, "tela_cheia")


def clip_file_for(job, clip: dict, platform: str) -> Path:
    """Arquivo certo para cada rede: a versão com o modelo da rede, se já foi gerada; senão, o corte normal."""
    v = (clip.get("styled") or {}).get(template_for(platform))
    if v and v.get("status") == "done" and v.get("file") and (job.dir / v["file"]).exists():
        return job.dir / v["file"]
    return job.dir / clip["file"]


# ------------------------------------------------------------------ números do canal (yt-dlp, grátis)
def _yt(args: list[str], timeout: int = 300) -> dict:
    from .download import _err, _ytdlp
    out = subprocess.run(_ytdlp() + args, capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise _err(out.stderr, "canal")
    return json.loads(out.stdout)


def _video_stats(url: str) -> dict:
    d = _yt(["--skip-download", "--no-playlist", "-J", url], timeout=120)
    return {"views": d.get("view_count"), "likes": d.get("like_count"), "comments": d.get("comment_count"),
            "upload_date": d.get("upload_date"), "duration": d.get("duration"), "title": d.get("title"),
            "updated": _now().isoformat(timespec="minutes")}


def _words(t: str) -> set[str]:
    from .comments import _words as w
    return set(w(t or ""))


def sync() -> dict:
    """Atualiza os números do canal e dos Shorts postados. Pode levar alguns minutos."""
    st = load()
    ch = st.get("channel")
    if not ch:
        raise RuntimeError("Informe o link do seu canal primeiro (ex.: https://www.youtube.com/@seucanal).")
    data = _yt(["--flat-playlist", "--playlist-end", "200", "-J", ch["url"] + "/shorts"])
    videos = [{"id": e.get("id"), "title": e.get("title"), "views": e.get("view_count"),
               "url": e.get("url") or f"https://www.youtube.com/shorts/{e.get('id')}"}
              for e in (data.get("entries") or []) if e.get("id")]
    snap = {"date": _now().isoformat(timespec="minutes"), "subscribers": data.get("channel_follower_count"),
            "channel": data.get("channel") or data.get("uploader") or data.get("title"), "videos": videos}

    with _lock:
        st = load()
        # liga Shorts postados (sem link) aos vídeos do canal pelo título
        for p in st["posts"]:
            if p["status"] == "postado" and not p.get("url") and p.get("platform") == "youtube":
                tw = _words(p["title"])
                best = max(videos, key=lambda v: len(tw & _words(v["title"])), default=None)
                if best and tw and len(tw & _words(best["title"])) / len(tw) >= 0.6:
                    p["url"] = best["url"]
        st["snapshots"] = (st.get("snapshots") or [])[-89:] + [snap]
        save(st)

    # estatísticas detalhadas (data de upload, curtidas) dos nossos posts e dos Shorts recentes
    for p in [p for p in st["posts"] if p.get("url") and "youtu" in p["url"]][-60:]:
        try:
            stats = _video_stats(p["url"])
            with _lock:
                s2 = load()
                for q in s2["posts"]:
                    if q["id"] == p["id"]:
                        q["stats"] = stats
                save(s2)
            time.sleep(1)  # gentil com o YouTube (evita 429)
        except Exception as e:
            print(f"[central] stats de {p['url']}: {e}")
    return summary()


# ------------------------------------------------------------------ painel e aprendizado
def _bucket_duration(d) -> str | None:
    if not d:
        return None
    return "até 30 s" if d <= 30 else "30–45 s" if d <= 45 else "45–60 s" if d <= 60 else "60 s+"


def _hour_bucket(iso: str | None) -> str | None:
    if not iso:
        return None
    h = int(iso[11:13])
    return "manhã (6–12h)" if 6 <= h < 12 else "tarde (12–18h)" if 12 <= h < 18 else "noite (18–24h)" if h >= 18 else "madrugada"


def insights(st: dict, min_posts: int = 4) -> list[str]:
    """Compara grupos de Shorts postados pela mediana de views. Precisa de alguns posts para valer."""
    rows = [p for p in st["posts"] if p["status"] == "postado" and (p.get("stats") or {}).get("views") is not None]
    if len(rows) < min_posts:
        falta = min_posts - len(rows)
        return [f"Poste mais {falta} Short(s) e sincronize para o DarkClip começar a aprender o que funciona no seu canal."]
    allmed = statistics.median(p["stats"]["views"] for p in rows)
    out = [f"Mediana do canal: {int(allmed):,} views por Short ({len(rows)} Shorts analisados).".replace(",", ".")]
    dims = {
        "duração": lambda p: _bucket_duration(p["meta"].get("duration") or p["stats"].get("duration")),
        "horário": lambda p: _hour_bucket(p.get("posted_at")),
        "estilo de legenda": lambda p: p["meta"].get("style"),
        "enquadramento": lambda p: {"track": "seguindo rosto", "split": "tela dividida", "blur": "desfoque"}.get(
            p["meta"].get("layout") or "", None),
        "formato": lambda p: {"clip": "corte de vídeo", "story": "história narrada"}.get(p["meta"].get("mode") or "", None),
    }
    for name, key in dims.items():
        groups: dict[str, list[int]] = {}
        for p in rows:
            k = key(p)
            if k:
                groups.setdefault(k, []).append(p["stats"]["views"])
        groups = {k: v for k, v in groups.items() if len(v) >= 2}
        if len(groups) < 2:
            continue
        best = max(groups, key=lambda k: statistics.median(groups[k]))
        worst = min(groups, key=lambda k: statistics.median(groups[k]))
        mb, mw = statistics.median(groups[best]), statistics.median(groups[worst]) or 1
        if mb / mw >= 1.3:
            out.append(f"{name.capitalize()}: **{best}** rende {mb / mw:.1f}× mais que {worst} "
                       f"(mediana {int(mb)} vs {int(mw)} views).")
    # a nota da IA prevê as views?
    scored = [(p["meta"].get("score"), p["stats"]["views"]) for p in rows if p["meta"].get("score") is not None]
    if len(scored) >= 6:
        hi = [v for s, v in scored if s >= statistics.median(s for s, _ in scored)]
        lo = [v for s, v in scored if s < statistics.median(s for s, _ in scored)]
        if hi and lo:
            r = statistics.median(hi) / (statistics.median(lo) or 1)
            out.append(f"Nota da IA: clipes de nota alta tiveram {r:.1f}× as views dos de nota baixa"
                       + (" — a nota está acertando." if r >= 1.2 else " — a nota ainda não prevê bem o seu público."))
    return out


def preferences_for_ai() -> str:
    """Perfil do canal (definido pelo dono) + dicas aprendidas, para o prompt da IA.
    O perfil manda; os dados reais só servem para desempatar."""
    st = load()
    parts = []
    brief = (st.get("settings") or {}).get("brief", "").strip()
    if brief:
        parts.append("PERFIL DO CANAL (definido pelo dono; siga com prioridade ao escolher os cortes):\n" + brief)
    try:  # notas 👍/👎 que o dono deu aos clipes
        from .feedback import examples_for_ai
        fb = examples_for_ai()
        if fb:
            parts.append(fb)
    except Exception:
        pass
    tips = [t for t in insights(st) if "×" in t and not t.startswith("Nota da IA")]
    if tips:
        parts.append("DADOS REAIS DO CANAL (use só para desempatar):\n- " + "\n- ".join(t.replace("**", "") for t in tips))
    return "\n\n".join(parts)


def summary() -> dict:
    st = load()
    snaps = st.get("snapshots") or []
    last = snaps[-1] if snaps else None
    now = _now()
    posts = sorted(st["posts"], key=lambda p: p.get("planned_at") or "")
    upcoming = [p for p in posts if p["status"] == "planejado"]
    posted = [p for p in posts if p["status"] == "postado"]
    # views de Shorts nos últimos 90 dias (estimativa: views totais dos Shorts publicados nesse período)
    cutoff = (now - timedelta(days=90)).strftime("%Y%m%d")
    v90 = sum((p.get("stats") or {}).get("views") or 0 for p in posted
              if ((p.get("stats") or {}).get("upload_date") or "99999999") >= cutoff)
    if last and not v90:
        v90 = sum(v.get("views") or 0 for v in last["videos"][:60])  # sem datas: aproxima pelos 60 mais recentes
    growth = None
    if len(snaps) >= 2 and snaps[0].get("subscribers") is not None and last.get("subscribers") is not None:
        growth = last["subscribers"] - snaps[0]["subscribers"]
    top = sorted(last["videos"], key=lambda v: -(v.get("views") or 0))[:5] if last else []
    return {
        "channel": st.get("channel"), "settings": st["settings"],
        "now": now.isoformat(timespec="minutes"), "next_slot": next_slot(st),
        "stats": {"name": (last or {}).get("channel"), "subscribers": (last or {}).get("subscribers"),
                  "shorts": len(last["videos"]) if last else None, "views_90d": v90, "synced": (last or {}).get("date"),
                  "subs_growth": growth},
        "ypp": {"subs": YPP_SUBS, "views": YPP_VIEWS},
        "due": [p for p in upcoming if p["planned_at"] <= now.isoformat(timespec="minutes")],
        "upcoming": upcoming, "posted": posted[-30:][::-1], "top": top,
        "insights": insights(st),
    }


# ------------------------------------------------------------------ postagem automática
def publish_post(post_id: str) -> dict:
    """Envia o vídeo do post para a conta conectada e marca como postado (ou erro)."""
    from . import social
    from .pipeline import Job
    st = load()
    post = next(p for p in st["posts"] if p["id"] == post_id)
    if not post.get("account"):
        raise RuntimeError("Este post não tem conta conectada: escolha uma na aba Contas ou poste pelo 📤.")
    job = Job(post["job"])
    clip = job.data["clips"][post["clip"]]
    with _lock:  # marca "enviando" para o agendador não repetir
        st = load()
        for p in st["posts"]:
            if p["id"] == post_id:
                p["status"], p["error"] = "enviando", None
        save(st)
    try:
        res = social.publish(post["account"], clip_file_for(job, clip, post.get("platform", "youtube")), title=post.get("title") or clip.get("title", ""),
                             description=clip.get("description", ""), hashtags=clip.get("hashtags") or [],
                             duration=clip.get("duration"))
        fields = {"status": "postado", "url": res.get("url"), "note": res.get("note"),
                  "posted_at": _now().isoformat(timespec="minutes"), "error": None}
    except Exception as e:
        tries = (post.get("tries") or 0) + 1
        fields = {"status": "erro" if tries >= 3 else "planejado", "error": str(e)[:400], "tries": tries}
    with _lock:
        st = load()
        for p in st["posts"]:
            if p["id"] == post_id:
                p.update(fields)
                if fields.get("status") == "planejado":  # tenta de novo em 15 min
                    p["planned_at"] = (_now() + timedelta(minutes=15)).isoformat(timespec="minutes")
                post = p
        save(st)
    return post


def run_due() -> list[str]:
    """Chamado a cada minuto pelo servidor: publica os posts automáticos que chegaram na hora."""
    now = _now().isoformat(timespec="minutes")
    done = []
    for p in load()["posts"]:
        if p.get("auto") and p.get("account") and p["status"] == "planejado" and (p.get("planned_at") or "9") <= now:
            publish_post(p["id"])
            done.append(p["id"])
    return done


def plan_all(job_id: str, account: str | None = None, auto: bool = False, platform: str = "youtube",
             every_hours: float | None = None, min_score: int = 0) -> list[dict]:
    """📅 Agendamento em massa: todos os clipes prontos de um trabalho, nos próximos horários livres
    (ou a cada N horas a partir do próximo horário livre)."""
    from .pipeline import Job
    job = Job(job_id)
    clips = [(i, c) for i, c in enumerate(job.data.get("clips", [])) if c.get("file") and not c.get("error")
             and (c.get("score") is None or c["score"] >= min_score)]
    clips.sort(key=lambda ic: -(ic[1].get("score") or 0))      # melhores primeiro
    already = {(p["job"], p["clip"]) for p in load()["posts"]}
    out, when = [], None
    for i, _ in clips:
        if (job_id, i) in already:
            continue
        st = load()
        if every_hours and when:
            when = (datetime.fromisoformat(when) + timedelta(hours=every_hours)).isoformat(timespec="minutes")
        else:
            when = next_slot(st)
        out.append(plan(job_id, i, when, platform, account, auto))
    return out
