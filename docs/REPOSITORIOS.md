# Repositórios estudados e o que o DarkClip aprendeu (nov/2026)

Os quatro primeiros foram clonados e o código foi lido (só leitura). Nenhum código foi copiado: as técnicas foram reescritas no DarkClip, com crédito nos comentários.

| Repositório | Licença | O que faz | O que veio para o DarkClip |
|---|---|---|---|
| [PIGJET/autoclipnew](https://github.com/PIGJET/autoclipnew) (ClipForge) | sem licença declarada (só a ideia) | Acha destaques de VODs com chat, heatmap, comentários e áudio, sem baixar o vídeo | **Transcrever só os trechos promissores** em vídeos longos sem legenda (`whisper_windows`); **picos de áudio sustentados** por z-score em blocos de 15 s (`audio_peaks`); **bônus quando sinais diferentes concordam** (`blend_score`) |
| [Rohi56u/VoXCluTcH](https://github.com/Rohi56u/VoXCluTcH) | MIT | Radar de momentos em lives da Twitch: chat + energia do áudio | **Áudio relativo ao entorno** (pico vs. mediana de ±45 s) no `energy_score`. Ideia futura: nota do chat = 45% velocidade + 35% diversidade de quem fala + 20% reações |
| [WyattBlue/auto-editor](https://github.com/wyattblue/auto-editor) | domínio público | Corta silêncio pelo áudio (limiar, margem de 0,2 s, corte mínimo) | **Corte de silêncio pelo áudio real** (`audio_active`), cruzado com o corte pela fala |
| [Chamanrajragu/purffle-shorts](https://github.com/Chamanrajragu/purffle-shorts) | MIT | Gerador de Shorts sem rosto | **Efeitos sonoros gerados por código** (`sfx.py`): whoosh nos cortes e impacto no gancho |
| [mutonby/openshorts](https://github.com/mutonby/openshorts) | MIT | Clipador completo | (já aplicado antes) câmera com salto confirmado, zoom por corte, regra "recue o início" |
| [ColinGPT9/clips-studio](https://github.com/ColinGPT9/clips-studio) | AGPL-3.0 | Clipador de lives | (já aplicado antes) peso maior para visual e áudio em trecho com pouca fala |

## Outros projetos encontrados (para estudar depois)
- [jekku0966/HighlightMiner](https://github.com/jekku0966/HighlightMiner) (MIT): destaques de VOD por áudio + Whisper + chat.
- [bendawg2010/Auto-clipper](https://github.com/bendawg2010/Auto-clipper): detecção por YOLO e pixels, específica por jogo, e clipe por voz ("clip it").
- [Junhua-Liao/Light-ASD](https://github.com/Junhua-Liao/Light-ASD): **detecção de quem está falando**, leve (1 milhão de parâmetros), ótima para podcasts com 2 pessoas.
- [EverythingAI-Pro/ai-video-editor](https://github.com/EverythingAI-Pro/ai-video-editor): corta muletas ("ãh", "tipo") e põe B-roll.
- [NaufalRizqullah/opensource-clipping](https://github.com/NaufalRizqullah/opensource-clipping): estúdio web com tela dividida, B-roll e postagem no YouTube e Facebook.
- [shubhxtech/AutoShorts](https://github.com/shubhxtech/AutoShorts) (MIT): 100% local, com ganchos, zooms e B-roll.

## Próximas melhorias sugeridas (em ordem de valor)
1. **Quem está falando** (Light-ASD) nos podcasts: hoje a câmera segue o maior rosto.
2. **Chat das lives com diversidade de quem fala** (VoXCluTcH), para não cair em spam ou chuva de emotes.
3. **Emojis nas palavras-chave** (Twemoji, CC-BY) acima da legenda.
4. **Cortar muletas** ("ãh", "éé", "hum") pela transcrição palavra a palavra.
