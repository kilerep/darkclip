"""Linha de comando.

  python -m darkclip.cli clip  "https://youtu.be/..." -n 5 --crop face
  python -m darkclip.cli clip  --file video.mp4 --subs video.vtt
  python -m darkclip.cli story --topic "O caso do voo 19"  [--bg-url URL]
  python -m darkclip.cli story --script "Texto pronto..."
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from . import config
from .pipeline import Job, run, safe_print


def _hms(v: str) -> float:
    t = 0.0
    for x in (v or "").split(":"):
        if x.strip():
            t = t * 60 + float(x)
    return t


def main() -> None:
    ap = argparse.ArgumentParser(prog="darkclip")
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("clip", help="vídeo longo -> Shorts")
    c.add_argument("url", nargs="?")
    c.add_argument("--file", help="vídeo local em vez de URL")
    c.add_argument("--subs", help="legenda .vtt do vídeo local (opcional)")
    c.add_argument("-n", "--n-clips", type=int, default=4)
    c.add_argument("--min", dest="min_s", type=int, default=20)
    c.add_argument("--max", dest="max_s", type=int, default=58)
    c.add_argument("--crop", choices=["auto", "track", "split", "gamer", "blur", "center"], default="auto",
                   help="auto: segue rosto / tela dividida p/ 2 pessoas / desfoque se não houver rosto")
    c.add_argument("--style", choices=["amarelo", "verde", "caixa", "minimal"], default="amarelo")
    c.add_argument("--no-jumpcut", action="store_true", help="não remover silêncios")
    c.add_argument("--no-zoom", action="store_true", help="sem zoom de impacto")
    c.add_argument("--no-progress", action="store_true", help="sem barra de progresso")
    c.add_argument("--full", action="store_true", help="baixar o vídeo inteiro (desliga o modo inteligente)")
    c.add_argument("--pedido", default="", help='o que procurar, ex.: "a parte em que ele fala do acidente"')
    c.add_argument("--no-comments", action="store_true", help="não analisar comentários/chat")
    c.add_argument("--no-visual", action="store_true", help="não usar o Gemini para assistir o vídeo")
    c.add_argument("--aspect", choices=["9:16", "4:5", "1:1", "original"], default=None,
                   help="padrão: 9:16 nos cortes, original nas ferramentas")
    c.add_argument("--distancia", choices=["padrao", "longe"], default="padrao", help="câmera mais aberta")
    c.add_argument("--de", default="", help="início do intervalo (h:mm:ss)")
    c.add_argument("--ate", default="", help="fim do intervalo (h:mm:ss)")
    c.add_argument("--partes", type=float, default=0, help="dividir em partes de N minutos (lives longas)")
    c.add_argument("--sem-legenda", action="store_true")
    c.add_argument("--sem-efeitos", action="store_true", help="sem whoosh/impacto")
    c.add_argument("--ferramenta", choices=["clip", "legendar", "silencios"], default="clip",
                   help="legendar = legenda no vídeo inteiro; silencios = tira as pausas do vídeo inteiro")
    c.add_argument("--lang", default="pt")
    c.add_argument("--niche", default="")
    c.add_argument("--no-grade", action="store_true")
    c.add_argument("--no-hook", action="store_true")
    c.add_argument("--music", help="trilha de fundo (mp3)")

    s = sub.add_parser("story", help="Short dark narrado")
    s.add_argument("--topic", default="")
    s.add_argument("--script")
    s.add_argument("--voice", default=config.VOICE)
    s.add_argument("--bg-url")
    s.add_argument("--bg-file")
    s.add_argument("--music")
    a = ap.parse_args()

    def stash(path: str | None) -> str | None:
        if not path:
            return None
        dst = config.UPLOADS_DIR / Path(path).name
        if Path(path).resolve() != dst.resolve():
            shutil.copy(path, dst)
        return dst.name

    if a.mode == "clip":
        if not (a.url or a.file):
            ap.error("informe uma URL ou --file")
        params = dict(mode="clip", url=a.url, upload=stash(a.file), upload_subs=stash(a.subs),
                      n_clips=a.n_clips, min_s=a.min_s, max_s=a.max_s, crop=a.crop, lang=a.lang,
                      niche=a.niche, grade=not a.no_grade, hook=not a.no_hook, music=stash(a.music),
                      style=a.style, jumpcut=not a.no_jumpcut, zoom=not a.no_zoom, progress=not a.no_progress,
                      smart=not a.full, request=a.pedido, comments=not a.no_comments, visual=not a.no_visual,
                      aspect=a.aspect or ("9:16" if a.ferramenta == "clip" else "original"), distance=a.distancia, range_start=_hms(a.de), range_end=_hms(a.ate),
                      part_min=a.partes, captions=not a.sem_legenda, sfx=not a.sem_efeitos)
        params["mode"] = a.ferramenta
    else:
        params = dict(mode="story", topic=a.topic, script=a.script, voice=a.voice, bg_url=a.bg_url,
                      bg_upload=stash(a.bg_file), music=stash(a.music))
    job = Job.create(params)
    run(job)
    safe_print(f"\nResultados em: {job.dir}")
    for cl in job.data["clips"]:
        r = cl.get("render", {})
        # safe_print: o título vem da IA e pode trazer emoji, que o terminal do Windows não escreve
        safe_print(f" • {cl.get('file', 'ERRO')}  [{cl.get('score')}]  {cl['title']}  "
                   f"{r.get('layout', '')} {r.get('duration', '')}s cortes={r.get('cuts', '')} {cl.get('error', '')}")


if __name__ == "__main__":
    main()
