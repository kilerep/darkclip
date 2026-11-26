---
name: assistir-video
description: Faz o Claude "assistir" a um vídeo (YouTube, TikTok, Instagram, Facebook, Kwai ou arquivo) extraindo quadros-chave e a fala de cada trecho, para entender o que acontece, analisar o gancho e apontar os melhores momentos para cortes. Use quando o usuário pedir para ver, assistir, analisar, resumir ou entender um vídeo, ou para estudar por que um vídeo viralizou.
---

# /assistir-video

O Claude não recebe vídeo direto, só imagens. Esta skill transforma o vídeo em **quadros-chave + fala alinhada**, e você (o Claude Code) lê as imagens para entender o que acontece. **Não precisa de chave de API.**

## 1. Preparar o vídeo

Na raiz do projeto DarkClip:

```bash
python -m darkclip.vision "<link ou caminho do vídeo>" --quadros 60
```

- Baixa o vídeo em até 480p, pega a legenda (ou transcreve com faster-whisper, se instalado) e tira quadros nas **mudanças de cena** e a cada N segundos.
- Vídeo curto (até 90 s): use `--quadros 30`. Vídeo longo: 60–100. Para focar num trecho, corte o arquivo antes com ffmpeg ou peça ao usuário o intervalo.
- No fim aparece o caminho do `INDICE.md`.

## 2. Assistir

1. Leia o `INDICE.md` (ferramenta Read).
2. Leia **cada imagem listada**, na ordem. Leia várias em paralelo para ganhar tempo.
3. Para cada quadro, combine **o que se vê** (pessoas, expressões, ação, texto na tela, cenário, cortes) com **a fala** daquele trecho.
4. Não invente o que não está nos quadros nem na fala. Entre dois quadros pode ter acontecido algo que você não viu; diga isso quando importar.

## 3. Responder

Adapte ao pedido do usuário. Para análise completa, use este formato (em português simples):

- **Resumo** em 3–5 frases.
- **Gancho:** o que acontece nos primeiros 3 segundos e se prende ou não (e por quê).
- **Linha do tempo:** `MM:SS` + o que acontece, só os pontos importantes.
- **Melhores momentos para cortes:** tabela `Trecho | Nota 0–100 | O que acontece | Gancho sugerido`. Cada trecho de 20–60 s, começando forte e terminando no desfecho.
- **Por que funciona / o que copiar:** formato, ritmo, legendas, enquadramento.
- **Riscos:** música com direitos, marca d'água de outra rede, pessoas identificáveis, conteúdo sensível.

## Alternativa com API (sem o Claude Code)

`python -m darkclip.vision "<link>" --api` envia os quadros direto para a API do Claude (precisa de `ANTHROPIC_API_KEY`) e salva `analise.md`. O app do DarkClip usa essa função no modo **🔍 Analisar vídeo**, e no pipeline de cortes ela entra como sinal 👁️ quando não há chave do Gemini.

## Problemas comuns
- `Sign in to confirm you're not a bot` / 429: o YouTube bloqueou o download. Rode no PC/celular (IP residencial), atualize o yt-dlp ou use `DARKCLIP_COOKIES`.
- Sem legenda e sem faster-whisper: a análise segue só com as imagens. Avise o usuário que a fala não foi considerada.
