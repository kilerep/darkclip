# Receitas de edição para cortes de gameplay

Baseado em como CapCut, Submagic, OpusClip, Eklipse e auto-editor editam clipes curtos, e em guias de retenção de Shorts de 2026. Leia quando for planejar os efeitos de um clipe.

## Estrutura que prende (gameplay)

1. **0–3 s, gancho:** a coisa mais estranha, engraçada ou tensa do clipe, ou uma pergunta. Se o clipe começa com o jogador andando, apare.
2. **3 s até o clímax, tensão:** algo novo na tela a cada 2–5 s (zoom, texto, troca de cena, corte). Silêncio e espera morrem aqui: acelere (`lento --fator 2`) ou apare.
3. **Clímax/reação:** é o momento do efeito mais forte (zoom + hit, tremor ou quadro congelado). Um só.
4. **Desfecho curto:** 1–3 s depois da reação e acabou. Um final que "emenda" com o começo faz a pessoa assistir de novo (loop), e isso conta muito para o algoritmo.

## Escolhendo o efeito

| Situação | Melhor efeito | Por quê |
|---|---|---|
| Streamer grita / leva susto | `zoom --forca 1.3 --dur 0.8 --som` | aproxima o rosto no pico da emoção |
| Bug bizarro, física quebrada | `congelar` + texto ("COMO??") | dá tempo para o público entender o absurdo |
| Algo dá muito errado (explosão, morte) | `tremor --dur 0.5 --som` | imita o impacto |
| Jogada perfeita | `lento --fator 0.5 --dur 1.5` | deixa saborear |
| Carregando, andando, menu | `lento --fator 2` (acelerado) ou `aparar` | corta a espera |
| Piada falada | `texto --pos topo` com a palavra-chave | reforça para quem está sem som |
| Antes de um desastre | `congelar` com "ELE NÃO SABIA…" / "ELE NÃO VIU 💀" | cria expectativa (meme clássico) |
| Comentário sarcástico | `texto` curto + `som --tipo hit` | marca o timing da piada |

## Intensidade

- `zoom --forca`: 1.15 sutil (conversa), 1.25 padrão, 1.4+ exagerado (meme). Use `--foco 0.2` se o rosto/ação estiver no alto da tela (webcam no layout gamer) e `--foco 0.6` se estiver embaixo.
- `tremor --forca`: 10–15 leve, 18–25 padrão, 30–40 só em explosões.
- Texto: 1 a 4 palavras, MAIÚSCULAS, 1–2 s na tela. Amarelo ou branco para piada, vermelho para perigo/susto.
- Som: `hit` em impacto/reação/texto que entra, `whoosh` em transições e trocas de cena. O DarkClip já põe whoosh nos jump cuts; não exagere.

## O que não fazer

- Efeito em todo segundo: com mais de 1 efeito forte a cada ~4 s, o clipe fica cansativo.
- Zoom e tremor no mesmo instante: escolha um.
- Texto por cima da legenda ou do rosto.
- Câmera lenta em fala: a voz fica grave e estranha. Use só em ação sem fala.
- Música com direitos autorais: o DarkClip só usa efeitos gerados por código, sem risco de direitos.

## Ordem segura dos comandos

1. `aparar` (define o tamanho final)
2. efeitos que **não mudam a duração**: `zoom`, `tremor`, `texto`, `som`
3. efeitos que **mudam a duração**, do fim para o começo: `congelar`, `lento`

## Referências estudadas

- auto-editor (WyattBlue): corte por volume do áudio com margem; inspirou os jump cuts do DarkClip.
- OpenCut / ShortsStudio: transições com xfade, efeitos sonoros procedurais e predefinições 9:16.
- OpenShorts (mutonby): texto de gancho gerado por IA e filtros ffmpeg montados pelo Gemini.
- Submagic e Eklipse para gaming: zoom automático no pico e corte de tempo morto na mesma passada.
- OpusClip (13,5 mi clipes analisados): legenda grande, gancho nos 3 s, troca visual frequente.
