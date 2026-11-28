"""Reenquadramento inteligente 16:9 -> 9:16.

- Detecta rostos (YuNet se o modelo existir, senão Haar) ~6x por segundo.
- Detecta cortes de cena e não "arrasta" a câmera entre planos diferentes.
- Câmera virtual com zona morta + suavização (não treme, só se move quando o rosto sai do quadro).
- Decide o layout: 'track' (1 pessoa), 'split' (2 pessoas lado a lado -> tela dividida),
  'blur' (sem rostos: vídeo inteiro com fundo desfocado).
Gera comandos `sendcmd` para o ffmpeg mover o corte quadro a quadro.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

MODEL = Path(__file__).parent / "models" / "face_detection_yunet_2023mar.onnx"
SAMPLE_FPS = 6
DET_W = 480


@dataclass
class Plan:
    layout: str                      # track | split | blur
    src_w: int = 0
    src_h: int = 0
    crop_w: int = 0                  # largura do corte (track) ou de cada metade (split)
    crop_h: int = 0
    cmds: list[str] = field(default_factory=list)   # linhas sendcmd
    x0: dict = field(default_factory=dict)          # x inicial por crop (a / b)
    y0: dict = field(default_factory=dict)
    faces_ratio: float = 0.0
    shots: int = 1
    extra: dict = field(default_factory=dict)       # layout gamer: retângulos da webcam e do jogo


def _detector(w: int, h: int):
    import cv2
    if MODEL.exists():
        try:
            det = cv2.FaceDetectorYN.create(str(MODEL), "", (w, h), 0.7, 0.3, 50)

            def yunet(img):
                det.setInputSize((img.shape[1], img.shape[0]))
                _, faces = det.detect(img)
                return [] if faces is None else [tuple(map(float, f[:4])) for f in faces]
            return yunet
        except Exception:
            pass
    d = _cascade_dir()
    if d is None:
        return None
    front = cv2.CascadeClassifier(str(d / "haarcascade_frontalface_default.xml"))
    prof = cv2.CascadeClassifier(str(d / "haarcascade_profileface.xml"))
    if front.empty():
        return None

    def haar(img):
        g = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        mn = (int(img.shape[0] * 0.08),) * 2
        fs = list(front.detectMultiScale(g, 1.12, 6, minSize=mn))
        if not fs:
            fs = list(prof.detectMultiScale(g, 1.12, 6, minSize=mn))
        return [tuple(map(float, f)) for f in fs]
    return haar


def _cascade_dir() -> Path | None:
    """Pasta dos arquivos Haar. O OpenCV do Termux não tem `cv2.data`: procura nas pastas do sistema."""
    import cv2
    cands = []
    d = getattr(getattr(cv2, "data", None), "haarcascades", None)
    if d:
        cands.append(Path(d))
    for base in (os.environ.get("PREFIX", ""), "/usr", "/usr/local", "/data/data/com.termux/files/usr"):
        if base:
            cands += [Path(base) / "share/opencv4/haarcascades", Path(base) / "share/opencv/haarcascades"]
    return next((c for c in cands if (c / "haarcascade_frontalface_default.xml").exists()), None)


def analyze(video: Path, start: float, end: float) -> list[dict] | None:
    """Amostras: {t, faces:[(cx, cy, size) normalizados], cut:bool}. None = sem detecção disponível."""
    try:
        return _analyze(video, start, end)
    except Exception as e:  # qualquer problema no OpenCV vira "sem rosto", nunca derruba o clipe
        print(f"[reframe] detecção de rosto indisponível: {e}")
        return None


def _analyze(video: Path, start: float, end: float) -> list[dict] | None:
    try:
        import cv2
        import numpy as np  # noqa: F401
    except ImportError:
        return None
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    step = max(1, round(fps / SAMPLE_FPS))
    detect, prev_hist, out, i = None, None, [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if t > end:
            break
        if i % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            h, w = frame.shape[:2]
            small = cv2.resize(frame, (DET_W, int(DET_W * h / w)))
            if detect is None:
                detect = _detector(small.shape[1], small.shape[0])
                if detect is None:
                    print("[reframe] sem detector de rosto (instale o modelo YuNet ou os arquivos Haar)")
                    return None
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            cut = prev_hist is not None and cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL) < 0.55
            prev_hist = hist

            sw, sh = small.shape[1], small.shape[0]
            faces = [((x + fw / 2) / sw, (y + fh / 2) / sh, fw / sw) for x, y, fw, fh in detect(small)]
            out.append({"t": max(0.0, t - start), "faces": sorted(faces, key=lambda f: -f[2]), "cut": cut})
        i += 1
    cap.release()
    return out


def _camera(points: list[tuple[float, float | None, bool]], dead: float, speed: float,
            big: float = 0.22, confirm: int = 3) -> list[tuple[float, float]]:
    """Câmera virtual 1D. points=(t, alvo|None, corte). Retorna (t, posição) suavizada.

    - zona morta: só se mexe se o rosto sair de ±dead do centro do corte;
    - salto grande (> big) só é seguido se for confirmado em `confirm` detecções seguidas
      (evita "pulos" por detecção falsa — técnica do OpenShorts, ~69% menos vai-e-volta);
    - corte de cena: pula direto, como um editor faria.
    """
    cam, out, last_t, pending = None, [], 0.0, []
    for t, target, cut in points:
        if target is None:
            target = cam if cam is not None else 0.5
        if cam is None or cut:
            cam, pending = target, []
        elif abs(target - cam) > big:
            pending.append(target)
            if len(pending) >= confirm and max(pending[-confirm:]) - min(pending[-confirm:]) < big / 2:
                cam, pending = sum(pending[-confirm:]) / confirm, []   # salto confirmado: corta seco
        else:
            pending = []
            if abs(target - cam) > dead:
                dt = max(t - last_t, 1e-3)
                cam += (target - cam) * min(1.0, speed * dt)
        out.append((t, cam))
        last_t = t
    return out


def _interp(track: list[tuple[float, float]], duration: float, fps: int = 30) -> list[tuple[float, float]]:
    if not track:
        return []
    res, j = [], 0
    n = int(duration * fps) + 1
    for k in range(n):
        t = k / fps
        while j + 1 < len(track) and track[j + 1][0] <= t:
            j += 1
        if j + 1 < len(track) and track[j + 1][0] > track[j][0]:
            (t0, a), (t1, b) = track[j], track[j + 1]
            a_ = a + (b - a) * min(1.0, max(0.0, (t - t0) / (t1 - t0)))
        else:
            a_ = track[j][1]
        res.append((t, a_))
    return res


DISTANCE = {"padrao": 1.0, "longe": 1.45}


def plan(video: Path, start: float, end: float, src_w: int, src_h: int, mode: str = "auto",
         distance: str = "padrao") -> Plan:
    """mode: auto | track | split | blur | center."""
    from .render import H, W
    if mode in ("blur",) or src_h >= src_w or W / H >= src_w / src_h * 0.95:  # já cabe: só encaixa
        return Plan("blur", src_w, src_h)
    samples = analyze(video, start, end) if mode != "center" else None
    dur = end - start
    if not samples:
        if mode == "auto":  # sem como detectar rostos: mostra o quadro inteiro (seguro p/ qualquer vídeo)
            return Plan("blur", src_w, src_h)
        cw = min(src_w, int(src_h * W / H * DISTANCE.get(distance, 1.0))) // 2 * 2
        return Plan("track", src_w, src_h, cw, src_h, [], {"a": (src_w - cw) // 2})

    with_face = [s for s in samples if s["faces"]]
    ratio = len(with_face) / len(samples)
    shots = 1 + sum(s["cut"] for s in samples)
    if mode == "auto" and ratio < 0.25:
        return Plan("blur", src_w, src_h, faces_ratio=ratio, shots=shots)

    # Gameplay com webcam num canto: rosto pequeno e quase sempre no mesmo lugar -> webcam em cima, jogo embaixo
    corner = [s["faces"][0] for s in with_face
              if s["faces"][0][2] < 0.16 and (s["faces"][0][0] < 0.33 or s["faces"][0][0] > 0.67)]
    if mode == "gamer" or (mode == "auto" and len(corner) / len(samples) > 0.5):
        pool = corner or [s["faces"][0] for s in with_face]
        if pool:
            size = _median([f[2] for f in pool])
            p = _gamer_plan(src_w, src_h, _median([f[0] for f in pool]), _median([f[1] for f in pool]),
                            size, ratio, shots)
            # trechos em que a webcam ocupa a TELA INTEIRA (o streamer troca de cena): ali o layout gamer
            # mostraria só a parede em cima e o rosto ampliado embaixo -> nesses segundos, corte normal no rosto
            full = _full_ranges(samples, size, dur)
            if full:
                fw = min(src_w, int(src_h * W / H * DISTANCE.get(distance, 1.0))) // 2 * 2
                p.extra["full"] = [(a, b, _px(cx, src_w, fw)) for a, b, cx in full]
                p.extra["full_w"] = fw
            # trechos SEM rosto nenhum: a faixa de cima mostraria um pedaço ampliado do jogo, e o
            # espectador veria a mesma cena duas vezes. Nesses segundos o jogo ocupa a tela toda.
            sem = _lost_ranges([(s["t"], (s["faces"][0][0] if s["faces"] else None), s["cut"])
                                for s in samples], dur)
            sem = _subtrai(sem, [(a, b) for a, b, _ in full])   # tela cheia da webcam tem prioridade
            if sem:
                p.extra["noface"] = sem
                p.extra["noface_w"] = min(src_w, int(src_h * W / H)) // 2 * 2
            return p

    # Duas pessoas afastadas na maior parte do tempo -> tela dividida
    two = [s for s in samples if len(s["faces"]) >= 2 and abs(s["faces"][0][0] - s["faces"][1][0]) > 0.3
           and s["faces"][1][2] > s["faces"][0][2] * 0.6]
    split = mode == "split" or (mode == "auto" and len(two) / len(samples) > 0.6)

    if split:
        ch = src_h
        cw = min(src_w // 2, int(src_h * W / (H / 2))) // 2 * 2   # metade 1080x960 -> proporção 9:8
        ch = int(cw * (H / 2) / W) // 2 * 2
        left, right = [], []
        for s in samples:
            fs = sorted(s["faces"][:2], key=lambda f: f[0])
            if len(fs) >= 2:
                left.append((s["t"], fs[0][0], s["cut"]))
                right.append((s["t"], fs[1][0], s["cut"]))
            else:
                left.append((s["t"], None, s["cut"]))
                right.append((s["t"], None, s["cut"]))
        p = Plan("split", src_w, src_h, cw, ch, faces_ratio=ratio, shots=shots)
        yc = _median([f[1] for s in samples for f in s["faces"][:2]] or [0.4])
        y = int(min(max(yc * src_h - ch * 0.45, 0), src_h - ch))
        for name, pts in (("a", left), ("b", right)):
            cam = _interp(_camera(pts, 0.06, 2.5), dur)
            p.x0[name] = _px(cam[0][1], src_w, cw)
            p.y0[name] = y
            p.cmds += _cmds(cam, name, src_w, cw)
        return p

    main_size = _median([s["faces"][0][2] for s in with_face]) if with_face else 0
    if mode == "auto" and (main_size < 0.07 or (main_size < 0.11 and ratio < 0.5)):
        # rosto muito pequeno, ou pequeno e que aparece pouco: avatar de jogo ou pessoa ao longe -> tela inteira.
        # Rosto pequeno mas presente quase o tempo todo (palestrante, plano médio) continua sendo seguido.
        return Plan("blur", src_w, src_h, faces_ratio=ratio, shots=shots)
    cw = min(src_w, int(src_h * W / H * DISTANCE.get(distance, 1.0))) // 2 * 2
    # rostos bem menores que o principal (webcam no canto durante o jogo) não puxam a câmera
    pts = [(s["t"], s["faces"][0][0] if s["faces"] and s["faces"][0][2] >= main_size * 0.5 else None, s["cut"])
           for s in samples]
    cam = _interp(_camera(pts, 0.07, 3.0), dur)
    p = Plan("track", src_w, src_h, cw, src_h, faces_ratio=ratio, shots=shots)
    # sem rosto por mais de ~1 s (de costas, de lado, plateia): mostra o quadro inteiro até o rosto voltar,
    # em vez de deixar a câmera parada num braço ou na parede
    wide = _lost_ranges(pts, dur)
    if wide:
        p.extra["wide"] = wide
    p.x0["a"] = _px(cam[0][1], src_w, cw) if cam else (src_w - cw) // 2
    p.cmds = _cmds(cam, "a", src_w, cw)
    return p


def _full_ranges(samples: list[dict], cam_size: float, dur: float,
                 min_len: float = 1.0) -> list[tuple[float, float, float]]:
    """Trechos em que o rosto aparece GRANDE (webcam em tela cheia) num clipe de layout gamer.
    Retorna [(início, fim, centro_x)]. Ignora piscadas da detecção (< min_len) e emenda buracos curtos."""
    big_size = max(0.12, cam_size * 2.2)
    step = 1.0 / SAMPLE_FPS
    labels, last, last_t = [], False, -9.0
    for s in samples:
        if s["faces"]:
            last, last_t = s["faces"][0][2] >= big_size, s["t"]
            labels.append((s["t"], last, s["faces"][0][0] if last else None))
        else:  # sem rosto: mantém o estado anterior por até 1 s (piscada/transição), depois volta ao jogo
            labels.append((s["t"], last and s["t"] - last_t <= 1.0, None))
    runs: list[list] = []
    for t, big, cx in labels:
        if big:
            if runs and t - runs[-1][1] <= 0.6:
                runs[-1][1] = t
                if cx is not None:
                    runs[-1][2].append(cx)
            else:
                runs.append([t, t, [cx] if cx is not None else []])
    out = []
    for a, b, xs in runs:
        b = min(dur, b + step)
        cuts = [s["t"] for s in samples if s["cut"] and a - 0.4 <= s["t"] <= a]  # começa no corte de cena
        a = cuts[0] if cuts else a
        if b - a >= min_len and xs:
            out.append((round(max(0.0, a), 2), round(b, 2), _median(xs)))
    return out


def _subtrai(trechos: list[tuple[float, float]], tirar: list[tuple[float, float]],
             min_len: float = 0.8) -> list[tuple[float, float]]:
    """Tira de `trechos` tudo o que cai dentro de `tirar`; sobras curtas demais são descartadas."""
    out = []
    for a, b in trechos:
        pedacos = [(a, b)]
        for ta, tb in tirar:
            novos = []
            for pa, pb in pedacos:
                if tb <= pa or ta >= pb:
                    novos.append((pa, pb))
                    continue
                if pa < ta:
                    novos.append((pa, ta))
                if tb < pb:
                    novos.append((tb, pb))
            pedacos = novos
        out += [(round(pa, 2), round(pb, 2)) for pa, pb in pedacos if pb - pa >= min_len]
    return out


def _lost_ranges(pts: list[tuple[float, float | None, bool]], dur: float, min_len: float = 1.2,
                 gap: float = 0.8) -> list[tuple[float, float]]:
    """Trechos sem rosto com pelo menos `min_len` s (buracos menores que `gap` s são emendados)."""
    step = 1.0 / SAMPLE_FPS
    runs: list[list[float]] = []
    for t, target, _cut in pts:
        if target is None:
            if runs and t - runs[-1][1] <= gap:
                runs[-1][1] = t
            else:
                runs.append([t, t])
    out = []
    for a, b in runs:
        b = min(dur, b + step)
        if b - a >= min_len:
            out.append((round(a, 2), round(b, 2)))
    return out


GAMER_TOP = 0.30   # fração da altura para a webcam (era 0,36: webcam pequena ampliada demais,
                   # e o jogo, que é o que o público veio ver, ficava apertado)


def _gamer_plan(src_w: int, src_h: int, cx: float, cy: float, size: float, ratio: float, shots: int) -> Plan:
    """Webcam (recortada em volta do rosto) em cima + jogo (corte central) embaixo."""
    from .render import H, W
    top_h = int(H * GAMER_TOP) // 2 * 2
    bot_h = H - top_h
    face_px = size * src_w
    cam_w = min(src_w, int(face_px * 2.8)) // 2 * 2          # rosto + ombros + um pouco do fundo da webcam
    cam_h = min(src_h, int(cam_w * top_h / W)) // 2 * 2
    cam_w = int(cam_h * W / top_h) // 2 * 2
    cam_x = int(min(max(cx * src_w - cam_w / 2, 0), src_w - cam_w))
    cam_y = int(min(max(cy * src_h - cam_h * 0.45, 0), src_h - cam_h))
    game_w = min(src_w, int(src_h * W / bot_h)) // 2 * 2
    game_h = src_h if game_w < src_w else int(src_w * bot_h / W) // 2 * 2
    p = Plan("gamer", src_w, src_h, faces_ratio=ratio, shots=shots)
    # close da reação: a webcam em tela cheia, com o rosto ocupando ~40% da largura (técnica do HAYLIGHTS)
    rw = int(face_px / 0.42)
    rh = int(rw * H / W)
    if rh > src_h:
        rh = src_h
        rw = int(rh * W / H)
    rw, rh = max(2, rw // 2 * 2), max(2, rh // 2 * 2)
    rx = int(min(max(cx * src_w - rw / 2, 0), src_w - rw))
    ry = int(min(max(cy * src_h - rh * 0.38, 0), src_h - rh))
    # O close da reação só vale se couber quase todo dentro da webcam. Numa webcam pequena de canto,
    # esse retângulo 9:16 é um corredor alto que pega mais jogo e parede do que rosto, e ainda é
    # ampliado para a tela toda: o resultado é um borrão que ninguém entende. Melhor não fazer.
    dentro = max(0, min(ry + rh, cam_y + cam_h) - max(ry, cam_y)) / rh
    face_rect = (rx, ry, rw, rh) if dentro >= 0.7 else None
    p.extra = {"cam": (cam_x, cam_y, cam_w, cam_h), "game": ((src_w - game_w) // 2, (src_h - game_h) // 2, game_w, game_h),
               "top_h": top_h, "face_rect": face_rect}
    return p


def _median(v):
    v = sorted(v)
    return v[len(v) // 2]


def _px(center: float, src_w: int, cw: int) -> int:
    return int(min(max(center * src_w - cw / 2, 0), src_w - cw))


def _cmds(cam: list[tuple[float, float]], name: str, src_w: int, cw: int) -> list[str]:
    out, last = [], None
    for t, c in cam:
        x = _px(c, src_w, cw)
        if x != last:
            out.append(f"{t:.3f} crop@{name} x {x};")
            last = x
    return out
