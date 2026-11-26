"""👁️ Claude "assiste" o vídeo: quadros-chave (mudança de cena + intervalo fixo) + transcrição → análise.

O Claude não recebe vídeo direto, só imagens. Então:
  1. o ffmpeg tira quadros nas mudanças de cena e a cada N segundos (com teto de quadros);
  2. cada quadro vai para o Claude com o horário e a fala daquele momento;
  3. o Claude devolve o que acontece, os melhores momentos e os ganchos (mesmo formato do Gemini).

Dois usos:
  • no sistema (API): `analyze()` vira o sinal 👁️ quando não há Gemini, e o modo "Analisar vídeo" do app;
  • no Claude Code (sem chave de API): `python -m darkclip.vision <link|arquivo>` monta uma pasta com os
    quadros + índice em Markdown, e a skill /assistir-video manda o próprio Claude Code ler as imagens.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

from . import config

FRAME_W = 512


# ------------------------------------------------------------------ quadros
def extract_frames(video: Path, out: Path, start: float = 0, end: float | None = None,
                   max_frames: int = 60, every: float | None = None, scene: float = 0.32) -> list[dict]:
    """Quadros nas mudanças de cena + a cada `every` s (piso), reduzidos para no máx. `max_frames`."""
    from .download import probe_duration
    out.mkdir(parents=True, exist_ok=True)
    dur = (end or probe_duration(video)) - start
    every = every or max(2.0, dur / max_frames)
    # 1) instantes de mudança de cena (barato: 4 fps em baixa resolução)
    p = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", str(video),
                        "-vf", f"fps=4,scale=160:-2,select='gt(scene,{scene})',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True)
    cuts = [start + float(m) for m in re.findall(r"pts_time:([\d.]+)", p.stderr)]
    # 2) piso a cada `every` s, para cenas longas também aparecerem
    times = sorted(set([round(t, 1) for t in cuts] + [round(start + k * every, 1) for k in range(int(dur / every) + 1)]))
    times = [t for t in times if start <= t < start + dur - 0.2]
    if len(times) > max_frames:  # mantém distribuição uniforme no tempo
        step = len(times) / max_frames
        times = [times[int(i * step)] for i in range(max_frames)]
    frames = []
    for i, t in enumerate(times):
        f = out / f"q{i:03d}_{int(t // 60):02d}m{t % 60:04.1f}s.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", f"scale={FRAME_W}:-2", "-q:v", "5", str(f)], capture_output=True)
        if f.exists():
            frames.append({"t": t, "file": f, "scene_cut": any(abs(t - c) < 0.3 for c in cuts)})
    return frames


def _fmt(t: float) -> str:
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def _speech_near(segs: list[dict] | None, t: float, until: float) -> str:
    if not segs:
        return ""
    return " ".join(s["text"] for s in segs if s["end"] > t and s["start"] < until)[:400]


# ------------------------------------------------------------------ pasta para o Claude Code (skill)
def build_folder(video: Path, out: Path, segs: list[dict] | None, title: str = "", max_frames: int = 60) -> Path:
    """Gera <out>/INDICE.md com cada quadro (caminho + horário + fala) para o Claude Code ler as imagens."""
    frames = extract_frames(video, out / "quadros", max_frames=max_frames)
    lines = [f"# Vídeo: {title or video.name}", "",
             f"{len(frames)} quadros. Leia CADA imagem listada abaixo (ferramenta Read) junto com a fala daquele trecho.", ""]
    for i, fr in enumerate(frames):
        nxt = frames[i + 1]["t"] if i + 1 < len(frames) else fr["t"] + 10
        lines.append(f"## {_fmt(fr['t'])}{' · corte de cena' if fr['scene_cut'] else ''}")
        lines.append(f"- Imagem: `{fr['file'].resolve()}`")
        fala = _speech_near(segs, fr["t"], nxt)
        if fala:
            lines.append(f"- Fala: {fala}")
        lines.append("")
    if segs:
        (out / "transcricao.txt").write_text("\n".join(f"[{_fmt(s['start'])}] {s['text']}" for s in segs), encoding="utf-8")
        lines.append("Transcrição completa: `" + str((out / "transcricao.txt").resolve()) + "`")
    idx = out / "INDICE.md"
    idx.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return idx


# ------------------------------------------------------------------ análise pela API do Claude
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "resumo do vídeo em 3-5 frases"},
        "timeline": {"type": "array", "description": "o que acontece, em ordem", "items": {
            "type": "object", "properties": {
                "t": {"type": "string", "description": "MM:SS"}, "what": {"type": "string"}},
            "required": ["t", "what"], "additionalProperties": False}},
        "moments": {"type": "array", "items": {
            "type": "object", "properties": {
                "start": {"type": "string", "description": "MM:SS"}, "end": {"type": "string", "description": "MM:SS"},
                "score": {"type": "integer"}, "what": {"type": "string", "description": "o que se vê e o que se ouve"},
                "why": {"type": "string"}, "hook": {"type": "string"}, "title": {"type": "string"},
                "visual": {"type": "string", "description": "rosto, 2 pessoas, tela, ação, texto"}},
            "required": ["start", "end", "score", "what", "why", "hook", "title", "visual"],
            "additionalProperties": False}},
        "hook_analysis": {"type": "string", "description": "como o vídeo prende nos primeiros segundos (ou por que não prende)"},
        "risks": {"type": "string", "description": "direitos autorais, marcas d'água, conteúdo sensível, música"},
    },
    "required": ["summary", "timeline", "moments", "hook_analysis", "risks"],
    "additionalProperties": False,
}


def _img_block(path: Path) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(path.read_bytes()).decode()}}


def analyze(video: Path, segs: list[dict] | None, *, workdir: Path, start: float = 0, end: float | None = None,
            niche: str = "", request: str = "", n: int = 10, max_frames: int = 60) -> dict:
    """Claude vê os quadros + lê a fala e devolve {summary, timeline, moments(start/end em s), ...}."""
    if not config.HAS_CLAUDE:
        raise RuntimeError("precisa de ANTHROPIC_API_KEY (ou use a skill /assistir-video no Claude Code)")
    from .ai import _ask_json
    frames = extract_frames(video, workdir / "quadros", start, end, max_frames=max_frames)
    content: list[dict] = [{"type": "text", "text": (
        f"Você vai 'assistir' a um vídeo por {len(frames)} quadros em ordem, cada um com o horário e a fala daquele trecho. "
        "Descreva o que acontece (o que se VÊ e o que se OUVE), aponte os melhores momentos para Shorts/Reels "
        f"de 20 a 60 s (até {n}), com começo forte e fim no desfecho"
        + (f", para um canal de {niche}" if niche else "") + ". "
        + (f"PEDIDO DO USUÁRIO: {request}. " if request else "")
        + "Use horários reais (MM:SS). Score honesto de 0 a 100. Responda em português do Brasil.")}]
    for i, fr in enumerate(frames):
        nxt = frames[i + 1]["t"] if i + 1 < len(frames) else fr["t"] + 8
        fala = _speech_near(segs, fr["t"], nxt)
        content.append({"type": "text", "text": f"[{_fmt(fr['t'])}]{' (corte de cena)' if fr['scene_cut'] else ''}"
                                                + (f" Fala: {fala}" if fala else " (sem fala)")})
        content.append(_img_block(fr["file"]))
    data = _ask_json(content, ANALYSIS_SCHEMA)
    from .gemini import _sec
    moments = []
    for m in data.get("moments", []):
        s, e = _sec(m["start"]), _sec(m["end"])
        if e > s:
            moments.append({**m, "start": s, "end": e, "score": max(0, min(100, int(m.get("score") or 0)))})
    data["moments"] = moments
    data["frames"] = len(frames)
    data["model"] = config.CLAUDE_MODEL
    return data


def report_md(a: dict, title: str = "") -> str:
    from .comments import fmt
    out = [f"# Análise do vídeo{(' — ' + title) if title else ''}", "", "## Resumo", a.get("summary", ""), "",
           "## Gancho (primeiros segundos)", a.get("hook_analysis", ""), "", "## O que acontece"]
    out += [f"- **{x['t']}** {x['what']}" for x in a.get("timeline", [])]
    out += ["", "## Melhores momentos para cortes", "", "| Trecho | Nota | O que acontece | Gancho sugerido |",
            "|---|---|---|---|"]
    for m in sorted(a.get("moments", []), key=lambda m: -m["score"]):
        out.append(f"| {fmt(m['start'])}–{fmt(m['end'])} | {m['score']} | {m['what'].replace('|', '/')} | {m['hook']} |")
    out += ["", "## Riscos", a.get("risks", "")]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ CLI (usada pela skill /assistir-video)
def main(argv: list[str] | None = None) -> None:
    import argparse
    import tempfile
    ap = argparse.ArgumentParser(description="Prepara um vídeo para o Claude assistir (quadros + fala)")
    ap.add_argument("fonte", help="link (YouTube, TikTok, Instagram, Facebook…) ou arquivo de vídeo")
    ap.add_argument("--out", help="pasta de saída (padrão: data/assistir/<nome>)")
    ap.add_argument("--quadros", type=int, default=60, help="máximo de quadros (padrão 60)")
    ap.add_argument("--lang", default="pt")
    ap.add_argument("--api", action="store_true", help="em vez de preparar a pasta, analisa direto pela API do Claude")
    a = ap.parse_args(argv)
    from . import transcribe
    from .download import download
    src = Path(a.fonte)
    title = src.stem
    if src.exists():
        video, subs = src, (src.with_suffix(".vtt") if src.with_suffix(".vtt").exists() else None)
    else:
        work = Path(tempfile.mkdtemp(prefix="dc_assistir_"))
        d = download(a.fonte, work, lang=a.lang, max_height=480)
        video, subs, title = d["video"], d["subs"], d["title"]
    try:
        segs, how = transcribe.transcribe(video, subs, a.lang)
    except Exception as e:  # sem legenda e sem whisper: analisa só a imagem
        print(f"(sem transcrição: {e})", file=sys.stderr)
        segs, how = None, "nenhuma"
    out = Path(a.out) if a.out else config.DATA_DIR / "assistir" / re.sub(r"[^\w\-]+", "_", title)[:60]
    if a.api:
        res = analyze(video, segs, workdir=out, max_frames=a.quadros)
        md = report_md(res, title)
        (out / "analise.md").write_text(md, encoding="utf-8")
        (out / "analise.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(md)
    else:
        idx = build_folder(video, out, segs, title, max_frames=a.quadros)
        print(f"Pronto. Transcrição: {how}. Leia o índice: {idx.resolve()}")


if __name__ == "__main__":
    main()
