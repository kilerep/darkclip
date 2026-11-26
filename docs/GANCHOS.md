# 🎣 Ganchos e finais: como o DarkClip prende quem assiste

**Gancho** é o que acontece nos primeiros 1 a 3 segundos e decide se a pessoa fica ou arrasta para o próximo. **Final** é como o vídeo termina; um bom final faz a pessoa assistir de novo.

## Os tipos de gancho

| Tipo | O que é | Quando usar | Exemplo de texto |
|---|---|---|---|
| ⏩ **Prévia** (flash-forward) | Abre com 2–3 s do momento mais forte, flash branco, som de rebobinar e volta ao começo | O desfecho é forte e está no fim: explosão, falha, susto, reação | "COMO ELE CHEGOU NISSO?" |
| ❓ **Pergunta** | Uma pergunta que só o vídeo responde (lacuna de curiosidade) | O trecho responde algo curioso | "VAI DAR CERTO?" |
| ⏳ **Espera até o fim** | Promete que o melhor vem depois | A graça está no final e o começo é mais calmo | "ESPERA O FINAL…" |
| 😱 **Afirmação chocante** | Conta o absurdo numa frase | Aconteceu algo que dá para resumir | "DEU TUDO ERRADO" |
| 🎬 **POV / situação** | Uma situação com que o público se identifica | Cenas do dia a dia, humor | "POV: VOCÊ TENTANDO AJUDAR" |
| 🎮 **Começa na ação** | Sem texto; o corte já abre agitado | O trecho começa no meio da ação | (sem texto) |

## Os finais

| Final | O que faz |
|---|---|
| 🔁 **Loop** | No último meio segundo, o vídeo se dissolve no **primeiro quadro**. Quando a rede recomeça, o último quadro é igual ao primeiro: o replay parece continuação |
| ⏹️ **Normal** | Termina no desfecho |
| 🤖 **Automático** | Usa o loop quando a IA diz que a última frase emenda bem na primeira |

## Como o DarkClip escolhe (modo Automático)
1. **Com IA (Claude ou Gemini):** a IA conhece os tipos acima. Para cada corte, ela escolhe o tipo, escreve o texto, aponta o momento mais forte para a prévia e diz se o loop funciona. Ela varia os tipos entre os cortes.
2. **Sem IA (regras automáticas):** o DarkClip procura, na parte final do corte, a janela de som mais forte comparada ao **próprio corte**, como grito, explosão ou risada. Se ela se destaca uns 3 dB e o corte tem 25 s ou mais, usa a **Prévia**. Se não, mantém o gancho de texto.
3. **Se você pediu Prévia, mas não há momento forte:** o sistema troca para **Espera até o fim**.
4. **Se você escreveu o texto do gancho** no ✏️ Editar, o seu texto vence.

## Onde mexer
- **Aba ✂️ Clipar → 🎣 Gancho e Final:** vale para o trabalho inteiro (o app lembra a escolha).
- **✏️ Editar** em cada corte: muda o gancho e o final só daquele corte.
- **Selos no corte:** ⏩ prévia, ❓ pergunta, ⏳ espera o fim, 😱 chocante, 🎬 POV, 🎮 ação, 🔁 loop.
- **Pelo Claude (MCP):** `cortar_video` aceita `gancho` e `final`; `editar_corte` aceita `tipo_gancho` e `final`.

## O que a pesquisa diz (e o que é só opinião de blog)
- Quase todas as fontes colocam o gancho no **primeiro 1 a 3 segundos**, e recomendam texto grande na tela, porque muita gente assiste sem som.
- **Abrir com o resultado e explicar depois** ("faz primeiro, explica depois") é um padrão citado para prender.
- **Micro-ganchos** a cada 10–15 s ajudam a segurar a pessoa até o fim. O DarkClip já faz parte disso com zoom, cortes e efeitos.
- **Loop:** desde 31/03/2025, o YouTube conta replays de Shorts como visualizações, mas não como "visualizações engajadas", e o loop não ajuda a bater as horas do Programa de Parcerias. Blogs dizem que o algoritmo gosta de replays; **não achei confirmação oficial**.
- Os números de "retenção ideal" que aparecem nos blogs são de empresas que vendem ferramentas: use o **YouTube Studio → Retenção do público** dos seus próprios vídeos para saber o que funciona no seu canal.

Fontes: [CapCut: padrões dos 3 primeiros segundos](https://www.capcut.com/create/short-form-video-hooks-first-3-second-patterns) · [CapCut: loops sem emenda](https://www.capcut.com/create/seamless-loop-videos-continuity-techniques) · [vidIQ: looping de Shorts](https://vidiq.com/blog/post/double-youtube-watch-time-looping-shorts) · [vidIQ: ganchos para Shorts](https://vidiq.com/blog/post/viral-video-hooks-youtube-shorts/) · [OpusClip: fórmulas de gancho](https://www.opus.pro/blog/youtube-shorts-hook-formulas) · [Social Media Examiner: curiosidade e loops](https://www.socialmediaexaminer.com/youtube-shorts-hooks-and-curiosity-loops-that-explode-your-views/) · [captions.ai: ganchos](https://captions.ai/blog/video-hooks-how-to-write-a-scroll-stopping-opening) · [Buffer: anatomia de um gancho](https://buffer.com/resources/good-hooks/) · [Terra Market Group: aberturas testadas](https://www.terramarketgroup.com/blog/short-form-video-retention-hooks-2026-30-tested-opening-patterns-for-reels-tiktok-and-shorts) · [JML: gancho nos 3 primeiros segundos](https://www.jmltechstudios.com/blog/video-hooks-first-3-seconds)
