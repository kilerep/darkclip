"""Publicação/agendamento no YouTube Shorts (e outras redes) via Postiz CLI.

Requer: npm i -g postiz  +  POSTIZ_API_KEY (e POSTIZ_API_URL se self-hosted)
e o ID da integração do YouTube (postiz integrations:list) em POSTIZ_YOUTUBE_ID.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def available() -> bool:
    return bool(shutil.which("postiz") and os.environ.get("POSTIZ_API_KEY") and os.environ.get("POSTIZ_YOUTUBE_ID"))


def _postiz(*args: str) -> str:
    p = subprocess.run(["postiz", *args], capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip()[-800:] or p.stdout.strip()[-800:])
    return p.stdout


def publish_youtube(video: Path, title: str, description: str, hashtags: list[str],
                    when_iso: str | None = None, privacy: str = "public") -> dict:
    if not available():
        raise RuntimeError("Postiz não configurado (instale o CLI e defina POSTIZ_API_KEY e POSTIZ_YOUTUBE_ID).")
    integ = os.environ["POSTIZ_YOUTUBE_ID"]
    up = json.loads(_postiz("upload", str(video)))  # regra: mídia sempre via postiz upload
    tags = [{"value": h.lstrip("#"), "label": h.lstrip("#")} for h in hashtags[:15]]
    title = title if "#shorts" in title.lower() else f"{title[:90]} #shorts"
    settings = {"title": title[:100], "type": privacy, "selfDeclaredMadeForKids": "no", "tags": tags}
    body = description.strip() + "\n\n" + " ".join(hashtags)
    args = ["posts:create", "-c", body, "-p", "youtube", "-i", integ, "-m", up["path"],
            "--settings", json.dumps(settings, ensure_ascii=False)]
    if not when_iso:  # sem data: publica daqui a 5 minutos
        from datetime import datetime, timedelta, timezone
        when_iso = (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    args += ["-s", when_iso]
    out = _postiz(*args)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"output": out}
