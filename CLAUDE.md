# DarkClip — guia para o Claude Code

Fábrica de cortes (Shorts/Reels/TikTok/Kwai/Facebook) com IA, em português do Brasil. O dono do projeto é iniciante em programação: explique as mudanças em linguagem simples e prefira passos pequenos, testados e reversíveis.

## Como rodar
- Instalar: `install_windows.bat` (Windows) ou `./install.sh` (Linux/Mac). No Android, use o Termux: `install_termux.sh`.
- Servidor + app: `start_windows.bat` ou `./start.sh`. O app abre em http://127.0.0.1:8787; o celular usa o endereço com `?token=` que aparece no terminal.
- Diagnóstico: `python -m darkclip.doctor` (Windows: `verificar_windows.bat`) — peça o print ao usuário quando algo falhar.
- Linha de comando: `python -m darkclip.cli clip <link|--file video.mp4> [-n 5] [--aspect 9:16] [--de 1:00:00 --ate 2:00:00 --partes 15]`
- Ferramentas avulsas: `python -m darkclip.cli clip --file v.mp4 --ferramenta legendar|silencios`
- Comentários: `python -m darkclip.comments <link>` (também existe a skill `/analisar-comentarios`).
- Conversar com o Gemini (assiste vídeos inteiros, segunda opinião): `python -m darkclip.consultar "pergunta" [--video LINK] [--arquivo x]` + skill `/consultar-gemini` (registro em `docs/CONVERSAS_GEMINI.md`).
- Estudo de edição de vídeos de referência: `python -m darkclip.estudo LINK` + skill `/estudar-edicao` (padrão vai para `docs/ESTUDO_EDICAO.md`).
- Edição fina de um clipe pronto (zoom, tremor, câmera lenta, quadro congelado, texto, som): skill `/editar-video` (`.claude/skills/editar-video/scripts/editar.py`).
- Não há suíte de testes formal. Para validar, rode a CLI num vídeo curto e confira os quadros com `ffmpeg -ss 3 -i clip_01.mp4 -frames:v 1 x.png`.

## Arquitetura (pasta `darkclip/`)
| Arquivo | Papel |
|---|---|
| `pipeline.py` | Orquestra os jobs (`clip`, `story`, `legendar`, `silencios`, `rerender`), o intervalo De/Até e as partes |
| `download.py` | yt-dlp: modo inteligente (só legenda + heatmap → só os trechos), uma única legenda por vídeo (evita 429), plano B com download completo |
| `transcribe.py` | VTT → palavras com tempo (`timed` False = legenda por frase); fallback para faster-whisper (`DARKCLIP_WHISPER_MODEL`); `estimate_offset` mede o atraso da legenda e `whisper_words` dá a fala exata de cada corte (pipeline `_sync_subs`/`_caption_words`, desligáveis com `DARKCLIP_SUBS_SYNC=0`/`DARKCLIP_CAPTION_WHISPER=0`) |
| `signals.py` | Heatmap "Mais repetidos", energia do áudio, marcadores 🔥💬👁️⚡😂, nota final ponderada |
| `comments.py` | Comentários (timestamps, frases citadas, reações) e chat de lives → curva de atenção |
| `gemini.py` | Gemini assiste o vídeo (Interactions API, modo agentic em vídeo longo, JSON estruturado), só com stdlib |
| `ai.py` | Seleção dos trechos: Claude → Ollama (offline) → Gemini lendo a transcrição → momentos do Gemini → regras automáticas (com recuo de contexto); notas Gancho/Fluxo/Valor/Tendência |
| `reframe.py` | Detecção de rosto (YuNet incluído em `models/`, Haar de reserva), câmera virtual (zona morta, salto confirmado em 3 detecções), quadro inteiro quando o rosto some >1,2 s, tela dividida, layout gamer que troca para rosto em tela cheia quando a webcam ocupa a tela |
| `render.py` | ffmpeg: formatos 9:16/4:5/1:1/original, distância da câmera, jump cuts, zoom, legendas ASS, gancho, barra de progresso |
| `central.py` | 📅 Central do Canal: calendário, números do canal via yt-dlp, aprendizado com as views reais, agendador de posts automáticos |
| `vision.py` | Claude "assiste" vídeos: quadros-chave + fala → análise (API) ou pasta para a skill `/assistir-video` |
| `sfx.py` | 🔊 Efeitos sonoros gerados por código (whoosh nos cortes, impacto no gancho) |
| `doctor.py` | 🩺 Diagnóstico da instalação |
| `costs.py` | 💰 Medidor de custo: soma os tokens reais de Claude/Gemini por tarefa (tabela de preços aqui) |
| `trends.py` | 💡 Google Trends do Brasil → ideias de vídeo para o nicho |
| `social.py` | Contas e postagem: Facebook Reels/vídeo, Instagram Reels (upload resumível), YouTube (OAuth app de computador) |
| `server.py` + `web/index.html` | API FastAPI + app PWA (celular e janela de app no PC) |
| `hooks.py` | 🎣 Tipos de gancho (prévia/flash-forward, pergunta, espera, chocante, POV, ação) e finais (loop); regras para o prompt; `decide()` escolhe por corte; prévia pelo pico de som relativo ao corte. `render._add_teaser`/`_make_loop` montam o vídeo |
| `reacoes.py` | 😂 Momentos de reação (pico de som ≥ +5 dB sobre o próprio corte, risada na fala) → `render_clip(reactions=…)`: zoom no rosto (track/blur) ou webcam em tela cheia (gamer). Figurinhas existem no código mas ficam desligadas (`stickers=False`, o dono preferiu sem) |
| `templates.py` | 🎨 Modelos visuais (cartão sobre fundo desfocado/cor/degradê/imagem, título fixo, @ do canal), prévias e modelo por rede; `render_clip(template=…)` monta o cartão antes da legenda |
| `feedback.py` | 👍/👎 do dono em cada corte (`data/feedback.json`): vira exemplos no prompt e ajusta o recuo de contexto |
| `mcp_server.py` | Servidor MCP (stdio, só stdlib): o Claude usa o DarkClip aberto pela API local (`registrar_claude_windows.bat`) |

## Regras do projeto
- **Nada pode derrubar o job inteiro por causa de um sinal opcional** (comentários, Gemini, rosto, chat): use try/except, registre com `job.step(...)` e siga em frente.
- **Corte nunca termina antes do desfecho.** Se faltar contexto, recue o início (regra do prompt + `_extend_to_payoff`).
- Toda chamada de IA aceita ficar sem chave: o sistema precisa funcionar só com as regras automáticas.
- Modelos padrão: Claude `claude-opus-5-5` (`DARKCLIP_MODEL`), Gemini `gemini-4-hydrogen` (`DARKCLIP_GEMINI_MODEL`), com reservas em `DARKCLIP_GEMINI_FALLBACKS` quando o Google responde 503. Não troque de modelo sem pedido do usuário.
- Mensagens para o usuário (`job.step`, erros, UI) em **português simples**, dizendo o que fazer.
- Nunca grave chaves no código: tudo vem do `.env` (veja `.env.example`).
- Registros e arquivos de job passam por `config.redact()`: nunca grave chave ou token em log. O `data/contas.json` guarda tokens de propósito e não é mascarado.
- `data/` é local (jobs, uploads, central.json) e fica fora do git.

## Pesquisa de referência
`docs/REPOSITORIOS.md` lista os repositórios estudados, o que foi aproveitado de cada um e as próximas melhorias.

`docs/Plataformas de clipes com IA.md` reúne como OpusClip, Klap, Vizard, Submagic, OpenShorts, Clips Kitty e outros escolhem e editam os cortes, com links para o código de cada um. Consulte antes de inventar uma técnica nova.

## Documentação para o dono
- `docs/INSTALAR_PC.md`: tutorial de instalação e atualização (pasta `C:\deploy\darkclip`).
- `docs/GUIA_DO_SISTEMA.md`: o que cada aba e função faz. Atualize quando mudar a interface.
- `docs/GANCHOS.md`: tipos de gancho e final, como o DarkClip escolhe, e o que a pesquisa diz.
- `docs/IDEIAS_ENGENHARIA.md` e `docs/ESTUDO_EDICAO.md`: ideias estudadas (REA, Cut.Pro público) e referências de edição.

## Próximos passos (ROADMAP)
0. **Cortes de live em lotes** (Kick/Twitch/YouTube ao vivo): confirmar se o yt-dlp detecta a live da Kick antes de construir.
1. **Falante ativo** (quem está falando) em podcasts: TalkNet/LR-ASD ou correlação entre a boca e o áudio, em vez de "maior rosto".
2. **Reranking relativo:** uma segunda passada da IA comparando os candidatos entre si; notas absolutas se aglomeram.
3. **Detectar legenda já gravada no vídeo original** e recortar essa faixa, para não empilhar duas legendas.
4. **Emojis e efeitos sonoros** nas palavras-chave; B-roll automático.
5. **Gravar tela** e **legenda editável** (corrigir uma palavra antes de renderizar).
6. **Empacotar como .exe** (PyInstaller, ou pywebview para uma janela nativa) com ffmpeg embutido.
7. **Agendamento nativo** no Facebook (`video_state=SCHEDULED`), para não depender do PC ligado na hora do post.
8. **Métricas do Facebook e do Instagram** (Graph API Insights) na aba Canal, além do YouTube.
