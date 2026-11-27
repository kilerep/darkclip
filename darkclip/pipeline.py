"""Orquestra os jobs.

clip  : vídeo longo -> vários Shorts.
        Modo inteligente (links): baixa só legenda + heatmap, escolhe os trechos e então
        baixa APENAS os trechos escolhidos (live de 3 h vira poucos MB).
story : Short dark narrado.
rerender: refaz um clipe com ajustes do editor (início/fim, gancho, estilo, layout…).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

from . import ai, config, render, signals, transcribe
from .download import download, download_audio, download_section, fetch_transcript_only, probe_duration

MARGIN = 4.0  # segundos extras baixados antes/depois de cada trecho (permite ajustes no editor)


def safe_print(msg: str) -> None:
    """Mostra a mensagem sem nunca derrubar o job.

    No Windows o terminal costuma estar em cp1252, que não tem emoji: imprimir "🧠" levantava
    UnicodeEncodeError e o job inteiro morria, perdendo a transcrição que já estava pronta.
    Aqui o que o terminal não souber escrever vira "?" e o trabalho continua.
    """
    try:
        print(msg)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        try:
            print(msg.encode(enc, "replace").decode(enc, "replace"))
        except Exception:
            pass
    except Exception:
        pass



class Job:
    def __init__(self, job_id: str):
        self.id = job_id
        self.dir = config.JOBS_DIR / job_id
        self.file = self.dir / "job.json"
        self.data = json.loads(self.file.read_text(encoding="utf-8")) if self.file.exists() else {}

    @classmethod
    def create(cls, params: dict) -> "Job":
        jid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:5]
        job = cls(jid)
        job.dir.mkdir(parents=True, exist_ok=True)
        job.data = {"id": jid, "status": "queued", "progress": 0, "log": [], "params": params,
                    "created": time.time(), "clips": []}
        job.save()
        return job

    def save(self) -> None:
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(config.redact(json.dumps(self.data, ensure_ascii=False, indent=2)), encoding="utf-8")
        tmp.replace(self.file)

    def note(self, msg: str, progress: int | None = None) -> None:
        """Atualiza a última linha (progresso contínuo, sem encher o log)."""
        if self.data["log"] and self.data["log"][-1].split(":")[0] == msg.split(":")[0]:
            self.data["log"][-1] = msg
        else:
            self.data["log"].append(msg)
        if progress is not None:
            self.data["progress"] = progress
        self.save()

    def step(self, msg: str, progress: int | None = None) -> None:
        safe_print(config.redact(f"[{self.id}] {msg}"))
        self.data["log"].append(msg)
        self.data["log"] = self.data["log"][-60:]
        if progress is not None:
            self.data["progress"] = progress
        self.save()


# ------------------------------------------------------------------ etapas
def _whisper_progress(job: "Job", base: int = 15, span: int = 24):
    from .comments import fmt
    job.step(f"Preparando a transcrição (na 1ª vez baixa o modelo do Whisper, ~{_WHISPER_MB.get(config.WHISPER_MODEL, 500)} MB)…")
    return lambda pct, done, total: job.note(f"Transcrevendo o áudio: {pct}% ({fmt(done)} de {fmt(total)})",
                                             base + int(span * pct / 100))


_WHISPER_MB = {"tiny": 75, "base": 145, "small": 480, "medium": 1500, "large-v3": 3000}


def _has_whisper() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _prepare_source(job: Job, p: dict) -> tuple[dict, list[dict], list[float] | None]:
    """Retorna (fonte, transcrição, energia do áudio)."""
    work = job.dir / "src"
    work.mkdir(parents=True, exist_ok=True)
    lang = p.get("lang", "pt")
    if p.get("upload"):
        up = config.UPLOADS_DIR / Path(p["upload"]).name
        video = work / ("source" + up.suffix)
        shutil.move(str(up), video)
        subs = None
        if p.get("upload_subs"):
            subs = work / "source.vtt"
            shutil.move(str(config.UPLOADS_DIR / Path(p["upload_subs"]).name), subs)
        src = {"video": video, "subs": subs, "title": p.get("title") or up.stem.split("_", 1)[-1],
               "duration": probe_duration(video), "heatmap": None, "chapters": []}
        job.step("Transcrevendo…", 20)
        energy = signals.audio_energy(video)
        dur = src["duration"] or 0
        if not subs and dur > 20 * 60 and p.get("targeted_whisper", True):
            wins = transcribe.merge_windows(signals.audio_peaks(energy), duration=dur)
            if wins:
                job.step(f"Vídeo longo sem legenda: transcrevendo só {len(wins)} trechos promissores…", 22)
                segs = transcribe.whisper_windows(video, wins, lang,
                                                  progress=lambda k, n: job.step(f"Transcrevendo trecho {k} de {n}…"))
                job.step(f"Transcrição via faster-whisper (só {len(wins)} trechos)", 40)
                return src, segs, energy
        segs, how = transcribe.transcribe(video, subs, lang, progress=None if subs else _whisper_progress(job))
        job.step(f"Transcrição via {how}", 40)
        return src, segs, energy

    if p.get("smart", True):
        job.step("Lendo legenda, capítulos e mapa de calor (sem baixar o vídeo)…", 5)
        src = fetch_transcript_only(p["url"], work, lang)
        energy = None
        if src.get("warning"):
            job.step(src["warning"])
        sub_lang = (src.get("sub_lang") or "").split("-")[0].lower()
        if src["subs"] and sub_lang and sub_lang != lang.lower() and _has_whisper():
            # o YouTube às vezes erra o idioma (ex.: fala em português marcada como inglês) e gera legenda sem sentido
            job.step(f"A legenda automática do YouTube está em '{src.get('sub_lang')}', diferente do idioma escolhido "
                     f"('{lang}'): vou transcrever o áudio em {lang} com o Whisper…", 12)
            src["subs"] = None
        if src["subs"]:
            segs, how = transcribe.transcribe(Path("-"), src["subs"], lang)
            how += f" ({src.get('sub_lang')})"
        else:
            try:
                import faster_whisper  # noqa: F401
            except ImportError:
                raise RuntimeError(
                    (src.get("warning") or "Este vídeo não tem legenda") + ". Sem legenda, a transcrição exige o "
                    "faster-whisper (só no PC). Tente de novo em alguns minutos ou escolha um vídeo com legenda.")
            job.step("Sem legenda: baixando só o áudio para transcrever…", 15)
            audio = download_audio(p["url"], work)
            energy = signals.audio_energy(audio)
            dur = src.get("duration") or 0
            if dur > 20 * 60 and p.get("targeted_whisper", True):
                # Live/vídeo longo sem legenda: transcreve só onde há sinal (picos de áudio + mais repetidos)
                hm = sorted(src.get("heatmap") or [], key=lambda h: -h["value"])
                centers = signals.audio_peaks(energy) + [(h["start_time"] + h["end_time"]) / 2 for h in hm[:6]
                                                         if h["value"] >= 0.5]
                r0, r1 = float(p.get("range_start") or 0), float(p.get("range_end") or 0) or dur
                centers = [c for c in centers if r0 <= c <= r1]
                wins = transcribe.merge_windows(centers, duration=dur) if centers else []
                if wins:
                    total = sum(b - a for a, b in wins)
                    job.step(f"Live longa: transcrevendo só {len(wins)} trechos promissores "
                             f"({total / 60:.0f} de {dur / 60:.0f} min)…", 18)
                    segs = transcribe.whisper_windows(
                        audio, wins, lang, progress=lambda k, n: job.step(f"Transcrevendo trecho {k} de {n}…"))
                    how = f"faster-whisper (só {len(wins)} trechos)"
                else:
                    segs, how = transcribe.whisper_transcribe(audio, lang, progress=_whisper_progress(job)), "faster-whisper"
            else:
                segs, how = transcribe.whisper_transcribe(audio, lang, progress=_whisper_progress(job)), "faster-whisper"
        job.step(f"Transcrição via {how}" + (" · heatmap ✓" if src.get("heatmap") else ""), 40)
        if energy is None and p.get("audio_energy", True) and 0 < (src.get("duration") or 0) <= 3 * 3600:
            try:  # só o áudio (~1 MB/min): gritos, risadas e picos de emoção viram o sinal ⚡
                job.step("Ouvindo o áudio (gritos, risadas, picos de emoção)…", 42)
                energy = signals.audio_energy(download_audio(src["url"], work))
            except Exception as e:
                job.step(f"Áudio indisponível ({str(e)[:120]}); seguindo sem o sinal ⚡")
        return src, segs, energy

    job.step("Baixando vídeo completo…", 5)
    src = download(p["url"], work, lang=lang)
    job.step("Transcrevendo…", 25)
    segs, how = transcribe.transcribe(src["video"], src["subs"], lang)
    energy = signals.audio_energy(src["video"])
    job.step(f"Transcrição via {how}", 40)
    return src, segs, energy


def _clip_source(job: Job, clip: dict, src_info: dict, name: str) -> tuple[Path, float]:
    """Arquivo que contém o trecho e o deslocamento (segundo do original onde o arquivo começa)."""
    if src_info.get("video"):
        return job.dir / src_info["video"], 0.0
    sec = clip.get("section")
    if sec and sec["from"] <= clip["start"] and sec["to"] >= clip["end"] and (job.dir / sec["file"]).exists():
        return job.dir / sec["file"], sec["from"]
    a = max(0.0, clip["start"] - MARGIN)
    b = clip["end"] + MARGIN
    if src_info.get("duration"):
        b = min(b, src_info["duration"])
    try:
        f = download_section(src_info["url"], job.dir / "src", a, b, name)
    except RuntimeError as e:
        # Alguns sites/redes não aceitam download parcial: baixa o vídeo inteiro uma vez e reaproveita
        job.step(f"Download por trecho falhou ({str(e)[-120:]}); baixando o vídeo completo…")
        full = download(src_info["url"], job.dir / "src" / "full", subs=False)  # transcrição já existe
        src_info["video"] = str(full["video"].relative_to(job.dir))
        job.save()
        return full["video"], 0.0
    clip["section"] = {"file": str(f.relative_to(job.dir)), "from": a, "to": b}
    return f, a


def _loud(energy: list[float] | None, start: float, end: float, hop: float = 0.5) -> list[tuple[float, float]]:
    """Trechos (relativos ao clipe) com áudio bem acima do normal do vídeo."""
    if not energy:
        return []
    thr = sorted(energy)[int(len(energy) * 0.75)] + 3     # 3 dB acima do 75º percentil do vídeo
    out: list[tuple[float, float]] = []
    for i in range(int(start / hop), min(len(energy), int(end / hop) + 1)):
        if energy[i] >= thr:
            a, b = max(0.0, i * hop - start), min(end, (i + 1) * hop) - start
            if out and a - out[-1][1] <= hop:
                out[-1] = (out[-1][0], b)
            else:
                out.append((a, b))
    return out


def _manual_subs(segs: list[dict]) -> bool:
    """Legenda escrita por frase (sem tempo por palavra): tempo e texto podem não bater com a fala."""
    return any(sg.get("timed") is False for sg in segs[:50])


def _sync_subs(job: Job, p: dict, src: dict, segs: list[dict]) -> list[dict]:
    """⏱️ Confere se a legenda está no tempo da fala (ex.: vídeo com vinheta que a legenda não conta) e corrige."""
    if not _manual_subs(segs) or not _has_whisper() or os.environ.get("DARKCLIP_SUBS_SYNC", "1") == "0":
        return segs
    media = None
    if src.get("video"):
        media = Path(src["video"]) if Path(src["video"]).is_absolute() else job.dir / src["video"]
    if not media or not media.exists():
        media = next((job.dir / "src").glob("audio.*"), None)
    if not media:
        return segs
    try:
        job.step("Conferindo se a legenda está no tempo da fala…")
        d = transcribe.estimate_offset(media, segs, p.get("lang", "pt"), model="base")
    except Exception as e:
        job.step(f"Não deu para conferir o tempo da legenda ({str(e)[:100]})")
        return segs
    if d is None or abs(d) < 0.35:
        job.step("⏱️ Legenda no tempo certo da fala ✓")
        return segs
    job.step(f"⏱️ A legenda estava {abs(d):.1f} s {'adiantada' if d > 0 else 'atrasada'} em relação à fala: corrigido")
    return transcribe.shift(segs, d)


def _caption_words(job: Job, clip: dict, segs: list[dict], video: Path, offset: float, name: str) -> list[dict]:
    """Palavras da legenda do corte. Se a legenda veio escrita por frase, o Whisper escuta o trecho e a
    legenda passa a mostrar exatamente o que é dito, no tempo certo (guardado para refazer sem repetir)."""
    base = transcribe.slice_words(segs, clip["start"], clip["end"])
    if not _manual_subs(segs) or not _has_whisper() or os.environ.get("DARKCLIP_CAPTION_WHISPER", "1") == "0":
        return base
    cache = job.dir / f"{name}_words.json"
    key = [round(clip["start"], 2), round(clip["end"], 2)]
    try:
        if cache.exists():
            data = json.loads(cache.read_text(encoding="utf-8"))
            if data.get("key") == key:
                return data["words"]
        words = transcribe.whisper_words(video, clip["start"] - offset, clip["end"] - offset, job.data["params"].get("lang", "pt"))
        if len(words) >= max(3, len(base) * 0.4):
            cache.write_text(json.dumps({"key": key, "words": words}, ensure_ascii=False), encoding="utf-8")
            return words
    except Exception as e:
        print(f"[legenda] Whisper indisponível para o corte ({e}); usando a legenda original")
    return base


def _render(job: Job, clip: dict, segs: list[dict], idx: int, tpl_name: str | None = None) -> dict:
    p = job.data["params"]
    opts = {**{k: p.get(k) for k in ("crop", "style", "jumpcut", "zoom", "grade", "progress", "hook",
                                      "aspect", "distance", "captions", "sfx", "hook_mode", "ending",
                                      "stickers", "react_zoom")},
            **clip.get("edit", {})}
    name = f"clip_{idx + 1:02d}"
    from . import templates
    tpl = templates.get(tpl_name)
    brand = {}
    if tpl:
        from . import central
        st = central.load()["settings"]
        brand = {"template": tpl, "header_text": clip.get("title") or clip.get("hook"),
                 "handle": st.get("handle") or None, "bg_img": templates.bg_image(st, config.DATA_DIR)}
        if not (clip.get("edit") or {}).get("style") and tpl.get("style"):
            opts["style"] = tpl["style"]  # cada modelo com sua legenda: as versões ficam mais diferentes
    video, offset = _clip_source(job, clip, job.data["source"], name + "_src")
    words = _caption_words(job, clip, segs, video, offset, name)
    music = config.UPLOADS_DIR / Path(p["music"]).name if p.get("music") else None
    energy, e_off = getattr(job, "energy", None), 0.0
    if energy is None:  # corte refeito pelo editor: mede a energia no próprio trecho baixado
        try:
            energy, e_off = signals.audio_energy(video), offset
        except Exception:
            energy = None
    loud = _loud(energy, clip["start"] - e_off, clip["end"] - e_off)
    # 🎣 gancho e final (as versões por rede reaproveitam a escolha do corte principal)
    from . import hooks
    ret = clip.get("retention") if tpl and clip.get("retention") else None
    if not ret:
        ret = hooks.decide(clip, opts.get("hook_mode") or "auto", opts.get("ending") or "auto", loud, words,
                           hook_on=opts.get("hook", True) is not False, energy=energy, e_off=e_off)
    # 😂 momentos de reação (figurinha + zoom no rosto); as versões por rede reaproveitam os mesmos
    st_on, rz_on = opts.get("stickers") is True, opts.get("react_zoom", True) is not False
    if tpl and clip.get("reactions") is not None:
        reacts = clip["reactions"]
    elif st_on or rz_on:
        from . import reacoes
        reacts = reacoes.detect(energy, clip["start"], clip["end"], words, e_off=e_off)
    else:
        reacts = []
    mine = ((clip.get("edit") or {}).get("hook") or "").strip()
    if mine and not tpl:  # o texto que você escreveu no ✏️ Editar vence a escolha automática
        ret = {**ret, **({"teaser_text": mine} if ret.get("teaser") else {"hook": mine})}
    teaser = tuple(ret["teaser"]) if ret.get("teaser") else None
    out = job.dir / (f"{name}_{tpl_name}.mp4" if tpl else f"{name}.mp4")
    info = render.render_clip(
        video, clip["start"] - offset, clip["end"] - offset, words, out,
        hook=ret.get("hook"), teaser=teaser, teaser_text=ret.get("teaser_text"), loop=bool(ret.get("loop")),
        mode=opts.get("crop") or "auto", grade=opts.get("grade", True) is not False,
        jumpcut=opts.get("jumpcut", True) is not False, zoom=opts.get("zoom", True) is not False,
        style=opts.get("style") or "amarelo", emphasis=clip.get("emphasis"),
        progress=opts.get("progress", True) is not False, music=music if music and music.exists() else None,
        aspect=opts.get("aspect") or "9:16", distance=opts.get("distance") or "padrao",
        captions=opts.get("captions", True) is not False, loud=loud, sfx=opts.get("sfx", True) is not False,
        reactions=reacts, stickers=st_on, react_zoom=rz_on, **brand)
    if tpl:
        return {"file": out.name, "thumb": out.with_suffix(".jpg").name, "duration": info["duration"],
                "template": tpl_name, "v": int(time.time())}
    clip.update(file=out.name, thumb=out.with_suffix(".jpg").name, duration=info["duration"],
                render=info, v=int(time.time()), retention=ret, reactions=reacts)
    return info


def _comments(job: Job, p: dict, src: dict, segs: list[dict]) -> dict | None:
    """💬 Quais partes o público comenta (só para links do YouTube/plataformas com comentários)."""
    if not p.get("comments", True) or not src.get("url"):
        return None
    from . import comments as cm
    job.step("Lendo comentários do público…", 46)
    try:
        raw, _ = cm.fetch_comments(src["url"], int(p.get("max_comments", 600)))
        res = cm.analyze(raw, src.get("duration") or None, segs)
        if src.get("was_live"):  # replay de live: picos do chat também contam
            try:
                chat = cm.analyze_chat(cm.fetch_live_chat(src["url"], job.dir / "src"), src.get("duration"))
                job.step(f"💬 chat da live: {chat['total']} mensagens")
                res = cm.merge(res, chat)
            except Exception as e:
                job.step(f"Chat da live indisponível ({str(e)[:120]})")
        (job.dir / "comments.json").write_text(json.dumps({"analysis": res, "themes": cm.themes(raw)},
                                                          ensure_ascii=False), encoding="utf-8")
        job.data["source"]["comments"] = {"total": res["total"], "mapped": res["mapped"]}
        job.step(f"💬 {res['total']} comentários, {res['mapped']} citam um momento do vídeo", 48)
        return res if res["mapped"] else None
    except Exception as e:  # comentários são um bônus: nunca derrubam o trabalho
        job.step(f"Comentários indisponíveis ({str(e)[:160]})")
        return None


def _hints(src: dict, comments: dict | None) -> list[str]:
    """Picos do público (heatmap + comentários/chat) para o Gemini verificar."""
    from .comments import fmt
    out = []
    hm = sorted(src.get("heatmap") or [], key=lambda h: -h["value"])
    for h in hm[:5]:
        if h["value"] >= 0.5:
            out.append(f"{fmt(h['start_time'])}–{fmt(h['end_time'])}: muito reassistido pelo público "
                       f"(intensidade {h['value']:.2f})")
    for pk in (comments or {}).get("peaks", [])[:5]:
        ex = pk["comments"][0]["text"][:80].replace("\n", " ") if pk["comments"] else ""
        out.append(f"{fmt(pk['start'])}–{fmt(pk['end'])}: citado nos comentários/chat ({pk['mentions']}x) — \"{ex}\"")
    return out


def _vision_engine(p: dict) -> str | None:
    """Quem "assiste" o vídeo: gemini (imagem + áudio) | claude (quadros + fala) | None."""
    want = (p.get("vision") or config.VISION).lower()
    if want == "off" or not p.get("visual", True):
        return None
    if want in ("auto", "gemini") and config.HAS_GEMINI:
        return "gemini"
    if want in ("auto", "claude") and config.HAS_CLAUDE:
        return "claude"
    return None


def _lowres_video(job: Job, src: dict) -> Path | None:
    """Vídeo local para tirar quadros (no modo inteligente o vídeo completo não é baixado)."""
    if job.data.get("source", {}).get("video"):
        return job.dir / job.data["source"]["video"]
    if src.get("video"):
        return Path(src["video"])
    if src.get("url"):
        return download(src["url"], job.dir / "src" / "lowres", subs=False, max_height=360)["video"]
    return None


def _visual(job: Job, p: dict, src: dict, comments: dict | None = None, segs: list[dict] | None = None) -> dict | None:
    """👁️ A IA assiste o vídeo e aponta os momentos fortes (Gemini; sem Gemini, o Claude por quadros)."""
    engine = _vision_engine(p)
    if not engine:
        return None
    dur = src.get("duration") or 0
    r0, r1 = float(p.get("range_start") or 0), float(p.get("range_end") or 0) or dur
    n = max(8, int(p.get("n_clips", 4)) * 3)
    try:
        if engine == "gemini":
            if dur > 3 * 3600:
                job.step("Vídeo com mais de 3 h: o Gemini foi pulado (use 'De/Até' para escolher um trecho)")
                return None
            from . import gemini
            job.step("Gemini assistindo o vídeo (imagem + áudio)…", 49)
            local = job.dir / job.data["source"]["video"] if job.data["source"].get("video") else None
            res = gemini.find_moments(url=src.get("url"), path=local, duration=dur,
                                      niche=p.get("niche", ""), request=p.get("request", ""), n=n,
                                      hints=_hints(src, comments), on_retry=job.step)
        else:
            from . import vision
            job.step("Claude assistindo o vídeo (quadros-chave + fala)…", 49)
            video = _lowres_video(job, src)
            frames = int(min(100, max(30, (r1 - r0) / 20)))  # ~1 quadro a cada 20 s, entre 30 e 100
            res = vision.analyze(video, segs, workdir=job.dir / "visao", start=r0, end=r1 or None,
                                 niche=p.get("niche", ""), request=p.get("request", ""), n=n, max_frames=frames)
        (job.dir / "visual.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        job.step(f"👁️ {engine.capitalize()} ({res.get('model', '')}) marcou {len(res.get('moments', []))} momentos", 51)
        return res
    except Exception as e:
        job.step(f"Análise visual indisponível ({str(e)[:200]})")
        return None


def run_analyze(job: Job) -> None:
    """🔍 Analisar vídeo: o que acontece, gancho, linha do tempo, melhores momentos e riscos."""
    from . import vision
    p = {**job.data["params"], "smart": True}
    src, segs, _ = _prepare_source(job, p)
    job.data["source"] = {"title": src["title"], "url": src.get("url"), "duration": src.get("duration"),
                          "video": str(Path(src["video"]).relative_to(job.dir)) if src.get("video") else None}
    comments = _comments(job, p, src, segs) if src.get("url") else None
    engine = _vision_engine({**p, "visual": True})
    if engine == "claude":
        job.step("Claude assistindo o vídeo (quadros-chave + fala)…", 50)
        video = _lowres_video(job, src)
        dur = src.get("duration") or 0
        res = vision.analyze(video, segs, workdir=job.dir / "visao", niche=p.get("niche", ""),
                             request=p.get("request", ""), max_frames=int(min(100, max(30, dur / 15))))
    elif engine == "gemini":
        res = _visual(job, {**p, "visual": True}, src, comments, segs) or {}
        res.setdefault("timeline", [])
        res.setdefault("hook_analysis", "")
        res.setdefault("risks", "")
    else:
        raise RuntimeError("Para analisar o vídeo pelo app, coloque ANTHROPIC_API_KEY ou GEMINI_API_KEY no .env. "
                           "Sem chave, use a skill /assistir-video no Claude Code.")
    md = vision.report_md(res, src["title"])
    if comments and comments.get("peaks"):
        from .comments import fmt
        md += "\n## O que o público comenta\n" + "\n".join(
            f"- {fmt(pk['start'])}–{fmt(pk['end'])} ({pk['mentions']} menções): "
            f"{pk['comments'][0]['text'][:120] if pk['comments'] else ''}" for pk in comments["peaks"][:6]) + "\n"
    (job.dir / "analise.md").write_text(md, encoding="utf-8")
    job.data["analysis"] = {"markdown": md, "engine": engine}
    job.save()


def run_clip(job: Job) -> None:
    p = job.data["params"]
    src, segs, energy = _prepare_source(job, p)
    if not segs:
        raise RuntimeError("Transcrição vazia: o vídeo não tem fala/legenda.")
    segs = _sync_subs(job, p, src, segs)
    (job.dir / "transcript.json").write_text(json.dumps(segs, ensure_ascii=False), encoding="utf-8")
    job.data["source"] = {
        "title": src["title"], "url": src.get("url"), "duration": src.get("duration"),
        "license": src.get("license"), "channel": src.get("channel"),
        "video": str(src["video"].relative_to(job.dir)) if src.get("video") else None,
        "has_heatmap": bool(src.get("heatmap")),
    }
    job.step(f"Fonte: {src['title']} ({(src.get('duration') or 0) / 60:.0f} min)", 45)

    job.energy = energy  # usado pelos cortes de silêncio (não corta ação barulhenta sem fala)
    comments = _comments(job, p, src, segs)
    visual = _visual(job, p, src, comments, segs)

    # intervalo (ex.: só de 2:00:00 até 7:00:00 de uma live) e divisão em partes
    dur = src.get("duration") or (segs[-1]["end"] if segs else 0)
    r0 = float(p.get("range_start") or 0)
    r1 = float(p.get("range_end") or 0) or dur
    part = float(p.get("part_min") or 0) * 60
    parts = [(r0, r1)]
    if part and r1 - r0 > part * 1.2:
        parts = [(t, min(t + part, r1)) for t in _frange(r0, r1, part)]
    total_parts = len(parts)
    n = int(p.get("n_clips", 4))
    engine = None
    for k, (a, b) in enumerate(parts, 1):
        seg_k = [x for x in segs if x["start"] >= a and x["end"] <= b + 1]
        label = f"Parte {k} de {total_parts} ({_hms(a)}–{_hms(b)})" if total_parts > 1 else "Analisando momentos virais…"
        base = 52 + int(46 * (k - 1) / total_parts)
        job.step(label, base)
        if len(seg_k) < 3:
            job.step(f"{label}: sem fala suficiente, pulando")
            continue
        ai._ON_RETRY = job.step
        if ai.llm_name() == "gemini" and ai.has_llm():
            job.step("🧠 Gemini lendo a transcrição para escolher os cortes com contexto…")
        clips, engine = ai.select_clips(seg_k, n=n, min_s=int(p.get("min_s", 20)),
                                        max_s=int(p.get("max_s", 58)), title=src["title"], niche=p.get("niche", ""),
                                        heatmap=src.get("heatmap"), energy=energy, chapters=src.get("chapters"),
                                        comments=comments, visual=visual, request=p.get("request", ""),
                                        hook_mode=p.get("hook_mode") or "auto")
        clips = [c for c in clips if c["start"] >= a - 1 and c["end"] <= b + 15]
        job.data["engine"] = engine
        job.step(f"{label}: {len(clips)} trechos (motor: {engine})")
        clips.sort(key=lambda c: c["start"]) if total_parts > 1 else None  # por parte: em ordem do vídeo
        for i, c in enumerate(clips):
            idx = len(job.data["clips"])
            c["part"] = k if total_parts > 1 else None
            job.step(f"{label} · corte {i + 1} de {len(clips)} ({_hms(c['start'])}, nota {c['score']})",
                     base + int(46 / total_parts * (i + 1) / max(1, len(clips))))
            try:
                _render(job, c, segs, idx)
            except Exception as e:  # um clipe com problema não derruba os outros
                c["error"] = str(e)[-400:]
                job.step(f"Corte {idx + 1} falhou: {str(e)[-200:]}")
            job.data["clips"].append(c)
            job.save()
    if not job.data["clips"]:
        raise RuntimeError("Nenhum trecho encontrado no intervalo escolhido.")
    if all(c.get("error") for c in job.data["clips"]):
        raise RuntimeError(job.data["clips"][0]["error"])


def _frange(a: float, b: float, step: float):
    t = a
    while t < b - 1:
        yield t
        t += step


def _hms(t: float) -> str:
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def run_tool(job: Job) -> None:
    """Ferramentas avulsas no vídeo inteiro: 'legendar' (legenda animada) e 'silencios' (tira as pausas)."""
    p = {**job.data["params"], "smart": False}   # precisa do vídeo completo
    src, segs, _ = _prepare_source(job, p)
    video = src["video"]
    dur = probe_duration(video)
    job.data["source"] = {"title": src["title"], "url": src.get("url"), "duration": dur,
                          "video": str(video.relative_to(job.dir))}
    words = transcribe.slice_words(segs, 0, dur) if segs else []
    tool = p["mode"]
    job.step("Legendando o vídeo inteiro…" if tool == "legendar" else "Tirando os silêncios…", 60)
    out = job.dir / "clip_01.mp4"
    info = render.render_clip(
        video, 0, dur, words, out, hook=None, mode=p.get("crop") or "auto", grade=bool(p.get("grade", False)),
        jumpcut=tool == "silencios" or bool(p.get("jumpcut", False)), zoom=False,
        style=p.get("style") or "amarelo", progress=False, aspect=p.get("aspect") or "original",
        distance=p.get("distance") or "padrao", captions=tool == "legendar" or bool(p.get("captions", False)))
    job.data["clips"].append({"file": out.name, "thumb": out.with_suffix(".jpg").name, "title": src["title"],
                              "description": "", "hashtags": [], "score": None, "duration": info["duration"],
                              "render": info, "v": int(time.time())})
    if tool == "silencios":
        job.step(f"Removidos {max(0.0, info['removed']):.1f} s de silêncio ({info['cuts']} cortes)")


def render_styled(job: Job, idx: int, tpl_name: str) -> None:
    """🎨 Gera a versão do corte com um modelo visual (para postar numa rede diferente)."""
    def put(entry: dict) -> None:  # relê o job do disco: não apaga notas ou edições feitas enquanto renderizava
        fresh = Job(job.id)
        fresh.data["clips"][idx].setdefault("styled", {})[tpl_name] = entry
        fresh.save()

    put({"template": tpl_name, "status": "rendering"})
    clip = Job(job.id).data["clips"][idx]
    try:
        segs = json.loads((job.dir / "transcript.json").read_text(encoding="utf-8"))
        put({**_render(job, clip, segs, idx, tpl_name), "status": "done"})
    except Exception as e:
        put({"template": tpl_name, "status": "error", "error": config.redact(str(e))[-400:]})


def rerender(job: Job, idx: int) -> None:
    clip = job.data["clips"][idx]
    clip["status"] = "rendering"
    clip.pop("styled", None)  # o corte mudou: as versões com modelo precisam ser geradas de novo
    job.save()
    try:
        segs = json.loads((job.dir / "transcript.json").read_text(encoding="utf-8"))
        ed = clip.get("edit", {})
        for k in ("start", "end", "hook", "title", "description"):
            if ed.get(k) not in (None, ""):
                clip[k] = ed[k]
        if ed.get("emphasis") is not None:
            clip["emphasis"] = ed["emphasis"]
        if clip["end"] - clip["start"] < 3:
            raise RuntimeError("Clipe curto demais.")
        _render(job, clip, segs, idx)
        clip.pop("error", None)
    except Exception as e:
        clip["error"] = str(e)[-400:]
    clip["status"] = "done"
    job.save()


def run_story(job: Job) -> None:
    from . import tts
    p = job.data["params"]
    job.step("Escrevendo roteiro…", 10)
    story = ai.write_story(p.get("topic", ""), p.get("script") or None, p.get("formato", "livre"))
    job.step(f"Roteiro: {story['title']}", 30)
    job.step("Gerando narração…", 35)
    mp3, words = tts.narrate(story["script"], job.dir / "voz.mp3", voice=p.get("voice", config.VOICE))
    bg = None
    if p.get("bg_upload"):
        bg = config.UPLOADS_DIR / Path(p["bg_upload"]).name
    elif p.get("bg_url"):
        job.step("Baixando vídeo de fundo…", 45)
        bg = download(p["bg_url"], job.dir / "bg", subs=False)["video"]
    music = config.UPLOADS_DIR / Path(p["music"]).name if p.get("music") else None
    job.step("Renderizando Short…", 60)
    out = job.dir / "clip_01.mp4"
    render.render_story(mp3, words, out, story["hook"], background=bg, music=music,
                        style=p.get("style") or "amarelo", emphasis=story.get("emphasis"))
    job.data["clips"].append({
        "file": out.name, "thumb": out.with_suffix(".jpg").name, "title": story["title"],
        "hook": story["hook"], "description": story["description"], "hashtags": story["hashtags"],
        "script": story["script"], "score": None, "duration": round(probe_duration(out), 1),
    })
    job.save()


def run(job: Job) -> None:
    from . import costs
    costs.reset()
    job.data["status"] = "running"
    job.save()
    try:
        mode = job.data["params"].get("mode")
        (run_story if mode == "story" else run_tool if mode in ("legendar", "silencios")
         else run_analyze if mode == "analisar" else run_clip)(job)
        job.data["status"] = "done"
        job.data["cost"] = costs.summary()
        job.step(costs.human(job.data["cost"]))
        job.step("Pronto! ✅", 100)
    except Exception as e:
        job.data["status"] = "error"
        job.data["error"] = re.sub(r"\s+", " ", str(e))[:1500]
        job.step(f"Erro: {job.data['error']}")
    finally:
        shutil.rmtree(job.dir / "bg", ignore_errors=True)
        job.save()
