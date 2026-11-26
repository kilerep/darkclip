"""Análise de comentários: quais partes do vídeo o público mais comenta.

Sinais extraídos dos comentários do YouTube (via yt-dlp):
  1. Timestamps citados ("2:31", "1:02:10")  -> peso = 1 + log(1+curtidas)
  2. Frases citadas sem timestamp            -> casadas com a transcrição (sobreposição de palavras)
  3. Reações (kkkk, 😂, "arrepiei", "morri") -> reforçam o momento citado
Resultado: curva de atenção por segundo, picos com os comentários que os explicam,
e uma função attention_at() usada na nota final dos clipes.

Uso direto (também usado pela skill /analisar-comentarios):
  python -m darkclip.comments "https://youtu.be/..." [--max 800] [--json saida.json]
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

TS = re.compile(r"(?<![\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?![\d:])")
REACTION = re.compile(
    r"k{4,}|(?:ha){3,}|(?:rs){3,}|😂|🤣|😭|💀|🔥|😱|🤯|❤️|arrepi|morri|chorei|que isso|surreal|insano|genial|"
    r"melhor parte|melhor momento|best part|lmao|lol\b|omg|goat", re.I)
STOP = set("""a o as os um uma uns umas de do da dos das e é em no na nos nas que se por para pra pro com sem mas
ou eu tu ele ela nós vós eles elas me te lhe isso isto aquilo esse essa este esta foi ser ter tem tá ta não nao sim
muito mais menos já ja só so quando como onde porque pq vc você voce vcs the a an of to and is in it that this i you
he she was for on with be are at my me so de""".split())

BUCKET = 1.0          # resolução da curva (s)
SPREAD = (-2, 18)     # um timestamp citado "cobre" de 2 s antes a 18 s depois


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _words(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", _norm(t)) if w not in STOP and len(w) > 2]


def fetch_comments(url: str, max_comments: int = 800, timeout: int = 600) -> tuple[list[dict], dict]:
    """Baixa os comentários (os mais curtidos primeiro). Retorna (comentários, metadados)."""
    from .download import _err, _ytdlp
    # max_comments = total, pais, respostas, respostas por fio, profundidade (padrão do YouTube é "new": pedimos "top")
    args = f"youtube:max_comments={max_comments},all,{max_comments // 4},3,2;comment_sort=top"
    out = subprocess.run(_ytdlp() + ["--skip-download", "--no-playlist", "--write-comments", "--sleep-requests", "1",
                                     "--extractor-args", args, "--dump-single-json", url],
                         capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise _err(out.stderr, "comentários")
    meta = json.loads(out.stdout)
    comments = [{"text": c.get("text") or "", "likes": int(c.get("like_count") or 0),
                 "author": c.get("author") or "", "pinned": bool(c.get("is_pinned")),
                 "reply": c.get("parent") not in (None, "root")}
                for c in (meta.pop("comments", None) or [])]
    return comments, meta


def _timestamps(text: str, duration: float | None) -> list[float]:
    out = []
    for h, m, s in TS.findall(text):
        t = int(h or 0) * 3600 + int(m) * 60 + int(s)
        if int(s) < 60 and (not duration or t <= duration):
            out.append(float(t))
    return out


def _match_quote(text: str, index: dict, segs: list[dict]) -> int | None:
    """Encontra o trecho da transcrição que o comentário cita (sem timestamp)."""
    ws = set(_words(text))
    if len(ws) < 3:
        return None
    votes = Counter()
    for w in ws:
        for i in index.get(w, ()):
            votes[i] += 1
    best = None
    for i, n in votes.most_common(5):
        # junta a frase com a vizinha (citações costumam atravessar duas legendas)
        seg_words = set(_words(segs[i]["text"] + " " + (segs[i + 1]["text"] if i + 1 < len(segs) else "")))
        overlap = len(ws & seg_words)
        if overlap >= 3 and overlap / len(ws) >= 0.6:
            if best is None or overlap > best[1]:
                best = (i, overlap)
    return best[0] if best else None


def analyze(comments: list[dict], duration: float | None = None, segs: list[dict] | None = None) -> dict:
    """Curva de atenção + picos. `segs` (transcrição) habilita o casamento de frases citadas."""
    n = int((duration or 0) / BUCKET) + 1 if duration else 0
    curve: dict[int, float] = defaultdict(float)
    refs: dict[int, list[tuple[float, dict, str]]] = defaultdict(list)   # bucket -> (peso, comentário, tipo)
    index: dict[str, set[int]] = defaultdict(set)
    if segs:
        for i, s in enumerate(segs):
            for w in set(_words(s["text"])):
                index[w].add(i)
    stats = Counter()
    for c in comments:
        w = 1.0 + math.log1p(c["likes"]) + (1.0 if c["pinned"] else 0.0)
        reaction = bool(REACTION.search(c["text"]))
        if reaction:
            w *= 1.3
        times = _timestamps(c["text"], duration)
        if len(times) > 5:  # lista de capítulos/resumo: não é reação a um momento específico
            w /= len(times)
        kind = "timestamp"
        if not times and segs:
            i = _match_quote(c["text"], index, segs)
            if i is not None:
                times, kind = [segs[i]["start"]], "citação"
                w *= 0.8   # casamento por texto é menos certeiro que um timestamp explícito
        if not times:
            continue
        stats[kind] += 1
        for t in times:
            for b in range(int((t + SPREAD[0]) / BUCKET), int((t + SPREAD[1]) / BUCKET) + 1):
                if b >= 0 and (not n or b < n):
                    dist = abs(b * BUCKET - (t + 4))           # pico ~4 s depois do instante citado
                    curve[b] += w * max(0.25, 1 - dist / 16)
            refs[int(t / BUCKET)].append((w, c, kind))
    if not curve:
        return {"total": len(comments), "mapped": 0, "by_kind": dict(stats), "peaks": [], "curve": {}}
    peak_val = max(curve.values())
    norm = {b: round(v / peak_val, 3) for b, v in curve.items()}
    peaks = _peaks(norm, refs)
    return {"total": len(comments), "mapped": sum(stats.values()), "by_kind": dict(stats),
            "peaks": peaks, "curve": norm}


def _peaks(curve: dict[int, float], refs, min_gap: float = 25.0, top: int = 12) -> list[dict]:
    """Picos locais da curva, com os comentários que os explicam."""
    cands = sorted(curve.items(), key=lambda kv: -kv[1])
    picked: list[dict] = []
    for b, v in cands:
        t = b * BUCKET
        if v < 0.15 or any(abs(t - p["peak"]) < min_gap for p in picked):
            continue
        near = [r for bb in range(b - 20, b + 3) for r in refs.get(bb, [])]
        near.sort(key=lambda r: -r[0])
        start = min((bb * BUCKET for bb in range(b - 20, b + 3) if refs.get(bb)), default=t - 4)
        picked.append({
            "peak": t, "start": max(0.0, start - 2), "end": t + 14, "score": v, "mentions": len(near),
            "comments": [{"text": r[1]["text"][:220], "likes": r[1]["likes"], "type": r[2]} for r in near[:4]],
        })
        if len(picked) >= top:
            break
    return picked


# ------------------------------------------------------------------ chat de lives (replay)
def fetch_live_chat(url: str, workdir: Path, timeout: int = 900) -> list[float]:
    """Instantes (s) de cada mensagem do chat do replay de uma live do YouTube."""
    from .download import _err, _ytdlp
    workdir.mkdir(parents=True, exist_ok=True)
    out = subprocess.run(_ytdlp() + ["--skip-download", "--no-playlist", "--write-subs", "--sub-langs", "live_chat",
                                     "-o", str(workdir / "chat.%(ext)s"), url],
                         capture_output=True, text=True, timeout=timeout)
    f = next(workdir.glob("chat*.live_chat.json"), None)
    if not f:
        raise _err(out.stderr or "ERROR: esta live não tem replay de chat", "chat")
    times = []
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            act = json.loads(line)["replayChatItemAction"]
            times.append(int(act["videoOffsetTimeMsec"]) / 1000)
        except (ValueError, KeyError, TypeError):
            continue
    return times


def analyze_chat(times: list[float], duration: float | None = None, window: float = 25.0,
                 delay: float = 20.0) -> dict:
    """Picos de chat acima da média (janela de 25 s), recuados ~20 s:
    o chat reage depois do momento (estudo LIGHTOR, Twitch)."""
    if not times:
        return {"total": 0, "mapped": 0, "by_kind": {}, "peaks": [], "curve": {}}
    end = int(duration or max(times)) + 1
    cnt = [0] * (end + 1)
    for t in times:
        if 0 <= t <= end:
            cnt[int(t)] += 1
    w = int(window)
    roll = [sum(cnt[max(0, i - w + 1): i + 1]) for i in range(len(cnt))]
    base = sorted(roll)[len(roll) // 2] or 1           # mediana = ritmo normal do chat
    curve = {}
    for i, v in enumerate(roll):
        excess = max(0.0, v / base - 1.0)
        if excess > 0:
            b = int(max(0, i - w - delay + 10))           # início provável do momento
            curve[b] = max(curve.get(b, 0.0), excess)
    peak = max(curve.values(), default=0) or 1
    norm = {b: round(v / peak, 3) for b, v in curve.items()}
    return {"total": len(times), "mapped": len(times), "by_kind": {"chat": len(times)},
            "peaks": _peaks(norm, {}), "curve": norm}


def merge(*analyses: dict | None) -> dict | None:
    """Junta comentários + chat numa curva única (máximo ponto a ponto)."""
    items = [a for a in analyses if a and a.get("curve")]
    if not items:
        return None
    if len(items) == 1:
        return items[0]
    curve: dict = {}
    for a in items:
        for b, v in a["curve"].items():
            curve[int(b)] = max(curve.get(int(b), 0.0), v)
    peaks = sorted([p for a in items for p in a["peaks"]], key=lambda p: -p["score"])[:12]
    return {"total": sum(a["total"] for a in items), "mapped": sum(a["mapped"] for a in items),
            "by_kind": {k: v for a in items for k, v in a["by_kind"].items()}, "peaks": peaks, "curve": curve}


def attention_at(analysis: dict | None, start: float, end: float) -> float | None:
    """0-1: atenção dos comentários no intervalo (máximo da curva). None se não houver dados."""
    if not analysis or not analysis.get("curve"):
        return None
    curve = analysis["curve"]
    vals = [curve.get(b, curve.get(str(b), 0.0)) for b in range(int(start / BUCKET), int(end / BUCKET) + 1)]
    return round(max(vals), 3) if vals else 0.0


def themes(comments: list[dict], top: int = 15) -> list[tuple[str, int]]:
    """Palavras/temas mais citados (ponderados por curtidas)."""
    cnt = Counter()
    for c in comments:
        for w in set(_words(c["text"])):
            cnt[w] += 1 + math.log1p(c["likes"])
    return [(w, round(v)) for w, v in cnt.most_common(top)]


def fmt(t: float) -> str:
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def report(analysis: dict, comments: list[dict], title: str = "") -> str:
    lines = [f"# Comentários — {title}".rstrip(" —"), "",
             f"- Comentários lidos: **{analysis['total']}**",
             f"- Ligados a um momento do vídeo: **{analysis['mapped']}** {analysis['by_kind']}", ""]
    if analysis["peaks"]:
        lines += ["## Momentos que mais chamam atenção", "",
                  "| # | Momento | Atenção | Menções | O que o público diz |", "|---|---|---|---|---|"]
        for i, p in enumerate(analysis["peaks"], 1):
            quote = (p["comments"][0]["text"].replace("|", "/").replace("\n", " ")[:120]) if p["comments"] else ""
            lines.append(f"| {i} | {fmt(p['start'])}–{fmt(p['end'])} | {int(p['score'] * 100)} | {p['mentions']} | {quote} |")
    else:
        lines += ["_Nenhum comentário cita um momento específico (sem timestamps nem frases reconhecíveis)._"]
    top = sorted(comments, key=lambda c: -c["likes"])[:8]
    lines += ["", "## Comentários mais curtidos", ""]
    lines += [f"- ({c['likes']} 👍) {c['text'][:200].replace(chr(10), ' ')}" for c in top]
    lines += ["", "## Temas mais citados", "", ", ".join(f"{w} ({n})" for w, n in themes(comments))]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Quais partes do vídeo os comentários mais citam")
    ap.add_argument("url")
    ap.add_argument("--max", type=int, default=800, help="máximo de comentários (padrão 800)")
    ap.add_argument("--lang", default="pt", help="idioma da legenda para casar frases citadas")
    ap.add_argument("--no-transcript", action="store_true", help="não baixar legenda (só timestamps)")
    ap.add_argument("--json", help="salvar a análise completa em JSON")
    a = ap.parse_args(argv)

    comments, meta = fetch_comments(a.url, a.max)
    segs = None
    if not a.no_transcript:
        try:
            import tempfile
            from .download import fetch_transcript_only
            from .transcribe import parse_vtt
            src = fetch_transcript_only(a.url, Path(tempfile.mkdtemp(prefix="dc_")), a.lang)
            segs = parse_vtt(src["subs"]) if src.get("subs") else None
        except Exception as e:  # sem legenda: segue só com timestamps
            print(f"(sem transcrição: {e})", file=sys.stderr)
    res = analyze(comments, float(meta.get("duration") or 0) or None, segs)
    print(report(res, comments, meta.get("title", "")))
    if a.json:
        Path(a.json).write_text(json.dumps({"title": meta.get("title"), "analysis": res,
                                            "themes": themes(comments)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
