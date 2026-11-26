"""✂️ Mesa de edição do DarkClip: efeitos de edição de Shorts/Reels com ffmpeg, um por vez.

Cada comando lê um vídeo e grava OUTRO arquivo (o original nunca é alterado).
Rode da raiz do projeto DarkClip:

  python .claude/skills/editar-video/scripts/editar.py info     clip.mp4
  python .claude/skills/editar-video/scripts/editar.py quadros  clip.mp4 --n 12
  python .claude/skills/editar-video/scripts/editar.py zoom     clip.mp4 --em 4.2 --dur 1.2 --som
  python .claude/skills/editar-video/scripts/editar.py tremor   clip.mp4 --em 7 --dur 0.6 --som
  python .claude/skills/editar-video/scripts/editar.py lento    clip.mp4 --em 10 --dur 1.5 --fator 0.5
  python .claude/skills/editar-video/scripts/editar.py congelar clip.mp4 --em 12.3 --dur 1 --texto "ELE NÃO VIU 💀"
  python .claude/skills/editar-video/scripts/editar.py texto    clip.mp4 --em 2 --dur 2 --texto "KKKKK" --pos meio
  python .claude/skills/editar-video/scripts/editar.py som      clip.mp4 --em 3.1 --tipo hit
  python .claude/skills/editar-video/scripts/editar.py aparar   clip.mp4 --de 1.5 --ate 48

Saída padrão: <nome>_<comando>.mp4 ao lado do original (ou -o caminho.mp4).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]          # raiz do DarkClip (…/.claude/skills/editar-video/scripts)
if (ROOT / "darkclip").is_dir():
    sys.path.insert(0, str(ROOT))

VENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
AENC = ["-c:a", "aac", "-b:a", "192k"]


# ------------------------------------------------------------------ utilidades
def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        sys.exit("❌ ffmpeg falhou:\n" + p.stderr[-1200:])
    return p.stderr


def probe(video: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"❌ Não consegui ler o vídeo: {video}")
    d = json.loads(out.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    if not v:
        sys.exit("❌ O arquivo não tem vídeo.")
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": float(num) / float(den or 1),
            "dur": float(d["format"].get("duration") or v.get("duration") or 0), "audio": a is not None}


def out_path(args, suffix: str) -> Path:
    if args.o:
        return Path(args.o)
    src = Path(args.video)
    return src.with_name(f"{src.stem}_{suffix}.mp4")


def check_window(info: dict, t: float, d: float) -> None:
    if t < 0 or t >= info["dur"]:
        sys.exit(f"❌ --em {t} está fora do vídeo (duração {info['dur']:.2f} s).")
    if d <= 0:
        sys.exit("❌ --dur precisa ser maior que zero.")


def sfx_wav(kind: str, at: float, total: float, volume: float) -> Path | None:
    try:
        from darkclip import sfx
    except Exception:
        print("⚠️  Módulo de efeitos sonoros do DarkClip não encontrado: seguindo sem som.")
        return None
    dest = Path(tempfile.mkdtemp(prefix="dc_sfx_")) / "sfx.wav"
    return sfx.track([(at, kind)], total, dest, volume=volume)


def mux_sfx(video: Path, wav: Path | None, out: Path, has_audio: bool) -> None:
    """Mistura o efeito sonoro no áudio do vídeo (sem abaixar o áudio original)."""
    if wav is None:
        return
    tmp = out.with_name(out.stem + "_tmp.mp4")
    out.replace(tmp)
    if has_audio:
        fc = "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]"
    else:
        fc = "[1:a]apad[a]"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-i", str(wav), "-filter_complex", fc,
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", *AENC, "-shortest", str(out)])
    tmp.unlink(missing_ok=True)


def ass_file(text: str, start: float, dur: float, w: int, h: int, pos: str, color: str) -> Path:
    try:
        from darkclip import config
        font = config.FONT
    except Exception:
        font = "Arial"
    colors = {"branco": "&H00FFFFFF", "amarelo": "&H0000F0FF", "vermelho": "&H003030FF", "verde": "&H0050FF50"}
    align, mv = {"topo": (8, int(h * 0.12)), "meio": (5, 0), "baixo": (2, int(h * 0.22))}.get(pos, (5, 0))
    size = int(min(w, h) * 0.11)

    def ts(t: float) -> str:
        cs = int(round(t * 100))
        return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"

    safe = text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N").upper()
    body = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,{font},{size},{colors.get(color, colors['branco'])},&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,{max(4, size // 9)},4,{align},60,60,{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 2,{ts(start)},{ts(start + dur)},T,,0,0,0,,{{\\fad(80,120)\\t(0,120,\\fscx118\\fscy118)\\t(120,240,\\fscx100\\fscy100)}}{safe}
"""
    p = Path(tempfile.mkdtemp(prefix="dc_txt_")) / "t.ass"
    p.write_text(body, encoding="utf-8")
    return p


def ass_filter(p: Path) -> str:
    """Caminho do .ass escapado para o filtro (Windows: C\\:/pasta/t.ass)."""
    s = p.resolve().as_posix().replace(":", "\\:").replace("'", "\\'")
    extra = ""
    try:
        from darkclip import config
        if config.FONTS_DIR:
            extra = ":fontsdir='" + Path(config.FONTS_DIR).as_posix().replace(":", "\\:") + "'"
    except Exception:
        pass
    return f"ass='{s}'{extra}"


# ------------------------------------------------------------------ comandos
def cmd_info(args) -> None:
    v = Path(args.video)
    i = probe(v)
    print(f"🎬 {v.name}: {i['w']}x{i['h']} · {i['fps']:.0f} fps · {i['dur']:.2f} s · áudio: {'sim' if i['audio'] else 'NÃO'}")
    tips = []
    if i["audio"]:
        err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(v), "-af", "ebur128=framelog=quiet", "-f", "null", "-"])
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
        if m:
            lufs = float(m[-1])
            print(f"🔊 Volume médio: {lufs:.1f} LUFS (ideal para Shorts/Reels: perto de -14)")
            if lufs < -18:
                tips.append("áudio baixo: renderize de novo pelo DarkClip (ele normaliza para -14 LUFS)")
            elif lufs > -10:
                tips.append("áudio alto demais: pode distorcer no celular")
        err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(v), "-af", "silencedetect=n=-40dB:d=0.7",
                   "-f", "null", "-"])
        sil = [(float(a), float(b)) for a, b in re.findall(r"silence_start: ([\d.]+)[\s\S]*?silence_end: ([\d.]+)", err)]
        if sil:
            print("🤫 Silêncios ≥0,7 s: " + ", ".join(f"{a:.1f}–{b:.1f}s" for a, b in sil[:10]))
            if sil[0][0] < 0.3:
                tips.append(f"começa em silêncio ({sil[0][1]:.1f} s): o gancho precisa estar no 1º segundo")
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(v), "-vf", "blackdetect=d=0.3:pix_th=0.10",
               "-an", "-f", "null", "-"])
    blk = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)
    if blk:
        print("⬛ Tela preta: " + ", ".join(f"{float(a):.1f}–{float(b):.1f}s" for a, b in blk))
        tips.append("tem trecho de tela preta: corte fora")
    if i["h"] <= i["w"]:
        tips.append("o vídeo não está em pé (9:16): use o DarkClip com proporção 9:16")
    if i["dur"] > 180:
        tips.append("mais de 3 min: não entra como Short no YouTube")
    elif i["dur"] > 90:
        tips.append("mais de 90 s: Reels do Facebook/Instagram aceitam até 90 s com alcance total")
    print("✅ Nada a corrigir." if not tips else "👉 " + "\n👉 ".join(tips))


def cmd_quadros(args) -> None:
    v = Path(args.video)
    i = probe(v)
    a = args.de or 0.0
    b = min(args.ate or i["dur"], i["dur"])
    n = max(2, args.n)
    step = (b - a) / n
    times = [a + step * (k + 0.5) for k in range(n)]
    cols = 4 if n > 6 else n
    rows = -(-n // cols)
    outdir = Path(tempfile.mkdtemp(prefix="dc_q_"))
    for k, t in enumerate(times):
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(v), "-frames:v", "1",
             "-vf", "scale=270:-2", str(outdir / f"q{k:03d}.png")])
    grid = Path(args.o) if args.o else v.with_name(f"{v.stem}_quadros.png")
    run(["ffmpeg", "-y", "-v", "error", "-framerate", "1", "-i", str(outdir / "q%03d.png"),
         "-vf", f"tile={cols}x{rows}:padding=6:color=black", "-frames:v", "1", str(grid)])
    print(f"🖼️  Grade salva em: {grid}")
    print("Ordem (esquerda→direita, de cima para baixo): " + " · ".join(f"{k + 1}={t:.1f}s" for k, t in enumerate(times)))


def cmd_zoom(args) -> None:
    v = Path(args.video)
    i = probe(v)
    check_window(i, args.em, args.dur)
    t0, t1, z = args.em, args.em + args.dur, args.forca
    ramp = 0.08  # entra rápido (punch-in), sai suave
    zexpr = (f"if(between(t,{t0},{t1}),1+({z}-1)*min(1,(t-{t0})/{ramp}),"
             f"if(between(t,{t1},{t1 + 0.25}),1+({z}-1)*(1-(t-{t1})/0.25),1))")
    w, h = i["w"], i["h"]
    vf = (f"scale=w='trunc({w}*({zexpr})/2)*2':h='trunc({h}*({zexpr})/2)*2':eval=frame,"
          f"crop={w}:{h}:(iw-ow)/2:(ih-oh)*{args.foco},setsar=1")
    out = out_path(args, "zoom")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-vf", vf, *VENC, "-c:a", "copy", str(out)])
    if args.som:
        mux_sfx(out, sfx_wav("whoosh", t0, i["dur"], 0.45), out, i["audio"])
    print(f"✅ Zoom de {z:.2f}x em {t0:.2f}–{t1:.2f}s → {out}")


def cmd_tremor(args) -> None:
    v = Path(args.video)
    i = probe(v)
    check_window(i, args.em, args.dur)
    t0, t1, a = args.em, args.em + args.dur, args.forca
    w, h = i["w"], i["h"]
    pad = 1 + 2.4 * a / min(w, h)
    on = f"between(t,{t0},{t1})*(1-(t-{t0})/{args.dur})"  # tremor que vai diminuindo
    vf = (f"scale=trunc({w}*{pad:.4f}/2)*2:trunc({h}*{pad:.4f}/2)*2,"
          f"crop={w}:{h}:x='(iw-ow)/2+{a}*{on}*sin(t*71)':y='(ih-oh)/2+{a}*{on}*cos(t*53)',setsar=1")
    out = out_path(args, "tremor")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-vf", vf, *VENC, "-c:a", "copy", str(out)])
    if args.som:
        mux_sfx(out, sfx_wav("hit", t0, i["dur"], 0.55), out, i["audio"])
    print(f"✅ Tremor em {t0:.2f}–{t1:.2f}s → {out}")


def _segments_filter(i: dict, t0: float, t1: float, mid_v: str, mid_a: str) -> str:
    """Divide em antes | meio | depois, aplica o efeito no meio e junta de novo."""
    fc = (f"[0:v]trim=0:{t0},setpts=PTS-STARTPTS[v0];"
          f"[0:v]trim={t0}:{t1},setpts=PTS-STARTPTS,{mid_v}[v1];"
          f"[0:v]trim={t1},setpts=PTS-STARTPTS[v2];")
    if i["audio"]:
        fc += (f"[0:a]atrim=0:{t0},asetpts=PTS-STARTPTS[a0];"
               f"[0:a]atrim={t0}:{t1},asetpts=PTS-STARTPTS,{mid_a}[a1];"
               f"[0:a]atrim={t1},asetpts=PTS-STARTPTS[a2];"
               f"[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]")
    else:
        fc += "[v0][v1][v2]concat=n=3:v=1:a=0[v]"
    return fc


def _atempo(f: float) -> str:
    parts = []
    while f < 0.5:
        parts.append("atempo=0.5")
        f /= 0.5
    while f > 2.0:
        parts.append("atempo=2.0")
        f /= 2.0
    parts.append(f"atempo={f:.4f}")
    return ",".join(parts)


def cmd_lento(args) -> None:
    v = Path(args.video)
    i = probe(v)
    check_window(i, args.em, args.dur)
    t0, t1 = args.em, min(args.em + args.dur, i["dur"] - 0.05)
    f = args.fator
    if not 0.1 <= f <= 4:
        sys.exit("❌ --fator entre 0.1 (bem lento) e 4 (bem rápido). 0.5 = câmera lenta, 2 = acelerado.")
    mid_v = f"setpts=PTS/{f},fps={round(i['fps'])}" + (",minterpolate=fps=%d:mi_mode=blend" % round(i["fps"]) if f < 0.75 and args.suave else "")
    mid_a = _atempo(f)
    fc = _segments_filter(i, t0, t1, mid_v, mid_a)
    out = out_path(args, "lento" if f < 1 else "rapido")
    maps = ["-map", "[v]"] + (["-map", "[a]"] if i["audio"] else [])
    run(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-filter_complex", fc, *maps, *VENC, *AENC, str(out)])
    new = i["dur"] + (t1 - t0) * (1 / f - 1)
    print(f"✅ Velocidade {f}x em {t0:.2f}–{t1:.2f}s → {out} (duração nova ≈ {new:.1f}s)")


def cmd_congelar(args) -> None:
    v = Path(args.video)
    i = probe(v)
    check_window(i, args.em, args.dur)
    t0, d = args.em, args.dur
    fps = round(i["fps"])
    # quadro parado (com um leve zoom) + silêncio; o resto continua normal depois
    mid = (f"[0:v]trim={t0}:{t0 + 1 / fps},setpts=PTS-STARTPTS,loop=loop={int(d * fps)}:size=1:start=0,"
           f"setpts=N/{fps}/TB,scale=trunc(iw*1.06/2)*2:-2,crop={i['w']}:{i['h']},setsar=1[vf];")
    fc = (f"[0:v]trim=0:{t0},setpts=PTS-STARTPTS,setsar=1[v0];{mid}"
          f"[0:v]trim={t0},setpts=PTS-STARTPTS,setsar=1[v2];")
    if i["audio"]:
        fc += (f"[0:a]atrim=0:{t0},asetpts=PTS-STARTPTS[a0];"
               f"anullsrc=r=48000:cl=stereo,atrim=0:{d}[af];"
               f"[0:a]atrim={t0},asetpts=PTS-STARTPTS[a2];"
               f"[a0]aresample=48000,aformat=channel_layouts=stereo[a0b];"
               f"[a2]aresample=48000,aformat=channel_layouts=stereo[a2b];"
               f"[v0][a0b][vf][af][v2][a2b]concat=n=3:v=1:a=1[v][a]")
    else:
        fc += "[v0][vf][v2]concat=n=3:v=1:a=0[v]"
    out = out_path(args, "congelado")
    if args.texto:  # texto por cima do quadro congelado
        fc = fc.replace("[v][a]", "[vc][a]") if i["audio"] else fc.replace("concat=n=3:v=1:a=0[v]", "concat=n=3:v=1:a=0[vc]")
        fc += f";[vc]{ass_filter(ass_file(args.texto, t0, d, i['w'], i['h'], args.pos, args.cor))}[v]"
    maps = ["-map", "[v]"] + (["-map", "[a]"] if i["audio"] else [])
    run(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-filter_complex", fc, *maps, *VENC, *AENC, str(out)])
    if args.som:
        mux_sfx(out, sfx_wav("hit", t0, i["dur"] + d, 0.55), out, True)
    print(f"✅ Quadro congelado em {t0:.2f}s por {d:.1f}s → {out}")


def cmd_texto(args) -> None:
    v = Path(args.video)
    i = probe(v)
    check_window(i, args.em, args.dur)
    ass = ass_file(args.texto, args.em, args.dur, i["w"], i["h"], args.pos, args.cor)
    out = out_path(args, "texto")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-vf", ass_filter(ass), *VENC, "-c:a", "copy", str(out)])
    if args.som:
        mux_sfx(out, sfx_wav("hit", args.em, i["dur"], 0.45), out, i["audio"])
    print(f"✅ Texto \"{args.texto}\" em {args.em:.2f}–{args.em + args.dur:.2f}s → {out}")


def cmd_som(args) -> None:
    v = Path(args.video)
    i = probe(v)
    check_window(i, args.em, 1)
    out = out_path(args, "som")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-c", "copy", str(out)])
    wav = sfx_wav(args.tipo, args.em, i["dur"], args.volume)
    if wav is None:
        sys.exit("❌ Não consegui gerar o efeito sonoro.")
    mux_sfx(out, wav, out, i["audio"])
    print(f"✅ Som \"{args.tipo}\" em {args.em:.2f}s → {out}")


def cmd_aparar(args) -> None:
    v = Path(args.video)
    i = probe(v)
    a, b = max(0.0, args.de or 0.0), min(args.ate or i["dur"], i["dur"])
    if b - a < 1:
        sys.exit("❌ O trecho ficou com menos de 1 s.")
    out = out_path(args, "aparado")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(v), "-ss", f"{a:.3f}", "-to", f"{b:.3f}", *VENC, *AENC, str(out)])
    print(f"✅ Aparado {a:.2f}–{b:.2f}s ({b - a:.1f}s) → {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Mesa de edição do DarkClip (efeitos de Shorts com ffmpeg)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, timed=True, **extra):
        p = sub.add_parser(name)
        p.add_argument("video")
        p.add_argument("-o", help="arquivo de saída (padrão: <nome>_<comando>.mp4)")
        if timed:
            p.add_argument("--em", type=float, required=True, help="segundo onde o efeito começa")
            p.add_argument("--dur", type=float, default=extra.pop("dur", 1.0), help="duração do efeito (s)")
        for flag, kw in extra.items():
            p.add_argument("--" + flag, **kw)
        p.set_defaults(fn=fn)
        return p

    snd = {"action": "store_true", "help": "adiciona efeito sonoro junto"}
    txt = {"pos": {"default": "meio", "choices": ["topo", "meio", "baixo"]},
           "cor": {"default": "amarelo", "choices": ["branco", "amarelo", "vermelho", "verde"]}}
    add("info", cmd_info, timed=False)
    add("quadros", cmd_quadros, timed=False, n={"type": int, "default": 12},
        de={"type": float, "default": None}, ate={"type": float, "default": None})
    add("zoom", cmd_zoom, dur=1.2, forca={"type": float, "default": 1.25, "help": "1.15 sutil · 1.25 normal · 1.5 exagerado"},
        foco={"type": float, "default": 0.35, "help": "altura do foco: 0 topo · 0.5 meio · 1 base"}, som=snd)
    add("tremor", cmd_tremor, dur=0.6, forca={"type": float, "default": 18, "help": "pixels de tremor (10 a 40)"}, som=snd)
    add("lento", cmd_lento, dur=1.5, fator={"type": float, "default": 0.5, "help": "0.5 = câmera lenta · 2 = acelerado"},
        suave={"action": "store_true", "help": "mistura quadros na câmera lenta (mais suave, mais demorado)"})
    add("congelar", cmd_congelar, dur=1.0, texto={"default": ""}, som=snd, **txt)
    add("texto", cmd_texto, dur=1.5, texto={"required": True}, som=snd, **txt)
    add("som", cmd_som, tipo={"default": "hit", "choices": ["hit", "whoosh"]},
        volume={"type": float, "default": 0.5})
    add("aparar", cmd_aparar, timed=False, de={"type": float, "default": None}, ate={"type": float, "default": None})
    args = ap.parse_args()
    if not Path(args.video).exists():
        sys.exit(f"❌ Arquivo não encontrado: {args.video}")
    args.fn(args)


if __name__ == "__main__":
    main()
