"""🎞️ Estudo de edição: mede como um vídeo de referência foi editado, para o DarkClip copiar a TÉCNICA.

    python -m darkclip.estudo "LINK ou arquivo.mp4" [--quadros 24] [--idioma pt]

Gera em data/estudos/<nome>/:
  - RELATORIO.md: números do ritmo (cortes por minuto, duração das cenas, silêncio, fala por minuto,
    o que acontece nos 3 primeiros segundos) e como ler cada um;
  - grade.png: quadros ao longo do vídeo; inicio.png: os 3 primeiros segundos (o gancho);
  - dados.json: os mesmos números, para comparar vídeos.
Depois, no Claude Code: /estudar-edicao (lê tudo e escreve o padrão em docs/ESTUDO_EDICAO.md).
Estude a técnica (ritmo, zoom, texto, som); não copie vídeo, marca ou identidade de outro canal.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from . import config, signals


def _slug(s: str) -> str:
    return re.sub(r"[^\w]+", "_", s.lower()).strip("_")[:50] or "video"


def _probe(v: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(v)],
                         capture_output=True, text=True)
    d = json.loads(out.stdout or "{}")
    vs = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"w": int(vs.get("width") or 0), "h": int(vs.get("height") or 0),
            "dur": float((d.get("format") or {}).get("duration") or 0)}


def scene_cuts(v: Path, thr: float = 0.3) -> list[float]:
    """Momentos de troca de cena (corte de edição), pelo filtro de cena do ffmpeg."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(v), "-an", "-vf",
                        f"scale=320:-2,select='gt(scene,{thr})',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def _frames(v: Path, times: list[float], out: Path, cols: int, width: int = 240) -> None:
    tmp = out.parent / "_q"
    tmp.mkdir(exist_ok=True)
    for k, t in enumerate(times):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(v), "-frames:v", "1",
                        "-vf", f"scale={width}:-2", str(tmp / f"q{k:03d}.png")], capture_output=True)
    rows = -(-len(times) // cols)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(tmp / "q%03d.png"),
                    "-vf", f"tile={cols}x{rows}:padding=4:color=black", "-frames:v", "1", str(out)], capture_output=True)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()


def _words_per_min(subs: Path | None, dur: float) -> float | None:
    if not subs or not subs.exists() or dur <= 0:
        return None
    from .transcribe import parse_vtt
    n = sum(len(s["words"]) for s in parse_vtt(subs))
    return round(n / (dur / 60), 0) if n else None


def study(source: str, quadros: int = 24, lang: str = "pt") -> Path:
    if Path(source).exists():
        video, subs, title = Path(source), None, Path(source).stem
        folder = config.DATA_DIR / "estudos" / _slug(title)
        folder.mkdir(parents=True, exist_ok=True)
    else:
        from .download import download
        print("⬇️  Baixando o vídeo (pode levar alguns minutos)…", flush=True)
        tmp = config.DATA_DIR / "estudos" / "_baixando"
        d = download(source, tmp, lang=lang, max_height=720)
        title = d.get("title") or "video"
        folder = config.DATA_DIR / "estudos" / _slug(title)
        if folder.exists():
            import shutil
            shutil.rmtree(folder)
        tmp.rename(folder)
        video = folder / Path(d["video"]).name
        subs = folder / Path(d["subs"]).name if d.get("subs") else None
    info = _probe(video)
    dur = info["dur"]
    print(f"✂️  Medindo os cortes de cena ({dur / 60:.0f} min de vídeo)…", flush=True)
    cuts = scene_cuts(video)
    shots = [b - a for a, b in zip([0.0] + cuts, cuts + [dur]) if b - a > 0.05]
    print("🔊 Medindo silêncios e volume…", flush=True)
    energy = signals.audio_energy(video) or []
    silence = None
    if energy:
        med = sorted(energy)[len(energy) // 2]
        silence = round(100 * sum(e < med - 15 for e in energy) / len(energy), 1)
    data = {
        "titulo": title, "fonte": source, "duracao_s": round(dur, 1),
        "formato": "vertical (Short/Reels)" if info["h"] > info["w"] else "horizontal",
        "cortes": len(cuts), "cortes_por_min": round(len(cuts) / (dur / 60), 1) if dur else None,
        "cena_media_s": round(sum(shots) / len(shots), 2) if shots else None,
        "cena_mais_longa_s": round(max(shots), 1) if shots else None,
        "primeiro_corte_s": cuts[0] if cuts else None,
        "cortes_nos_3_primeiros_s": sum(c < 3 for c in cuts),
        "silencio_pct": silence, "palavras_por_min": _words_per_min(subs, dur),
        "tempos_dos_cortes": cuts[:200],
    }
    print("🖼️  Tirando os quadros para a grade…", flush=True)
    n = max(6, quadros)
    times = [dur * (k + 0.5) / n for k in range(n)]
    _frames(video, times, folder / "grade.png", cols=6)
    _frames(video, [0.2, 0.8, 1.5, 2.2, 2.9], folder / "inicio.png", cols=5, width=300)
    (folder / "dados.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [
        f"# Estudo de edição: {title}", "",
        f"Fonte: {source}", "",
        "| Medida | Valor | Como ler |", "|---|---|---|",
        f"| Duração | {data['duracao_s']} s ({data['formato']}) | |",
        f"| Cortes de cena | {data['cortes']} ({data['cortes_por_min']}/min) | Mais de 20/min = ritmo bem acelerado; menos de 6/min = calmo |",
        f"| Duração média de cada cena | {data['cena_media_s']} s | Shorts que prendem costumam trocar algo a cada 2–5 s |",
        f"| Cena mais longa | {data['cena_mais_longa_s']} s | Cenas longas pedem zoom, texto ou som para não cansar |",
        f"| Primeiro corte | {data['primeiro_corte_s']} s | Corte antes de 2 s = gancho visual rápido |",
        f"| Cortes nos 3 primeiros segundos | {data['cortes_nos_3_primeiros_s']} | |",
        f"| Silêncio | {data['silencio_pct']}% | Perto de 0% = pausas cortadas (jump cuts) |",
        f"| Palavras por minuto | {data['palavras_por_min'] or 'sem legenda'} | 150+ = fala rápida |",
        "", "## Imagens",
        f"- `grade.png`: {n} quadros do vídeo, da esquerda para a direita e de cima para baixo "
        f"(um a cada {dur / n:.1f} s).",
        "- `inicio.png`: 0,2 s · 0,8 s · 1,5 s · 2,2 s · 2,9 s (o gancho).",
        "", "## O que observar nas imagens",
        "- Legenda: cor, tamanho, posição, quantas palavras por vez, destaque de palavra.",
        "- Textos extras na tela, emojis, figurinhas, setas, molduras, nome do canal.",
        "- Zoom: o enquadramento muda de tamanho entre quadros vizinhos?",
        "- Gancho: o que aparece e o que está escrito nos 3 primeiros segundos.",
        "- Final: termina em loop, em pergunta ou com chamada para seguir?",
    ]
    (folder / "RELATORIO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder


def main() -> None:
    ap = argparse.ArgumentParser(description="Estudo de edição de um vídeo de referência")
    ap.add_argument("fonte", help="link do vídeo ou caminho de um arquivo")
    ap.add_argument("--quadros", type=int, default=24)
    ap.add_argument("--idioma", default="pt")
    a = ap.parse_args()
    folder = study(a.fonte, a.quadros, a.idioma)
    print(f"\n✅ Estudo pronto em: {folder}")
    print(f"   Leia {folder / 'RELATORIO.md'} e as imagens grade.png e inicio.png")
    print("   No Claude Code, peça: /estudar-edicao")


if __name__ == "__main__":
    main()
