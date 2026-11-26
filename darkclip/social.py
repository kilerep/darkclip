"""🔗 Contas conectadas e postagem automática.

Facebook (Página) + Instagram (conta profissional ligada à Página) — Graph API da Meta, com um app SEU
em modo de desenvolvimento (funciona para quem é administrador do app, sem análise da Meta):
  • Reels da Página:  /{page}/video_reels  start → upload (rupload) → finish (PUBLISHED)
  • Vídeo longo:      /{page}/videos (upload do arquivo)
  • Reels do Instagram: /{ig}/media (REELS, upload_type=resumable) → upload (rupload) → /{ig}/media_publish

YouTube — YouTube Data API v3 com um cliente OAuth "App para computador" SEU.
  ⚠️ Regra do Google: projetos não verificados (criados após 28/07/2020) só conseguem enviar vídeos PRIVADOS
  até passarem pela auditoria. O DarkClip envia e avisa; você publica no YouTube Studio com 1 toque.

TikTok e Kwai não têm API aberta para postar: continuam pelo botão 📤 (compartilhar) do celular.

Os tokens ficam só no seu PC, em data/contas.json.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

from . import config

FILE = config.DATA_DIR / "contas.json"
GRAPH_V = os.environ.get("DARKCLIP_GRAPH_VERSION", "v26.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_V}"
YT_SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"


class SocialError(RuntimeError):
    pass


def _http():
    import httpx
    return httpx.Client(timeout=httpx.Timeout(60, read=600, write=600), follow_redirects=True)


# ------------------------------------------------------------------ armazenamento
def load() -> dict:
    if FILE.exists():
        try:
            return json.loads(FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"meta": {"pages": []}, "youtube": {"channels": []}}


def save(d: dict) -> None:
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        os.chmod(FILE, 0o600)
    except OSError:
        pass


def public_view() -> dict:
    """O que o app mostra (sem tokens)."""
    d = load()
    accounts = []
    for p in d["meta"]["pages"]:
        accounts.append({"id": f"facebook:{p['id']}", "network": "facebook", "name": p["name"]})
        if p.get("ig"):
            accounts.append({"id": f"instagram:{p['ig']['id']}", "network": "instagram",
                             "name": "@" + (p["ig"].get("username") or p["ig"]["id"]), "page": p["name"]})
    for c in d["youtube"]["channels"]:
        accounts.append({"id": f"youtube:{c['id']}", "network": "youtube", "name": c["title"]})
    return {"accounts": accounts, "meta_app": bool(d["meta"].get("app_id")),
            "youtube_client": bool(d["youtube"].get("client_id"))}


def _check(r, what: str) -> dict:
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text[:300]}
    if r.status_code >= 400 or (isinstance(data, dict) and data.get("error")):
        err = data.get("error") if isinstance(data, dict) else None
        msg = (err.get("message") if isinstance(err, dict) else err) or r.text[:300]
        hint = ""
        if r.status_code in (401, 403) or "token" in str(msg).lower():
            hint = " → token vencido ou sem permissão: reconecte a conta na aba Contas."
        raise SocialError(f"{what}: {msg}{hint}")
    return data


# ------------------------------------------------------------------ Meta (Facebook + Instagram)
def meta_connect(app_id: str, app_secret: str, user_token: str) -> dict:
    """Troca o token curto (Graph API Explorer) por um longo e busca as Páginas (+ Instagram ligado)."""
    with _http() as h:
        long = _check(h.get(f"{GRAPH}/oauth/access_token", params={
            "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": app_secret,
            "fb_exchange_token": user_token}), "trocar token")["access_token"]
        pages = _check(h.get(f"{GRAPH}/me/accounts", params={
            "fields": "id,name,access_token,instagram_business_account{id,username}", "limit": 100,
            "access_token": long}), "listar páginas").get("data", [])
    if not pages:
        raise SocialError("Nenhuma Página encontrada. Confirme que você é admin da Página e marcou as permissões "
                          "pages_show_list e pages_manage_posts no token.")
    d = load()
    d["meta"] = {"app_id": app_id, "app_secret": app_secret, "connected": int(time.time()), "pages": [
        {"id": p["id"], "name": p["name"], "token": p["access_token"],
         "ig": p.get("instagram_business_account")} for p in pages]}
    save(d)
    return public_view()


def _page(page_id: str | None = None, ig_id: str | None = None) -> dict:
    for p in load()["meta"]["pages"]:
        if p["id"] == page_id or (ig_id and (p.get("ig") or {}).get("id") == ig_id):
            return p
    raise SocialError("conta não conectada")


def _rupload(h, url: str, token: str, video: Path) -> dict:
    size = video.stat().st_size
    with video.open("rb") as f:
        r = h.post(url, content=f.read(), headers={"Authorization": f"OAuth {token}", "offset": "0",
                                                   "file_size": str(size), "Content-Type": "application/octet-stream"})
    return _check(r, "enviar arquivo")


def publish_facebook(page_id: str, video: Path, description: str, title: str = "",
                     duration: float | None = None) -> dict:
    p = _page(page_id)
    tok = p["token"]
    with _http() as h:
        if duration is not None and duration > 90:  # Reels do Facebook vão até 90 s: acima disso, vídeo normal
            with video.open("rb") as f:
                r = h.post(f"https://graph-video.facebook.com/{GRAPH_V}/{page_id}/videos",
                           data={"description": description, "title": title[:250], "access_token": tok},
                           files={"source": (video.name, f, "video/mp4")})
            vid = _check(r, "enviar vídeo")["id"]
            return {"id": vid, "url": f"https://www.facebook.com/{page_id}/videos/{vid}"}
        start = _check(h.post(f"{GRAPH}/{page_id}/video_reels", data={"upload_phase": "start", "access_token": tok}),
                       "iniciar reel")
        vid = start["video_id"]
        _rupload(h, start.get("upload_url") or f"https://rupload.facebook.com/video-upload/{GRAPH_V}/{vid}", tok, video)
        _check(h.post(f"{GRAPH}/{page_id}/video_reels", data={
            "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": description,
            "access_token": tok}), "publicar reel")
    return {"id": vid, "url": f"https://www.facebook.com/reel/{vid}"}


def publish_instagram(ig_id: str, video: Path, caption: str, wait: float = 600) -> dict:
    p = _page(ig_id=ig_id)
    tok = p["token"]
    with _http() as h:
        c = _check(h.post(f"{GRAPH}/{ig_id}/media", data={
            "media_type": "REELS", "upload_type": "resumable", "caption": caption[:2200], "share_to_feed": "true",
            "access_token": tok}), "criar reel no Instagram")
        cid = c["id"]
        _rupload(h, c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_V}/{cid}", tok, video)
        t0 = time.time()
        while True:  # o Instagram processa o vídeo antes de deixar publicar
            st = _check(h.get(f"{GRAPH}/{cid}", params={"fields": "status_code,status", "access_token": tok}),
                        "status do reel")
            if st.get("status_code") == "FINISHED":
                break
            if st.get("status_code") in ("ERROR", "EXPIRED"):
                raise SocialError(f"Instagram recusou o vídeo: {st.get('status')}")
            if time.time() - t0 > wait:
                raise SocialError("Instagram demorou demais para processar o vídeo")
            time.sleep(5)
        pub = _check(h.post(f"{GRAPH}/{ig_id}/media_publish", data={"creation_id": cid, "access_token": tok}),
                     "publicar no Instagram")
        link = _check(h.get(f"{GRAPH}/{pub['id']}", params={"fields": "permalink", "access_token": tok}),
                      "link do post").get("permalink")
    return {"id": pub["id"], "url": link}


# ------------------------------------------------------------------ YouTube (OAuth "App para computador")
def youtube_auth_url(client_id: str, client_secret: str, redirect: str) -> str:
    d = load()
    state = secrets.token_urlsafe(16)
    d["youtube"].update(client_id=client_id.strip(), client_secret=client_secret.strip(), state=state, redirect=redirect)
    save(d)
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": client_id.strip(), "redirect_uri": redirect, "response_type": "code", "scope": YT_SCOPES,
        "access_type": "offline", "prompt": "consent", "state": state})


def youtube_callback(code: str, state: str) -> dict:
    d = load()
    y = d["youtube"]
    if not state or state != y.get("state"):
        raise SocialError("pedido de conexão inválido (state) — tente conectar de novo")
    with _http() as h:
        tok = _check(h.post("https://oauth2.googleapis.com/token", data={
            "code": code, "client_id": y["client_id"], "client_secret": y["client_secret"],
            "redirect_uri": y["redirect"], "grant_type": "authorization_code"}), "token do Google")
        ch = _check(h.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true"},
                          headers={"Authorization": f"Bearer {tok['access_token']}"}), "canal").get("items", [])
    if not ch:
        raise SocialError("Essa conta Google não tem canal no YouTube")
    c = ch[0]
    y["channels"] = [x for x in y.get("channels", []) if x["id"] != c["id"]] + [{
        "id": c["id"], "title": c["snippet"]["title"], "refresh_token": tok.get("refresh_token"),
        "access_token": tok["access_token"], "expires": time.time() + tok.get("expires_in", 3600) - 60}]
    y.pop("state", None)
    save(d)
    return public_view()


def _yt_token(channel_id: str) -> str:
    d = load()
    y = d["youtube"]
    c = next((x for x in y["channels"] if x["id"] == channel_id), None)
    if not c:
        raise SocialError("canal do YouTube não conectado")
    if c.get("expires", 0) > time.time():
        return c["access_token"]
    if not c.get("refresh_token"):
        raise SocialError("reconecte o YouTube na aba Contas")
    with _http() as h:
        tok = _check(h.post("https://oauth2.googleapis.com/token", data={
            "refresh_token": c["refresh_token"], "client_id": y["client_id"], "client_secret": y["client_secret"],
            "grant_type": "refresh_token"}), "renovar acesso do YouTube (em modo de teste do Google isso vence a cada 7 dias)")
    c["access_token"], c["expires"] = tok["access_token"], time.time() + tok.get("expires_in", 3600) - 60
    save(d)
    return c["access_token"]


def publish_youtube(channel_id: str, video: Path, title: str, description: str, tags: list[str],
                    privacy: str = "public") -> dict:
    token = _yt_token(channel_id)
    title = title if "#shorts" in title.lower() else f"{title[:90]} #shorts"
    meta = {"snippet": {"title": title[:100], "description": description[:4900],
                        "tags": [t.lstrip("#") for t in tags][:15], "categoryId": "24"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": bool(os.environ.get("DARKCLIP_SYNTHETIC", ""))}}
    size = video.stat().st_size
    with _http() as h:
        r = h.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                   json=meta, headers={"Authorization": f"Bearer {token}", "X-Upload-Content-Type": "video/mp4",
                                       "X-Upload-Content-Length": str(size)})
        if r.status_code >= 400:
            _check(r, "iniciar envio ao YouTube")
        with video.open("rb") as f:
            up = _check(h.put(r.headers["Location"], content=f.read(), headers={"Content-Type": "video/mp4"}),
                        "enviar ao YouTube")
    st = (up.get("status") or {}).get("privacyStatus")
    note = None
    if privacy == "public" and st == "private":
        note = ("O YouTube deixou o vídeo PRIVADO (projeto Google não verificado). Abra o YouTube Studio e mude "
                "para Público, ou peça a auditoria do projeto para liberar.")
    return {"id": up["id"], "url": f"https://youtube.com/shorts/{up['id']}", "note": note}


# ------------------------------------------------------------------ roteador
def publish(account: str, video: Path, *, title: str, description: str, hashtags: list[str],
            duration: float | None = None) -> dict:
    network, _, acc_id = account.partition(":")
    text = (description.strip() + "\n\n" + " ".join(hashtags)).strip()
    if network == "facebook":
        return publish_facebook(acc_id, video, f"{title}\n\n{text}".strip(), title, duration)
    if network == "instagram":
        return publish_instagram(acc_id, video, f"{title}\n\n{text}".strip())
    if network == "youtube":
        return publish_youtube(acc_id, video, title, text, hashtags)
    raise SocialError(f"{network}: postagem automática não disponível (use o botão 📤)")


def remove(account: str) -> dict:
    d = load()
    network, _, acc_id = account.partition(":")
    if network in ("facebook", "instagram"):
        d["meta"]["pages"] = [p for p in d["meta"]["pages"]
                              if p["id"] != acc_id and (p.get("ig") or {}).get("id") != acc_id]
    elif network == "youtube":
        d["youtube"]["channels"] = [c for c in d["youtube"]["channels"] if c["id"] != acc_id]
    save(d)
    return public_view()
