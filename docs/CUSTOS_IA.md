# IAs que leem, ouvem e veem vídeos: comparação de custos (nov/2026)

> Preços mudam com frequência e várias fontes são blogs que divergem entre si. **Confira na página oficial antes de assinar.** "Custo/hora" = estimativa para analisar **1 hora de vídeo** com resposta de ~3 mil tokens.

## 1. Quem faz o quê

| IA | 👁️ Vê | 👂 Ouve | 📖 Lê (texto na tela) | Vídeo direto? | Observação |
|---|---|---|---|---|---|
| **Google Gemini** (3.x / 4) | ✅ 1 quadro/s | ✅ áudio nativo | ✅ | ✅ arquivo ou **link do YouTube** | Mais madura para vídeo; modo *agentic* em vídeo longo |
| **OpenAI GPT-5.4 / 5.5** | ✅ | ✅ | ✅ | ✅ desde mar–abr/2026 | Vídeo nativo nas versões novas ([Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/gemini-gpt5-claude-opus-4-closed-frontier-2026)) |
| **Anthropic Claude** (Opus/Sonnet/Haiku 5.5) | ✅ por **quadros** | ❌ (precisa da transcrição) | ✅ | ❌ só imagens | Excelente para decidir e escrever; o DarkClip manda quadros + fala |
| **Twelve Labs** (Pegasus/Marengo) | ✅ | ✅ | ✅ | ✅ | Especialista em vídeo: busca "ache todos os momentos de X" numa biblioteca |
| **Amazon Nova** (Bedrock) | ✅ 1 quadro/s | — | ✅ | ✅ até 1 GB (S3) | ~276 mil tokens para 16 min ([AWS](https://docs.aws.amazon.com/nova/latest/userguide/modalities-video.html)) |
| **Qwen3-Omni** (aberto, no seu PC) | ✅ | ✅ | ✅ | ✅ | Grátis, mas pede GPU grande; o Ollama padrão não roda o vídeo/áudio dele ([GitHub](https://github.com/QwenLM/Qwen3-Omni)) |

## 2. Quanto custa analisar 1 hora de vídeo

| Opção | Preço (US$ por 1 mi tokens: entrada / saída) | **Custo por hora de vídeo** | Grátis? |
|---|---|---|---|
| **Gemini por link do YouTube** | — | **US$ 0** (prévia "sem custo", até 8 h/dia no plano grátis) | ✅ |
| Gemini 2.5 Flash-Lite | 0,10 / 0,40 | ≈ US$ 0,04 | descontinuado: vira 3.5 Flash-Lite em 01/12/2026 |
| **Gemini 3.5 Flash-Lite** | 0,30 / 2,50 | **≈ US$ 0,12** | cota grátis |
| Gemini 3.8 Flash | 0,75 / 3,75 (dobra em 2027) | ≈ US$ 0,28 (≈ 0,55 em 2027) | cota grátis |
| Gemini 4 Hydrogen (padrão do DarkClip) | 1,50 / 7,50 | ≈ US$ 0,56 | cota grátis |
| GPT-5.4 nano / mini | 0,20 / 1,25 · 0,75 / 4,50 | não verificado* | — |
| GPT-5.5 | 5,00 / 30,00 | não verificado* (por analogia ao Gemini, ≈ US$ 1,90) | — |
| **Claude Haiku 5.5** (quadros + fala) | 0,10 / 0,50 | **≈ US$ 0,005** | — |
| Claude Sonnet 5.5 (quadros + fala) | 2,00 / 10,00 | ≈ US$ 0,10 | — |
| Claude Opus 5.5 (quadros + fala) | 4,00 / 20,00 | ≈ US$ 0,20 | — |
| Twelve Labs Pegasus (analisar) | US$ 0,0292/min | ≈ US$ 1,75 (+ US$ 2,52 se indexar para busca) | 600 min grátis |
| Qwen3-Omni no seu PC | — | só a energia | ✅ (precisa de ~16–20 GB de VRAM quantizado, não verificado) |

\* As fontes não publicam quantos tokens a OpenAI conta por segundo de vídeo; o custo real só se sabe testando.

**Como calculei:**
- **Gemini:** cerca de 100 tokens por segundo de vídeo em resolução baixa, o que dá cerca de 360 mil tokens por hora ([docs do Gemini](https://ai.google.dev/gemini-api/docs/video-understanding)). O modo *agentic* promete até 88% menos tokens em vídeo longo; é afirmação do Google, não verificada.
- **Claude:** cerca de 100 quadros de 512 px (≈ 20 mil tokens) mais a transcrição de 1 h (≈ 15 mil tokens). Ele vê 1 quadro a cada ~36 s, contra 1 por segundo no Gemini: **menos detalhe visual, custo muito baixo.**

## 3. Ouvir (transcrição de 1 hora)

| Opção | Custo por hora |
|---|---|
| Legenda do YouTube / faster-whisper no PC (o DarkClip já usa) | **grátis** |
| Groq Whisper Large v3 Turbo | ≈ US$ 0,02–0,04 |
| AssemblyAI Universal-2 | US$ 0,15 |
| OpenAI gpt-4o-mini-transcribe | ≈ US$ 0,18 |
| Deepgram Nova-3 (lote) | ≈ US$ 0,26 |
| Gemini 3.5 Transcribe | US$ 0,30 |
| OpenAI Whisper / gpt-4o-transcribe | US$ 0,36 |

Fontes: [Fora Soft](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/real-cost-of-ai-in-video-products-gemini-openai-pricing), [AssemblyAI](https://assemblyai.com/blog/speech-to-text-api-pricing), [comparativo dev.to](https://dev.to/eli_9c82b7dfe52c1bc371ffe/ai-transcription-pricing-2026-whisper-vs-deepgram-vs-assemblyai-2eec).

## 4. Quanto custa um vídeo no DarkClip (ex.: vídeo de 20 min do YouTube, 6 cortes)

| Modo | O que usa | Custo por vídeo |
|---|---|---|
| **Grátis** | Legenda + 🔥 heatmap + 💬 comentários + ⚡ áudio + regras automáticas | **US$ 0** |
| **Econômico** | + Gemini pelo link (grátis) + Claude **Haiku 5.5** para decidir | **≈ US$ 0,01** |
| **Recomendado** | + Gemini pelo link (grátis) + Claude **Opus 5.5** (padrão) para decidir e escrever | **≈ US$ 0,12** (≈ R$ 0,70) |
| Arquivo/TikTok (sem link do YouTube) | Gemini 3.5 Flash-Lite (≈ US$ 0,04) + Claude Opus 5.5 | ≈ US$ 0,16 (≈ R$ 0,90) |
| Offline total | faster-whisper + Ollama + regras | US$ 0 (usa o seu PC) |

**Comparação:** o SmartClips custa R$ 47,90 por semestre. O OpusClip Pro custa US$ 29/mês por 300 minutos, ≈ US$ 5,80 por hora de vídeo, segundo terceiros.

O DarkClip agora **mostra o custo real** (pelos tokens que a API informa) no fim de cada tarefa: "💰 Custo de IA: US$ 0,08".

## 5. A estratégia do DarkClip (funil: do grátis ao pago)
1. **Sinais grátis primeiro:** legenda, heatmap, comentários, chat, energia do áudio.
2. **Gemini assiste** (vê + ouve), de graça por link do YouTube; nos outros casos, o modelo barato.
3. **Claude decide e escreve** em cima de texto e sinais. São poucos tokens, então sai barato mesmo no Opus.
4. **Claude por quadros** só quando não há Gemini (ou na skill `/assistir-video`, sem custo de API).

### Como trocar os modelos (no `.env`)
```
DARKCLIP_GEMINI_MODEL=gemini-3.5-flash-lite   # mais barato que o padrão gemini-4-hydrogen
DARKCLIP_MODEL=claude-haiku-5-5               # modo econômico (padrão: claude-opus-5-5, melhor qualidade)
DARKCLIP_VISION=gemini                        # auto | gemini | claude | off
```
