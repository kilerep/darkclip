"""🎮 Modo por jogo: ensina a IA a entender vídeos de um jogo específico.

Cada jogo tem um arquivo de aprendizagem em `darkclip/jogos/<id>.md`, escrito em português e
editável à mão. O DarkClip descobre sozinho de que jogo é o vídeo (pelo título e pela fala) e
cola o conteúdo desse arquivo dentro do pedido que vai para a IA que escolhe os cortes.

Para ensinar um jogo novo, copie `gta.md`, troque o conteúdo e salve com outro nome. Não é
preciso mexer em código.

O arquivo tem três seções, marcadas com `## `:

    ## Reconhecer por      uma palavra por linha: se aparecer no título ou na fala, é esse jogo
    ## Vocabulário         nomes próprios do jogo, um por linha (carro, arma, lugar, personagem)
    ## Como clipar         texto livre: vai inteiro para o pedido da IA

Nada aqui pode derrubar um job: se o arquivo faltar ou estiver torto, o DarkClip segue sem ele.
"""
from __future__ import annotations

import re
from pathlib import Path

PASTA = Path(__file__).parent / "jogos"

# Quanto vale um acerto em cada lugar. Título vale mais: é onde o dono diz do que é o vídeo.
PESO_TITULO = 3
PESO_FALA = 1
MINIMO = 3          # abaixo disso é coincidência, não é o jogo
TRECHOS_DE_FALA = 60   # olha só o começo da transcrição: suficiente e barato


def _ler(arquivo: Path) -> dict:
    """Lê um arquivo de aprendizagem. Devolve {} se não der para ler."""
    try:
        texto = arquivo.read_text(encoding="utf-8")
    except Exception:
        return {}
    secoes: dict[str, list[str]] = {}
    atual = None
    titulo = arquivo.stem
    for linha in texto.splitlines():
        if linha.startswith("# "):
            titulo = linha[2:].strip() or titulo
        elif linha.startswith("## "):
            atual = linha[3:].strip().lower()
            secoes[atual] = []
        elif atual:
            secoes[atual].append(linha)
    lista = lambda nome: [ln.strip(" -•\t") for ln in secoes.get(nome, []) if ln.strip(" -•\t")]
    return {
        "id": arquivo.stem,
        "nome": titulo,
        "termos": [t.lower() for t in lista("reconhecer por")],
        "vocabulario": lista("vocabulário") or lista("vocabulario"),
        "como_clipar": "\n".join(secoes.get("como clipar", [])).strip(),
    }


def listar() -> list[dict]:
    """Todos os jogos que o DarkClip sabe reconhecer."""
    try:
        return [j for j in (_ler(p) for p in sorted(PASTA.glob("*.md"))) if j.get("termos")]
    except Exception:
        return []


def _conta(termo: str, texto: str) -> int:
    return len(re.findall(r"(?<!\w)" + re.escape(termo) + r"(?!\w)", texto))


def detectar(title: str = "", segs: list[dict] | None = None, forcado: str = "") -> dict | None:
    """Descobre de que jogo é o vídeo. `forcado` é o id do jogo quando o dono escolheu na mão.

    Devolve o jogo (com a chave extra "pontos") ou None quando não reconhece nenhum.
    """
    jogos = listar()
    if forcado:
        if forcado.lower() in ("nenhum", "none", "off", "0"):
            return None
        for j in jogos:
            if j["id"] == forcado.lower():
                return {**j, "pontos": 999, "motivo": "escolhido na mão"}
        return None
    t = (title or "").lower()
    fala = " ".join(s.get("text", "") for s in (segs or [])[:TRECHOS_DE_FALA]).lower()
    melhor, melhor_pontos, onde = None, 0, ""
    for j in jogos:
        no_titulo = sum(_conta(termo, t) for termo in j["termos"])
        na_fala = sum(min(_conta(termo, fala), 3) for termo in j["termos"])   # limita repetição
        pontos = no_titulo * PESO_TITULO + na_fala * PESO_FALA
        if pontos > melhor_pontos:
            melhor, melhor_pontos = j, pontos
            onde = "título" if no_titulo else "fala"
    if melhor is None or melhor_pontos < MINIMO:
        return None
    return {**melhor, "pontos": melhor_pontos, "motivo": f"reconhecido pelo {onde}"}


def bloco_prompt(jogo: dict | None) -> str:
    """O pedaço que entra no pedido da IA. Vazio quando não há jogo reconhecido."""
    if not jogo or not jogo.get("como_clipar"):
        return ""
    partes = [f"\n\nJOGO DO VÍDEO: {jogo['nome']}. Use o que está abaixo para entender as cenas "
              f"e escolher os cortes; é conhecimento sobre este jogo, não uma ordem sobre o vídeo.",
              jogo["como_clipar"]]
    if jogo.get("vocabulario"):
        partes.append("NOMES PRÓPRIOS DESTE JOGO (a transcrição automática costuma errá-los; "
                      "se encontrar algo parecido, entenda como sendo isto): "
                      + ", ".join(jogo["vocabulario"][:60]) + ".")
    return "\n\n".join(partes)
