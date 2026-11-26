"""Narração grátis com edge-tts (vozes neurais da Microsoft) + tempo por palavra."""
from __future__ import annotations

import asyncio
from pathlib import Path

VOICES = {
    "pt-BR-AntonioNeural": "Antônio (grave, masculino)",
    "pt-BR-FranciscaNeural": "Francisca (feminina)",
    "pt-BR-ThalitaMultilingualNeural": "Thalita (feminina, multilíngue)",
    "pt-PT-DuarteNeural": "Duarte (Portugal)",
    "en-US-ChristopherNeural": "Christopher (EN, grave)",
}


async def _synth(text: str, voice: str, rate: str, pitch: str, mp3: Path) -> list[dict]:
    import edge_tts
    com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    words = []
    with mp3.open("wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 10_000_000
                words.append({"start": s, "end": s + chunk["duration"] / 10_000_000, "word": chunk["text"]})
    return words


def narrate(text: str, out: Path, voice: str = "pt-BR-AntonioNeural",
            rate: str = "+8%", pitch: str = "-4Hz") -> tuple[Path, list[dict]]:
    """Gera MP3 e lista de palavras com tempos. Voz levemente grave e rápida = tom 'dark'."""
    out.parent.mkdir(parents=True, exist_ok=True)
    words = asyncio.run(_synth(text, voice, rate, pitch, out))
    if not words:  # sem eventos de palavra: distribui pelo tempo do áudio
        from .download import probe_duration
        toks = text.split()
        d = probe_duration(out) / max(len(toks), 1)
        words = [{"start": i * d, "end": (i + 1) * d, "word": t} for i, t in enumerate(toks)]
    # Reanexa pontuação que o TTS remove, para a legenda ficar natural
    return out, words
