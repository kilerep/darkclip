"""🎨 Modelos visuais: o mesmo corte com cara diferente em cada rede.

Cada modelo coloca o vídeo editado num "cartão" sobre um fundo (desfoque do próprio vídeo, cor, degradê
animado ou uma imagem sua), com título fixo em cima e o @ do canal embaixo. A legenda continua em tamanho
cheio por cima de tudo. Tudo é feito pelo ffmpeg: nenhum programa extra.

A escolha de modelo por rede fica na Central do Canal (settings["templates"]).
"""
from __future__ import annotations

from pathlib import Path

TEMPLATES: dict[str, dict] = {
    "tela_cheia": {"nome": "🎬 Tela cheia", "desc": "O corte normal, ocupando a tela toda.", "card": None},
    "manchete": {"nome": "📰 Manchete", "desc": "Título fixo em cima, vídeo em cartão, @ do canal embaixo e fundo desfocado do próprio vídeo.",
                 "card": 0.80, "bg": "desfoque", "radius": 36, "header": True, "footer": True,
                 "accent": "0xE5FF00", "style": "amarelo"},
    "cartao": {"nome": "🃏 Cartão degradê", "desc": "Fundo degradê animado roxo e rosa, borda branca e legenda em caixa.",
               "card": 0.82, "bg": "gradiente", "colors": ("0x1A0B2E", "0xFF3D71"), "radius": 48,
               "border": "0xFFFFFF", "border_w": 8, "header": True, "footer": True, "accent": "0xFFFFFF", "style": "caixa"},
    "neon": {"nome": "⚡ Neon gamer", "desc": "Fundo escuro com degradê ciano, borda neon e legenda verde.",
             "card": 0.82, "bg": "gradiente", "colors": ("0x050014", "0x00B8D4"), "radius": 28,
             "border": "0x00FFD0", "border_w": 10, "header": True, "footer": True, "accent": "0x00FFD0", "style": "verde"},
    "minimal": {"nome": "⬛ Minimal", "desc": "Fundo preto, vídeo grande, só o @ embaixo e legenda discreta.",
                "card": 0.90, "bg": "cor", "color": "0x000000", "radius": 0, "header": False, "footer": True,
                "accent": "0xBBBBBB", "style": "minimal"},
    "meu_fundo": {"nome": "🖼️ Meu fundo", "desc": "Sua imagem de fundo (enviada na aba Canal), com título e @.",
                  "card": 0.80, "bg": "imagem", "radius": 40, "border": "0xFFFFFF", "border_w": 6,
                  "header": True, "footer": True, "accent": "0xE5FF00", "style": "amarelo"},
}

# Sugestão inicial: cada rede com uma cara diferente
DEFAULT_BY_PLATFORM = {"tiktok": "tela_cheia", "youtube": "tela_cheia", "instagram": "cartao",
                       "facebook": "manchete", "kwai": "neon"}
PLATFORMS = list(DEFAULT_BY_PLATFORM)


def get(name: str | None) -> dict | None:
    t = TEMPLATES.get(name or "")
    return t if t and t.get("card") else None


def catalog() -> list[dict]:
    return [{"id": k, "nome": v["nome"], "desc": v["desc"]} for k, v in TEMPLATES.items()]


def geometry(tpl: dict, W: int, H: int) -> dict:
    """Onde fica o cartão, o título e o @ na tela."""
    s = float(tpl["card"])
    cw, ch = int(W * s) // 2 * 2, int(H * s) // 2 * 2
    free = H - ch
    if tpl.get("header") and tpl.get("footer"):
        y = int(free * 0.62)
    elif tpl.get("header"):
        y = int(free * 0.75)
    elif tpl.get("footer"):
        y = int(free * 0.35)
    else:
        y = free // 2
    y = y // 2 * 2
    return {"x": (W - cw) // 2 // 2 * 2, "y": y, "cw": cw, "ch": ch, "scale": ch / H,
            "head_cy": y // 2, "foot_cy": y + ch + (H - y - ch) // 2}


def to_card(geo: dict, H: int, margin_from_bottom: int) -> int:
    """Converte uma margem medida na tela cheia para a posição equivalente dentro do cartão."""
    y = H - margin_from_bottom
    return int(H - (geo["y"] + y * geo["scale"]))


def _rounded_alpha(w: int, h: int, r: int, fps: int, dur: float, label: str) -> str:
    """Máscara de cantos arredondados calculada só no 1º quadro e repetida (rápido)."""
    r = max(1, min(r, w // 2, h // 2))
    expr = (f"255*lte(hypot(max(0\\,abs(X-{w / 2:.1f})-{w / 2 - r:.1f})\\,"
            f"max(0\\,abs(Y-{h / 2:.1f})-{h / 2 - r:.1f}))\\,{r})")
    return (f"color=c=black:s={w}x{h}:r={fps}:d={1 / fps:.4f},format=gray,geq=lum='{expr}',"
            f"loop=loop=-1:size=1,trim=duration={dur:.3f},setpts=N/{fps}/TB{label}")


def compose(tpl: dict, W: int, H: int, fps: int, dur: float, src: str, out: str,
            bg_input: int | None = None) -> tuple[str, dict]:
    """Filtro ffmpeg: [src] (vídeo editado, W×H) -> [out] (cartão sobre o fundo, W×H)."""
    geo = geometry(tpl, W, H)
    x, y, cw, ch = geo["x"], geo["y"], geo["cw"], geo["ch"]
    parts, fg = [], src
    kind = tpl.get("bg", "desfoque")
    if kind == "imagem" and bg_input is None:
        kind = "desfoque"  # sem imagem enviada: usa o desfoque do próprio vídeo
    if kind == "desfoque":
        parts.append(f"{src}split=2[tbg][tfg]")
        parts.append(f"[tbg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                     f"boxblur=30:5,eq=brightness=-0.22:saturation=0.8,setsar=1[tpl_bg]")
        fg = "[tfg]"
    elif kind == "gradiente":
        c0, c1 = tpl.get("colors", ("0x111111", "0x333333"))
        parts.append(f"gradients=s={W}x{H}:c0={c0}:c1={c1}:r={fps}:d={dur:.3f}:speed=0.006,setsar=1,format=yuv420p[tpl_bg]")
    elif kind == "imagem":
        parts.append(f"[{bg_input}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                     f"setsar=1,format=yuv420p,fps={fps}[tpl_bg]")
    else:
        parts.append(f"color=c={tpl.get('color', '0x000000')}:s={W}x{H}:r={fps}:d={dur:.3f},format=yuv420p[tpl_bg]")

    r = int(tpl.get("radius", 0))
    parts.append(f"{fg}scale={cw}:{ch},setsar=1,format=yuva420p[tpl_cd]")
    card = "[tpl_cd]"
    if r > 0:
        parts.append(_rounded_alpha(cw, ch, r, fps, dur, "[tpl_mk]"))
        parts.append("[tpl_cd][tpl_mk]alphamerge[tpl_cda]")
        card = "[tpl_cda]"
    bg = "[tpl_bg]"
    b = int(tpl.get("border_w", 0)) if tpl.get("border") else 0
    if b:
        bw, bh = cw + 2 * b, ch + 2 * b
        parts.append(f"color=c={tpl['border']}:s={bw}x{bh}:r={fps}:d={dur:.3f},format=yuva420p[tpl_bd]")
        if r > 0:
            parts.append(_rounded_alpha(bw, bh, r + b, fps, dur, "[tpl_bmk]"))
            parts.append("[tpl_bd][tpl_bmk]alphamerge[tpl_bda]")
            border = "[tpl_bda]"
        else:
            border = "[tpl_bd]"
        parts.append(f"{bg}{border}overlay={x - b}:{y - b}:shortest=1[tpl_bg2]")
        bg = "[tpl_bg2]"
    parts.append(f"{bg}{card}overlay={x}:{y}:shortest=1,format=yuv420p{out}")
    return ";".join(parts), geo


def _ass_color(hex_rgb: str) -> str:
    h = hex_rgb.replace("0x", "").replace("#", "").rjust(6, "0")[-6:]
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ass_styles(tpl: dict, font: str, k: float) -> str:
    acc = _ass_color(tpl.get("accent", "0xE5FF00"))
    return (f"Style: Head,{font},{int(60 * k)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,"
            f"{max(3, int(5 * k))},2,5,70,70,0,1\n"
            f"Style: Foot,{font},{int(42 * k)},{acc},&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,"
            f"{max(2, int(3 * k))},1,5,60,60,0,1\n")


def ass_events(tpl: dict, geo: dict, W: int, duration: float, header: str | None, handle: str | None,
               ass_time, esc, H: int = 1920) -> list[str]:
    out = []
    end = ass_time(duration)
    if tpl.get("header") and header:
        txt = header.strip()
        txt = (txt[:48].rsplit(" ", 1)[0] + "…") if len(txt) > 50 else txt
        k = min(1.0, H / 1920) ** 0.6
        fs = int(60 * k * (0.8 if len(txt) > 30 else 1.0))   # título longo: letra menor, cabe em 2 linhas
        out.append(f"Dialogue: 2,{ass_time(0)},{end},Head,,0,0,0,,{{\\an5\\pos({W // 2},{geo['head_cy']})\\fs{fs}}}{esc(txt.upper())}")
    if tpl.get("footer") and handle:
        h = handle.strip()
        h = h if h.startswith("@") else "@" + h
        out.append(f"Dialogue: 2,{ass_time(0)},{end},Foot,,0,0,0,,{{\\an5\\pos({W // 2},{geo['foot_cy']})}}{esc(h)}")
    return out


def bg_image(settings: dict, data_dir: Path) -> Path | None:
    name = (settings or {}).get("bg_image")
    if not name:
        return None
    p = data_dir / "uploads" / Path(name).name
    return p if p.exists() else None


def preview(name: str, settings: dict, data_dir: Path) -> Path:
    """Imagem de exemplo do modelo (com o seu @ e o seu fundo). Fica guardada até você mudar algo."""
    import hashlib
    import subprocess

    from . import config
    from .render import _ass, _ass_time, _esc
    tpl = TEMPLATES[name]
    img = bg_image(settings, data_dir) if tpl.get("bg") == "imagem" else None
    handle = (settings or {}).get("handle") or "seucanal"
    key = hashlib.md5(f"{name}|{handle}|{img and img.stat().st_mtime}|{tpl}".encode()).hexdigest()[:10]
    folder = data_dir / "previews"
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{name}_{key}.jpg"
    if out.exists():
        return out
    W, H, fps, dur = 1080, 1920, 1, 1.0   # tamanho real; a imagem é reduzida no fim
    k = min(1.0, H / 1920) ** 0.6
    styles = (f"Style: Sub,{config.FONT},{int(72 * k)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,"
              f"{max(3, int(6 * k))},3,2,40,40,{int(H * 0.29)},1\n")
    events = []
    geo = None
    if tpl.get("card"):
        geo = geometry(tpl, W, H)
        styles += ass_styles(tpl, config.FONT, k)
        events = ass_events(tpl, geo, W, dur, "Ele descobriu o segredo da caverna escondida", handle, _ass_time, _esc, H)
    mv = to_card(geo, H, int(H * 0.29)) if geo else int(H * 0.29)
    events.append(f"Dialogue: 1,{_ass_time(0)},{_ass_time(dur)},Sub,,0,0,{mv},,LEGENDA {{\\c&H0000F0FF&}}AQUI")
    ass = folder / f"{name}_{key}.ass"
    ass.write_text(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\n"
                   f"ScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
                   f"SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                   f"Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                   f"{styles}\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                   + "\n".join(events) + "\n", encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=s={W}x{H}:r={fps}:d={dur}"]
    if img:
        cmd += ["-loop", "1", "-t", "1", "-i", str(img.resolve())]
    if geo:
        comp, _ = compose(tpl, W, H, fps, dur, "[0:v]", "[vc]", bg_input=1 if img else None)
        fc = f"{comp};[vc]{_ass(ass.name)},scale=540:-2[vo]"
    else:
        fc = f"[0:v]{_ass(ass.name)},scale=540:-2[vo]"
    cmd += ["-filter_complex", fc, "-map", "[vo]", "-frames:v", "1", out.name]
    r = subprocess.run(cmd, cwd=folder, capture_output=True, text=True)
    ass.unlink(missing_ok=True)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError("não consegui gerar a prévia: " + r.stderr[-300:])
    return out
