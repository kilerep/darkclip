"""Renderização 9:16 com ffmpeg.

Recursos: câmera que segue o rosto (sendcmd), tela dividida para 2 pessoas, fundo desfocado,
zoom de impacto alternado por frase, remoção de silêncios (jump cuts), visual dark,
legendas animadas com estilos e palavras-ênfase, gancho no topo e barra de progresso.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from . import config
from .download import probe_size

W, H = config.OUT_W, config.OUT_H
ASPECTS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def set_aspect(aspect: str, src_w: int = 0, src_h: int = 0) -> tuple[int, int]:
    """Define o tamanho de saída: 9:16 (Shorts/Reels/TikTok), 4:5 (feed), 1:1 ou 'original' (formato da fonte)."""
    global W, H
    if aspect in ASPECTS:
        W, H = ASPECTS[aspect]
    elif src_w and src_h:
        W, H = (1920, 1080) if src_w > src_h * 1.1 else (1080, 1920) if src_h > src_w * 1.1 else (1080, 1080)
    else:
        W, H = ASPECTS["9:16"]
    return W, H
FPS = 30
DARK_GRADE = "eq=contrast=1.08:brightness=-0.04:saturation=0.8,vignette=angle=PI/5"

# ------------------------------------------------------------------ estilos de legenda
# cores ASS = &HAABBGGRR
STYLES = {
    # chars 18: com 16 a maioria dos blocos virava uma palavra só em português
    # ("DINHEIRO, DINHEIRO," já tem 19 caracteres) e o destaque não tinha o que destacar.
    # 20 foi medido e quebra em duas linhas no pior caso; 18 cabe sempre em uma (máx. 865 px de 960).
    "amarelo": {"size": 84, "hl": "&H0000E5FF&", "emph": "&H0066FF33&", "upper": True, "words": 3, "chars": 18,
                "bord": 7, "pill": False},
    "verde":   {"size": 84, "hl": "&H0066FF00&", "emph": "&H0000E5FF&", "upper": True, "words": 3, "chars": 18,
                "bord": 7, "pill": False},
    "caixa":   {"size": 80, "hl": "&H00FFFFFF&", "emph": "&H0000E5FF&", "upper": True, "words": 3, "chars": 18,
                "bord": 6, "pill": True},
    "minimal": {"size": 66, "hl": None, "emph": "&H0000E5FF&", "upper": False, "words": 5, "chars": 26,
                "bord": 4, "pill": False},
    # frases curtas, itálico amarelo, sem destaque palavra a palavra (padrão dos Shorts de referência)
    "frases":  {"size": 76, "hl": None, "emph": "&H00FFFFFF&", "upper": False, "words": 4, "chars": 22,
                "bord": 6, "pill": False, "color": "&H004AE5FF", "italic": True},
}


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(t: str) -> str:
    return t.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


ANNOT = re.compile(r"^[\(\[♪].*[\)\]♪]$|^[\(\[]|[\)\]]$")


def is_annotation(w: dict) -> bool:
    """(Risos), [Música], ♪ … -> não vira legenda, mas conta como 'som' para não ser cortado."""
    return bool(ANNOT.search(w["word"]))


def _norm(w: str) -> str:
    return w.lower().strip(".,!?;:\"'()…«»“”")


def build_ass(words: list[dict], hook: str | None, out: Path, duration: float, style: str = "amarelo",
              emphasis: list[str] | None = None, middle: bool = False, margin_v: int | None = None,
              hook_v: int | None = None, extra_styles: str = "", extra_events: list[str] | None = None) -> Path:
    st = STYLES.get(style, STYLES["amarelo"])
    emph = {_norm(e) for e in (emphasis or []) for e in e.split()}
    align, margin = (5, 0) if middle else (2, int(H * 0.29) if margin_v is None else margin_v)
    k = min(1.0, H / 1920) ** 0.6           # letras proporcionais em 1:1, 4:5 e 16:9
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{config.FONT},{int(st['size'] * k)},{st.get('color', '&H00FFFFFF')},&H00FFFFFF,&H00000000,&H96000000,-1,{-1 if st.get('italic') else 0},0,0,100,100,0,0,1,{max(3, int(st['bord'] * k))},3,{align},60,60,{margin},1
Style: Hook,{config.FONT},{int(70 * k)},&H00FFFFFF,&H00FFFFFF,&H001A1AC8,&H001A1AC8,-1,0,0,0,100,100,0,0,3,{int(18 * k)},0,8,80,80,{int(H * 0.12) if hook_v is None else hook_v},1
{extra_styles}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    if hook:
        ev.append(f"Dialogue: 1,{_ass_time(0)},{_ass_time(min(3.5, duration))},Hook,,0,0,0,,"
                  f"{{\\fad(150,250)}}{_esc(hook.upper())}")
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= st["words"] or sum(len(x["word"]) + 1 for x in cur) + len(w["word"]) > st["chars"]
                    or cur[-1]["word"].endswith((".", "?", "!"))):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)

    for ci, chunk in enumerate(chunks):
        chunk_end = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else chunk[-1]["end"] + 0.4
        if chunk_end - chunk[-1]["end"] > 1.0:   # pausa longa: some a legenda
            chunk_end = chunk[-1]["end"] + 0.3
        for wi, w in enumerate(chunk):
            start = w["start"]
            end = chunk[wi + 1]["start"] if wi + 1 < len(chunk) else chunk_end
            if end - start < 0.04 or start >= duration:
                continue
            parts = []
            for k, x in enumerate(chunk):
                txt = _esc(x["word"].upper() if st["upper"] else x["word"])
                is_emph = _norm(x["word"]) in emph
                if k == wi and st["hl"]:
                    if st["pill"]:
                        parts.append(f"{{\\3c&H001A1AC8&\\bord16\\shad0}}{txt}{{\\r}}")
                    else:
                        # só cor: aumentar a palavra ativa (\fscx) faria o libass recalcular a linha
                        # e empurrar as palavras vizinhas até 15 px a cada troca de destaque (tremor).
                        parts.append(f"{{\\c{st['hl']}}}{txt}{{\\r}}")
                elif is_emph:
                    parts.append(f"{{\\c{st['emph']}}}{txt}{{\\r}}")
                else:
                    parts.append(txt)
            pop = "{\\t(0,80,\\fscx104\\fscy104)\\t(80,160,\\fscx100\\fscy100)}" if wi == 0 else ""
            ev.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(min(end, duration))},Sub,,0,0,0,,{pop}{' '.join(parts)}")
            if not st["hl"]:  # estilo sem destaque: um evento por bloco
                ev[-1] = ev[-1].replace(_ass_time(min(end, duration)), _ass_time(min(chunk_end, duration)), 1)
                break
    ev += extra_events or []
    out.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")
    return out


# ------------------------------------------------------------------ jump cuts
def keep_intervals(words: list[dict], duration: float, max_gap: float = 0.5, pad: float = 0.12) -> list[tuple[float, float]]:
    """Trechos a manter, removendo silêncios > max_gap entre palavras (relativo ao clipe)."""
    if not words:
        return [(0.0, duration)]
    q = lambda t: round(t * FPS) / FPS  # alinha a quadros: evita dessincronia áudio/vídeo
    iv = [[max(0.0, words[0]["start"] - 0.15), None]]
    for a, b in zip(words, words[1:]):
        if b["start"] - a["end"] > max_gap:
            iv[-1][1] = a["end"] + pad
            iv.append([b["start"] - pad, None])
    iv[-1][1] = min(duration, words[-1]["end"] + 0.35)
    out = [(q(a), q(b)) for a, b in iv if q(b) - q(a) >= 2 / FPS]
    while len(out) > 400:  # vídeo longo: junta as pausas mais curtas (limite prático do filtro do ffmpeg)
        i = min(range(len(out) - 1), key=lambda k: out[k + 1][0] - out[k][1])
        out[i:i + 2] = [(out[i][0], out[i + 1][1])]
    return out or [(0.0, duration)]


def audio_active(video: Path, start: float, dur: float, hop: float = 0.05, min_sil: float = 0.6,
                 margin: float = 0.15) -> list[tuple[float, float]] | None:
    """Trechos com som (técnica do auto-editor): RMS a cada 50 ms; silêncio = abaixo de min(-35 dB, mediana-18 dB).
    Silêncios menores que `min_sil` ficam; cada trecho ganha `margin` de respiro. None se não deu para medir."""
    try:
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(video),
                              "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
        n = int(8000 * hop)
        if x.size < n * 4:
            return None
        frames = x[: x.size // n * n].reshape(-1, n)
        db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    except Exception:
        return None
    thr = min(-35.0, float(np.median(db)) - 18.0)
    active = db > thr
    out: list[list[float]] = []
    for i, on in enumerate(active):
        if on:
            a, b = i * hop, (i + 1) * hop
            if out and a - out[-1][1] < min_sil:
                out[-1][1] = b
            else:
                out.append([a, b])
    if not out:
        return None
    q = lambda t: round(t * FPS) / FPS
    return [(q(max(0.0, a - margin)), q(min(dur, b + margin))) for a, b in out]


def _intersect(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if hi - lo >= 2 / FPS:
            out.append((lo, hi))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    while len(out) > 400:  # mesmo limite prático do keep_intervals
        k = min(range(len(out) - 1), key=lambda k: out[k + 1][0] - out[k][1])
        out[k:k + 2] = [(out[k][0], out[k + 1][1])]
    return out


def remap(t: float, intervals: list[tuple[float, float]]) -> float:
    acc = 0.0
    for a, b in intervals:
        if t < a:
            return acc
        if t <= b:
            return acc + t - a
        acc += b - a
    return acc


def _between(intervals) -> str:
    return "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in intervals)


# ------------------------------------------------------------------ zoom de impacto
def zoom_expr(words: list[dict], duration: float, amount: float = 0.1) -> str | None:
    """Alterna zoom 100% / 110% a cada frase (estilo edição de podcast)."""
    sentences, cur_start = [], None
    for w in words:
        if cur_start is None:
            cur_start = w["start"]
        if w["word"].endswith((".", "?", "!")) or w is words[-1]:
            sentences.append((cur_start, w["end"]))
            cur_start = None
    zoomed = [(a, sentences[i + 1][0] if i + 1 < len(sentences) else duration)
              for i, (a, _) in enumerate(sentences) if i % 2 == 1]
    if not zoomed:
        # sem pontuação: alterna a cada ~4 s
        zoomed = [(t, min(t + 4, duration)) for t in range(4, int(duration), 8)]
    zoomed = zoomed[:40]
    return f"1+{amount}*({_between(zoomed)})" if zoomed else None


def zoom_cuts(keep: list[tuple[float, float]], amount: float = 0.1) -> str | None:
    """Zoom alternado em cada trecho mantido pelos jump cuts (técnica do OpenShorts)."""
    zoomed = [iv for i, iv in enumerate(keep) if i % 2 == 1][:40]
    return f"1+{amount}*({_between(zoomed)})" if zoomed else None


# ------------------------------------------------------------------ montagem do filtro
def _layout_filter(plan, cmdfile: str | None) -> str:
    """[0:v] -> [v] em 1080x1920."""
    base = "[0:v]setpts=PTS-STARTPTS,fps=30"
    sw, sh = plan.src_w, plan.src_h
    if plan.layout == "split":
        return (f"{base},sendcmd=f={cmdfile},split=2[s1][s2];"
                f"[s1]crop@a=w={plan.crop_w}:h={plan.crop_h}:x={plan.x0['a']}:y={plan.y0['a']},scale={W}:{H // 2},setsar=1[top];"
                f"[s2]crop@b=w={plan.crop_w}:h={plan.crop_h}:x={plan.x0['b']}:y={plan.y0['b']},scale={W}:{H // 2},setsar=1[bot];"
                f"[top][bot]vstack[v]")
    if plan.layout == "gamer":
        cx, cy, cw, ch = plan.extra["cam"]
        gx, gy, gw, gh = plan.extra["game"]
        th = plan.extra["top_h"]
        full = plan.extra.get("full") or []
        gamer = (f"[c]crop={cw}:{ch}:{cx}:{cy},scale={W}:{th},setsar=1[top];"
                 f"[g]crop={gw}:{gh}:{gx}:{gy},scale={W}:{H - th},setsar=1[bot];"
                 # a linha de 6 px sumia nos trechos escuros e os dois planos colavam
                 f"[top][bot]vstack,drawbox=x=0:y={th - 5}:w={W}:h=10:color=black@0.95:t=fill")
        react = plan.extra.get("react") or []
        rect = plan.extra.get("face_rect")
        sem = plan.extra.get("noface") or []
        nw = plan.extra.get("noface_w")
        outs = (["[c]", "[g]"] + (["[f]"] if full else []) + (["[r]"] if react and rect else [])
                + (["[n]"] if sem and nw else []))
        out_s, cur = f"{base},split={len(outs)}{''.join(outs)};{gamer}[gm]", "[gm]"
        if full:  # webcam em tela cheia em alguns trechos: nesses segundos mostra o rosto em tela cheia por cima
            fw = plan.extra["full_w"]
            on = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b, _ in full)
            xe = str(full[-1][2])
            for a, b, x in reversed(full[:-1]):
                xe = f"if(between(t,{a:.2f},{b:.2f}),{x},{xe})"
            out_s += (f";[f]crop={fw}:{sh}:x='{xe}':y=0,scale={W}:{H},setsar=1[full];"
                      f"{cur}[full]overlay=0:0:enable='{on}'[gm2]")
            cur = "[gm2]"
        if react and rect:  # 😱 reação: corta para a webcam em tela cheia por ~1,5 s
            rx, ry, rw, rh = rect
            on_r = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in react)
            out_s += (f";[r]crop={rw}:{rh}:{rx}:{ry},scale={W}:{H},setsar=1[rc];"
                      f"{cur}[rc]overlay=0:0:enable='{on_r}'[gm3]")
            cur = "[gm3]"
        if sem and nw:  # 🎮 sem rosto na webcam: o jogo ocupa a tela toda, sem faixa de cima vazia
            on_n = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in sem)
            out_s += (f";[n]crop={nw}:{sh}:{(sw - nw) // 2}:0,scale={W}:{H},setsar=1[jc];"
                      f"{cur}[jc]overlay=0:0:enable='{on_n}'[gm4]")
            cur = "[gm4]"
        return out_s + f";{cur}null[v]"
    if plan.layout == "track":
        sc = f"sendcmd=f={cmdfile}," if cmdfile else ""
        crop = f"crop@a=w={plan.crop_w}:h={plan.crop_h}:x={plan.x0['a']}:y=0"
        wide = plan.extra.get("wide") or []
        if wide:  # sem rosto por um tempo: nesses segundos mostra o quadro inteiro (fundo desfocado)
            on = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in wide)
            head, out_lbl = f"{base},split=2[trk][wid];[trk]", "[tv]"
            tail = (f";[wid]split=2[wa][wb];"
                    f"[wa]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:6,eq=brightness=-0.18:saturation=0.7[wbg];"
                    f"[wb]scale={W}:{H}:force_original_aspect_ratio=decrease,setsar=1[wfg];"
                    f"[wbg][wfg]overlay=(W-w)/2:(H-h)/2,setsar=1[wide];[tv][wide]overlay=0:0:enable='{on}'[v]")
        else:
            head, out_lbl, tail = f"{base},", "[v]", ""
        if plan.crop_w / plan.crop_h > W / H * 1.02:  # "câmera mais longe": corte mais aberto + fundo desfocado
            return (f"{head}{sc}split=2[a][b];"
                    f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:6,eq=brightness=-0.18:saturation=0.7[bg];"
                    f"[b]{crop},scale={W}:-2,setsar=1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1{out_lbl}{tail}")
        return f"{head}{sc}{crop},scale={W}:{H},setsar=1{out_lbl}{tail}"
    shift = int(H * 0.04) if H > W * 1.5 else 0
    return (f"{base},split=2[a][b];"
            f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:6,eq=brightness=-0.18:saturation=0.7[bg];"
            f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease,setsar=1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2-{shift},setsar=1[v]")


def _ass(name: str) -> str:
    return f"ass={name}" + (f":fontsdir={config.FONTS_DIR}" if config.FONTS_DIR else "")


def _encoder() -> list[str]:
    enc = config.ENCODER
    if enc == "libx264":
        return ["-c:v", "libx264", "-preset", config.X264_PRESET, "-crf", "21", "-pix_fmt", "yuv420p"]
    return ["-c:v", enc, "-b:v", "8M", "-pix_fmt", "yuv420p"]


def _run(cmd: list[str], cwd: Path) -> None:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg falhou:\n" + p.stderr[-1500:])


def render_clip(video: Path, start: float, end: float, words: list[dict], out: Path, *,
                hook: str | None = None, mode: str = "auto", grade: bool = True, jumpcut: bool = True,
                zoom: bool = True, style: str = "amarelo", emphasis: list[str] | None = None,
                progress: bool = True, music: Path | None = None, music_vol: float = 0.12,
                aspect: str = "9:16", distance: str = "padrao", captions: bool = True,
                loud: list[tuple[float, float]] | None = None, sfx: bool = False,
                template: dict | None = None, header_text: str | None = None, handle: str | None = None,
                bg_img: Path | None = None, teaser: tuple[float, float] | None = None,
                teaser_text: str | None = None, loop: bool = False, reactions: list[dict] | None = None,
                stickers: bool = True, react_zoom: bool = True) -> dict:
    """Renderiza um clipe. `start/end` são relativos ao arquivo `video`. Retorna info do render.

    aspect: 9:16 | 4:5 | 1:1 | original  ·  distance: padrao | longe (enquadramento mais aberto)
    captions: False = sem legenda (só gancho, se houver)."""
    from . import reframe
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = end - start
    sw, sh = probe_size(video)
    set_aspect(aspect, sw, sh)
    try:
        plan = reframe.plan(video, start, end, sw, sh, mode, distance)
    except Exception as e:  # reenquadramento nunca derruba o clipe
        print(f"[render] reenquadramento falhou ({e}); usando corte central/desfoque")
        plan = reframe.plan(video, start, end, sw, sh, "center" if mode in ("track", "split", "center") else "blur")
    cmdfile = None
    if plan.cmds:
        cmdfile = out.stem + ".cmd"
        (out.parent / cmdfile).write_text("\n".join(plan.cmds) + "\n")

    # anotações como (Risos) seguram ~1,5 s: a pausa da risada não é cortada
    sound = [dict(w, end=max(w["end"], w["start"] + 1.5)) if is_annotation(w) else w for w in words]
    # trechos de áudio alto sem fala (grito, explosão, risada, ação do jogo) também não são cortados
    sound += [{"start": a, "end": b, "word": "[som]"} for a, b in (loud or []) if b > a]
    sound.sort(key=lambda w: w["start"])
    keep = keep_intervals(sound, dur) if jumpcut else [(0.0, dur)]
    if jumpcut:  # confere com o áudio de verdade (auto-editor): silêncio real é cortado mesmo se a legenda "diz" que há fala
        ak = audio_active(video, start, dur)
        if ak:
            keep = _intersect(keep, ak) or keep
    words = [w for w in words if not is_annotation(w)]
    final_dur = sum(b - a for a, b in keep)
    new_words = [{"start": remap(w["start"], keep), "end": remap(w["end"], keep), "word": w["word"]} for w in words]
    new_words = [w for w in new_words if w["end"] > w["start"]]
    seam = H - plan.extra["top_h"] - int(H * 0.045) if plan.layout == "gamer" else None  # legenda na emenda cam/jogo
    hook_v = plan.extra["top_h"] + int(H * 0.10) if plan.layout == "gamer" else None
    from . import templates as _tpl
    geo, extra_styles, extra_events = None, "", []
    if template and template.get("card"):  # 🎨 modelo visual: vídeo vira cartão; legenda segue em tamanho cheio
        geo = _tpl.geometry(template, W, H)
        seam = _tpl.to_card(geo, H, seam if seam is not None else int(H * 0.29))
        hook_v = int(geo["y"] + (hook_v if hook_v is not None else int(H * 0.12)) * geo["scale"])
        extra_styles = _tpl.ass_styles(template, config.FONT, min(1.0, H / 1920) ** 0.6)
        extra_events = _tpl.ass_events(template, geo, W, final_dur, header_text, handle, _ass_time, _esc, H)
        if hook and header_text and template.get("header"):  # gancho igual ao título fixo: não repete
            hw = {w.strip(".,!?…").lower() for w in hook.split()}
            tw = {w.strip(".,!?…").lower() for w in header_text.split()}
            if hw and len(hw & tw) / len(hw) >= 0.6:
                hook = None
    ass = build_ass(new_words if captions else [], hook, out.with_suffix(".ass"), final_dur, style, emphasis,
                    middle=plan.layout == "split", margin_v=seam, hook_v=hook_v,
                    extra_styles=extra_styles, extra_events=extra_events)

    # 😂 reações (picos de som, risadas): figurinha + zoom no rosto / close da webcam
    reacts = [r for r in (reactions or []) if 0.5 <= r["t"] <= dur - 0.8]
    stick_items: list[tuple[float, Path]] = []
    if stickers and reacts:
        from . import reacoes
        for r in reacts:
            ft = remap(r["t"], keep)
            pth = reacoes.sticker_for(r["kind"], seed=round(start + r["t"], 2))
            if pth and 0.6 <= ft <= final_dur - 0.9:
                stick_items.append((round(ft, 2), pth))
    if react_zoom and reacts and plan.layout == "gamer":
        # A reação corta para um retângulo FIXO, calculado na posição média do rosto. Quando a webcam
        # já está em tela cheia, o rosto saiu daquele canto: o corte pegaria a parede ao lado dele.
        # Nesses segundos não há o que ampliar — a webcam já está grande.
        cheia = plan.extra.get("full") or []
        janelas = [(max(0.0, r["t"] - 0.15), r["t"] + 1.35) for r in reacts]
        janelas = [(a, b) for a, b in janelas if not any(a < fb and b > fa for fa, fb, _ in cheia)]
        if janelas:
            plan.extra["react"] = janelas
    vf = _layout_filter(plan, cmdfile)
    chain = []
    punch = ("+".join(f"0.2*between(t,{max(0.0, r['t'] - 0.1):.2f},{r['t'] + 1.4:.2f})" for r in reacts)
             if react_zoom and reacts and plan.layout in ("track", "blur") else "")
    if (zoom and plan.layout == "track") or punch:
        # com jump cuts: muda o zoom a cada corte (esconde o "pulo"); sem cortes: alterna por frase
        z = (zoom_cuts(keep) if len(keep) > 2 else zoom_expr(words, dur)) if zoom and plan.layout == "track" else None
        zz = "+".join(x for x in (f"({z})" if z else "1", punch) if x)
        yk = 0.3 if plan.layout == "track" else 0.42
        chain.append(f"scale=w='trunc({W}*({zz})/2)*2':h='trunc({H}*({zz})/2)*2':eval=frame,crop={W}:{H}:(iw-ow)/2:(ih-oh)*{yk}")
    if len(keep) > 1 or keep[0] != (0.0, dur):
        chain.append(f"select='{_between(keep)}',setpts=N/{FPS}/TB")
    if grade:
        chain.append(DARK_GRADE)
    use_img = bool(geo and bg_img and Path(bg_img).exists() and template.get("bg") == "imagem")
    if geo:
        comp, _ = _tpl.compose(template, W, H, FPS, final_dur, "[vb]", "[vc]", bg_input=1 if use_img else None)
        vf += f";[v]{','.join(chain) or 'null'}[vb];{comp};[vc]{_ass(ass.name)}[vs]"
    else:
        chain.append(f"{_ass(ass.name)}")
        vf += ";[v]" + ",".join(chain) + "[vs]"

    asel = f"aselect='{_between(keep)}',asetpts=N/SR/TB," if len(keep) > 1 or keep[0] != (0.0, dur) else ""
    af = f"[0:a]asetpts=PTS-STARTPTS,{asel}loudnorm=I=-14:TP=-1.5:LRA=11[voz]"
    cmd = ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(video.resolve())]
    n_in = 1
    if use_img:
        cmd += ["-loop", "1", "-t", f"{final_dur + 1:.3f}", "-i", str(Path(bg_img).resolve())]
        n_in += 1
    mix = ["[voz]"]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(Path(music).resolve())]
        af += f";[{n_in}:a]volume={music_vol}[m]"
        n_in += 1
        mix.append("[m]")
    if sfx:  # whoosh em cada corte + impacto no gancho (gerados por código)
        from . import sfx as _sfx
        cuts, acc = [], 0.0
        for a, b in keep[:-1]:
            acc += b - a
            cuts.append(acc)
        events = _sfx.events_for(cuts, bool(hook)) + [(ft, "pop") for ft, _ in stick_items]
        wav = _sfx.track(events, final_dur, out.with_suffix(".sfx.wav"))
        if wav:
            cmd += ["-i", str(wav.resolve())]
            af += f";[{n_in}:a]aresample=48000[fx]"
            n_in += 1
            mix.append("[fx]")
    af += (f";{''.join(mix)}amix=inputs={len(mix)}:duration=first:dropout_transition=0:normalize=0[ao]"
           if len(mix) > 1 else ";[voz]anull[ao]")
    # figurinhas: cada uma entra com "pop" (cresce rápido e assenta) embaixo da legenda e some suave
    cur = "[vs]"
    if stick_items:
        S = int(W * 0.24) // 2 * 2
        cap_m = seam if seam is not None else int(H * 0.29)
        yc = int(H * 0.5 + S * 0.9) if plan.layout == "split" else min(H - S // 2 - 40, H - cap_m + S // 2 + 12)
        for k, (ft, pth) in enumerate(stick_items):
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{final_dur:.3f}", "-i", str(Path(pth).resolve())]
            d = 1.3
            sc = (f"if(lt(t-{ft},0.12),max(0.1,(t-{ft})/0.12)*1.18,"
                  f"if(lt(t-{ft},0.24),1.18-(t-{ft}-0.12)*1.5,1))")
            vf += (f";[{n_in}:v]format=rgba,scale=w='2*trunc({S}*({sc})/2)':h=-1:eval=frame,"
                   f"fade=t=out:st={ft + d - 0.2:.2f}:d=0.2:alpha=1[stk{k}];"
                   f"{cur}[stk{k}]overlay=x='(W-w)/2':y='{yc}-h/2':eval=frame:"
                   f"enable='between(t,{ft},{ft + d:.2f})'[sv{k}]")
            cur = f"[sv{k}]"
            n_in += 1
    if progress:
        # 10 px de amarelo puro no rodapé passava por defeito gráfico em cima do HUD do jogo:
        # mais grossa (14 px) para ler como barra, e com transparência para não brigar com a cena.
        vf += (f";color=c=0xE5FF00@0.75:s={W}x14:r={FPS}:d={final_dur:.3f},format=yuva420p[pb];"
               f"{cur}[pb]overlay=x='-w+w*t/{final_dur:.3f}':y=H-h:eof_action=pass[vo]")
    else:
        vf += f";{cur}null[vo]"
    cmd += ["-filter_complex", f"{vf};{af}", "-map", "[vo]", "-map", "[ao]", "-t", f"{final_dur:.3f}",
            *_encoder(), "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
            "-movflags", "+faststart", out.name]
    _run(cmd, out.parent)
    extra = {}
    removed = round(dur - final_dur, 1)   # silêncio cortado (antes de somar a prévia)
    if teaser:  # ⏩ prévia: o melhor momento abre o vídeo e depois volta ao começo
        t0, t1 = remap(teaser[0], keep), remap(teaser[1], keep)
        if t1 - t0 >= 1.0:
            label_y = int(geo["y"] + geo["ch"] * 0.07) if geo else int(H * 0.13)  # no alto: não cobre o rosto
            _add_teaser(out, t0, t1, teaser_text, zoom=geo is None, label_y=label_y)  # com modelo: sem zoom
            final_dur += t1 - t0
            extra["teaser"] = [round(t0, 2), round(t1, 2)]
    if loop:  # 🔁 o fim se dissolve no primeiro quadro: o replay não tem emenda
        _make_loop(out, final_dur)
        extra["loop"] = True
    thumbnail(out)
    return {**extra, "layout": plan.layout, "faces": round(plan.faces_ratio, 2), "shots": plan.shots,
            "template": (template or {}).get("nome"), "reacoes": len(reacts), "figurinhas": len(stick_items),
            "cuts": len(keep) - 1, "duration": round(final_dur, 1), "removed": removed}


def _add_teaser(out: Path, t0: float, t1: float, text: str | None, zoom: bool = True,
                label_y: int | None = None) -> None:
    """Coloca na frente do vídeo os segundos [t0, t1] (já com legenda), com texto, flash branco e whoosh."""
    from . import sfx as _sfx
    td = t1 - t0
    k = min(1.0, H / 1920) ** 0.6
    ass = out.with_name(out.stem + "_tz.ass")
    lines = [f"Dialogue: 3,{_ass_time(0)},{_ass_time(td)},Tz,,0,0,0,,{{\\an5\\pos({W // 2},{label_y or int(H * 0.13)})"
             f"\\fad(120,150)}}{_esc(text.upper())}"] if text else []
    ass.write_text(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\n"
                   f"ScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
                   f"SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                   f"Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                   f"Style: Tz,{config.FONT},{int(70 * k)},&H00FFFFFF,&H00FFFFFF,&H001A1AC8,&H001A1AC8,-1,0,0,0,"
                   f"100,100,0,0,3,{int(18 * k)},0,5,80,80,0,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, "
                   f"MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(lines) + "\n", encoding="utf-8")
    wav = _sfx.track([(max(0.05, td - 0.12), "whoosh")], td, out.with_name(out.stem + "_tz.wav"), volume=0.5)
    tmp = out.with_name(out.stem + "_tz.mp4")
    st = "aformat=sample_rates=48000:channel_layouts=stereo"
    fc = (f"[0:v]split=2[m][t];"
          f"[t]trim={t0:.3f}:{t1:.3f},setpts=PTS-STARTPTS,"
          + (f"scale=trunc(iw*1.06/2)*2:-2,crop={W}:{H}," if zoom else "") +
          f"drawbox=y=ih-10:w=iw:h=10:color=black:t=fill,{_ass(ass.name)},"
          f"fade=t=out:st={max(0.0, td - 0.2):.3f}:d=0.2:color=white,setsar=1[tv];"
          f"[m]fade=t=in:st=0:d=0.18:color=white,setsar=1[mv];"
          f"[0:a]asplit=2[ma][ta];[ta]atrim={t0:.3f}:{t1:.3f},asetpts=PTS-STARTPTS,"
          f"afade=t=out:st={max(0.0, td - 0.25):.3f}:d=0.25,{st}[ta1];")
    cmd = ["ffmpeg", "-y", "-i", out.name]
    if wav:
        cmd += ["-i", wav.name]
        fc += f"[1:a]aresample=48000,{st}[fx];[ta1][fx]amix=inputs=2:duration=first:normalize=0,{st}[ta2];"
    else:
        fc += "[ta1]anull[ta2];"
    fc += f"[ma]{st}[ma2];[tv][ta2][mv][ma2]concat=n=2:v=1:a=1[v][a]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", *_encoder(), "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", tmp.name]
    _run(cmd, out.parent)
    tmp.replace(out)
    for f in (ass, out.with_name(out.stem + "_tz.wav")):
        f.unlink(missing_ok=True)


def _make_loop(out: Path, dur: float, fade: float = 0.45) -> None:
    """Loop sem emenda: o fim se dissolve no 1º quadro (congelado). Quando a rede recomeça o vídeo,
    o último quadro é igual ao primeiro; o som termina em fade."""
    if dur < 4:
        return
    tmp = out.with_name(out.stem + "_lp.mp4")
    n = max(2, int(fade * FPS))
    fc = (f"[0:v]split=2[m][h];[h]trim=end_frame=1,setpts=PTS-STARTPTS,loop=loop={n}:size=1,"
          f"setpts=N/{FPS}/TB[hv];[m][hv]xfade=transition=fade:duration={fade:.3f}:offset={dur - fade:.3f}[v];"
          f"[0:a]afade=t=out:st={dur - fade:.3f}:d={fade:.3f}[a]")
    _run(["ffmpeg", "-y", "-i", out.name, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
          *_encoder(), "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", tmp.name], out.parent)
    tmp.replace(out)


def render_story(audio: Path, words: list[dict], out: Path, hook: str | None,
                 background: Path | None = None, music: Path | None = None, music_vol: float = 0.10,
                 style: str = "amarelo", emphasis: list[str] | None = None) -> Path:
    """Short dark narrado: fundo (vídeo em loop ou grão escuro animado) + narração + legenda."""
    from .download import probe_duration
    set_aspect("9:16")
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = probe_duration(audio) + 0.6
    ass = build_ass(words, hook, out.with_suffix(".ass"), dur, style, emphasis)
    if background:
        inp = ["-stream_loop", "-1", "-i", str(Path(background).resolve())]
        sw, sh = probe_size(Path(background))
        crop_w = int(sh * W / H) // 2 * 2
        if sh >= sw:
            vf = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
        else:
            vf = f"[0:v]crop={crop_w}:{sh},scale={W}:{H},setsar=1"
        vf += ",eq=brightness=-0.12:saturation=0.6,gblur=sigma=1.2[v]"
    else:  # fundo procedural: preto com grão de filme e vinheta
        inp = ["-f", "lavfi", "-i", f"color=c=0x0b0b10:s={W}x{H}:r={FPS}"]
        vf = "[0:v]noise=alls=14:allf=t,vignette=angle=PI/3.5,setsar=1[v]"
    cmd = ["ffmpeg", "-y", *inp, "-i", str(audio.resolve())]
    afilter = "[1:a]loudnorm=I=-14:TP=-1.5[ao]"
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(Path(music).resolve())]
        afilter = f"[1:a]loudnorm=I=-14:TP=-1.5[voz];[2:a]volume={music_vol}[m];[voz][m]amix=inputs=2:duration=first[ao]"
    cmd += ["-filter_complex",
            f"{vf};[v]{DARK_GRADE},fps={FPS},{_ass(ass.name)}[vs];"
            f"color=c=0xE5FF00:s={W}x10:r={FPS}:d={dur:.2f}[pb];[vs][pb]overlay=x='-w+w*t/{dur:.2f}':y=H-h:eof_action=pass[vo];"
            f"{afilter}",
            "-map", "[vo]", "-map", "[ao]", "-t", f"{dur:.2f}", *_encoder(),
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", out.name]
    _run(cmd, out.parent)
    thumbnail(out)
    return out


def thumbnail(video: Path, at: float = 1.0) -> Path:
    jpg = video.with_suffix(".jpg")
    subprocess.run(["ffmpeg", "-y", "-ss", str(at), "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2",
                    "-q:v", "4", str(jpg)], capture_output=True)
    return jpg
