# DarkClip — fábrica de Shorts para canal dark

> **Instalar no PC (passo a passo):** [docs/INSTALAR_PC.md](docs/INSTALAR_PC.md).
> **O que cada função faz:** [docs/GUIA_DO_SISTEMA.md](docs/GUIA_DO_SISTEMA.md). **Ligar ao Claude (MCP):** dois cliques em `registrar_claude_windows.bat`.
> **Nunca fez um canal?** Leia primeiro o [COMECE_AQUI.md](COMECE_AQUI.md) e o plano de renda em [docs/MONETIZACAO.md](docs/MONETIZACAO.md).
> **Postar automático:** [docs/CONTAS.md](docs/CONTAS.md). **O que postar:** [docs/CONTEUDO.md](docs/CONTEUDO.md). **Custos das IAs:** [docs/CUSTOS_IA.md](docs/CUSTOS_IA.md).

Transforma vídeos longos em Shorts verticais prontos para postar e cria Shorts narrados "dark" (sem rosto), com um app instalável no celular.

```
Link/arquivo ─► yt-dlp ─► legendas/whisper ─► IA escolhe trechos ─► ffmpeg 9:16 + legenda animada + gancho ─► app ─► YouTube
Tema/roteiro ─► Claude (roteiro) ─► edge-tts (voz) ───────────────► ffmpeg (fundo dark + legenda) ──────────┘
```

## O que faz

| Modo | Entrada | Saída |
|---|---|---|
| ✂️ **Clipar** | link (YouTube/TikTok/Instagram/…) ou vídeo do celular | N Shorts 1080×1920 com nota de viralização, título, descrição e hashtags |
| 🎙️ **História** | tema (a IA escreve) ou roteiro pronto | Short narrado com voz neural grátis, fundo escuro/gameplay e legenda |

- **Download inteligente**: para links, baixa primeiro só a legenda, os capítulos e o mapa de calor "Mais repetidos" do YouTube (poucos KB). Depois de escolher os trechos, baixa **apenas esses trechos**: uma live de 3 h vira poucos MB, ótimo no celular. Se o site não aceitar download parcial, baixa o vídeo inteiro uma vez, automaticamente.
- **Seleção multi-sinal**: a nota final combina
  - a IA: com `ANTHROPIC_API_KEY`, o Claude avalia gancho, se o trecho se sustenta sozinho e o final forte; sem chave, uma heurística local;
  - 🔥 o **heatmap real do público** (trechos mais reassistidos);
  - ⚡ a energia do áudio (risadas, gritos, emoção);
  - o ritmo de fala.

  O app mostra cada sinal no cartão do clipe.
- **Reenquadramento automático** (`auto`):
  - **câmera virtual que segue o rosto**, com zona morta e suavização (não treme);
  - nos cortes de cena, pula direto para o novo plano, como um editor faria;
  - **tela dividida** quando há duas pessoas lado a lado (podcast);
  - **fundo desfocado** quando não há rosto.

  Usa o detector YuNet se estiver instalado, senão o Haar.
- **Edição automática**:
  - **remove silêncios** (jump cuts) e mantém 1,5 s das risadas para não matar a piada;
  - **zoom de impacto** alternado por frase;
  - **barra de progresso**;
  - áudio normalizado a -14 LUFS.
- **Legendas**: palavra a palavra, em 4 estilos (amarela, verde, caixa, minimalista). **Palavras-chave** em outra cor, gancho vermelho no topo nos 3 primeiros segundos e anotações como "(Risos)" removidas.
- **Editor no celular**: ajuste início e fim (±1 s), gancho, título, palavras em destaque, enquadramento e estilo, depois toque em **Re-renderizar** só aquele clipe.
- **Lote**: cole vários links, um por linha. Cada um vira um trabalho na fila.
- **Publicar**: no celular, o botão 📤 abre o menu "compartilhar" com o vídeo e copia o texto, para você escolher o app do YouTube. Com o Postiz configurado, o botão 🚀 agenda a postagem direto.

## Como a IA escolhe os trechos (v3)

```
            ┌─ 🔥 Mapa "Mais repetidos" do YouTube (o que o público reassiste)
            ├─ 💬 Comentários: timestamps citados, frases citadas, reações (kkkk, 😂)
 link ──────┼─ 💬 Chat do replay de lives (picos acima do normal, recuados ~20 s)
            ├─ 👁️ Gemini assiste o vídeo (imagem + áudio) e verifica as pistas do público
            ├─ ⚡ Energia do áudio  ·  🗣️ ritmo de fala
            └─ 📝 Transcrição
                          ↓
        Claude decide: trechos que se sustentam sozinhos, gancho nos 2 s, desfecho incluído,
        notas Gancho/Fluxo/Valor/Tendência, títulos e hashtags em PT-BR
                          ↓
        Nota final = IA 50% + heatmap 20% + comentários 15% + visual 10% + áudio 5%
        (em trecho com pouca fala, como gameplay ou corrida, o visual e o áudio pesam mais)
```

- **Sem nenhuma chave** funciona com regras automáticas, heatmap e comentários.
- **Com `GEMINI_API_KEY`** (grátis em aistudio.google.com/apikey) a IA *assiste* o vídeo. Links do YouTube vão direto, sem baixar.
- **Com `ANTHROPIC_API_KEY`** o Claude toma a decisão final e escreve os textos.
- **Campo "O que procurar?"**: peça um assunto ("a parte em que ele fala do acidente").

### 📅 Central do Canal (o "Metricool" grátis)
- **Calendário:** cada clipe tem o botão 📅 Planejar, com o horário sugerido. O app avisa ⏰ quando é hora de postar.
- **Postar:** o botão 📤 abre o menu de compartilhar do celular com o vídeo e o texto copiado. Não precisa de API nem de aprovação de app.
- **Números do canal pelo yt-dlp, sem API paga:** inscritos, views por Short, os mais vistos e o progresso estimado da monetização.
- **Aprendizado:** compara duração, horário, estilo e formato com as views reais. As dicas aparecem no app e entram na decisão da IA.
- Para agendar automaticamente no futuro, há integração opcional com o Postiz (self-hosted e open source).

### 🔍 Claude "assiste" vídeos
- **Skill `/assistir-video`** (Claude Code, sem chave de API). `python -m darkclip.vision <link>` gera quadros-chave (mudanças de cena + intervalo fixo) com a fala de cada trecho, e o Claude lê as imagens.
- **No app:** modo **🔍 Analisar vídeo**, com resumo, gancho, linha do tempo, melhores momentos e riscos, pela API do Claude ou do Gemini.
- **Nos cortes:** sem chave do Gemini, o Claude vira o sinal 👁️ (`DARKCLIP_VISION=auto|gemini|claude|off`).

### 🔗 Contas e postagem automática
Conecte a Página do Facebook, o Instagram profissional e o YouTube (guia em [docs/CONTAS.md](docs/CONTAS.md)). No **📅 Planejar**, escolha a conta e "automático", e o DarkClip publica sozinho na hora marcada. TikTok e Kwai não têm API aberta: continuam pelo 📤.

### Skill `/analisar-comentarios`
Para investigar um vídeo **antes** de clipar, use o Claude Code nesta pasta. Rode `/analisar-comentarios <link>` ou diretamente:
```bash
python -m darkclip.comments "https://youtu.be/XXXX" --max 800
```
A saída mostra os momentos mais citados pelo público, o que as pessoas dizem de cada um, os comentários mais curtidos e os temas.

Pesquisa completa sobre como OpusClip, Klap, Vizard e os projetos abertos funcionam: [docs/Plataformas de clipes com IA.md](docs/Plataformas%20de%20clipes%20com%20IA.md).

## Instalação

### Opção A: PC + celular como controle (recomendado)
**Windows:** dê dois cliques em `install_windows.bat` e depois em `start_windows.bat`. A janela mostra o endereço com a senha, para você abrir no celular.

**Linux/Mac:**
```bash
./install.sh
```
```bash
nano .env        # defina DARKCLIP_TOKEN e, se quiser, ANTHROPIC_API_KEY
```
```bash
./start.sh
```
No celular, na mesma rede Wi-Fi, abra `http://IP-DO-PC:8787`, vá em ⚙️ Ajustes, informe o token e use "Adicionar à tela inicial". Para acessar fora de casa, use um túnel com HTTPS, como Tailscale ou Cloudflare Tunnel. Com HTTPS o botão "compartilhar arquivo" também funciona.

### Opção B: tudo no Android (Termux)
1. Instale o **Termux** pelo F-Droid ou pelo GitHub. A versão da Play Store está desatualizada.
2. Baixe o `darkclip.zip` no celular (pasta Download).
3. No Termux:
```bash
termux-setup-storage
```
```bash
pkg install -y unzip && cp ~/storage/downloads/darkclip.zip ~ && cd ~ && unzip -o darkclip.zip
```
```bash
bash ~/darkclip/install_termux.sh
```
4. Para abrir, sempre: digite `darkclip` no Termux. O app abre sozinho no navegador. Instale-o em ⋮ → **Adicionar à tela inicial**.
5. (Opcional) Com o app **Termux:Widget**, adicione o widget e abra o DarkClip com um toque.

Dicas: desative a otimização de bateria do Termux (Configurações → Apps → Termux → Bateria → Sem restrições). Deixe o Termux aberto em segundo plano enquanto renderiza. Um clipe leva cerca de 1 a 3 min.

### Linha de comando
```bash
python3 -m darkclip.cli clip "https://youtu.be/XXXX" -n 5 --style verde --niche "mistérios"
```
```bash
python3 -m darkclip.cli story --topic "O mistério do voo 19"
```
Os resultados ficam em `data/jobs/<id>/clip_XX.mp4`, junto com `job.json` (títulos, descrições e hashtags).

## YouTube bloqueando ("confirme que você não é um robô")
O YouTube costuma bloquear IPs de servidores e VPS. No seu PC ou celular (IP residencial) isso raramente acontece. Se acontecer:
1. Atualize o yt-dlp: `pip install -U "yt-dlp[default]"`.
2. Tenha Node ou Deno instalado (o DarkClip já ativa o Node automaticamente).
3. Último recurso: exporte um `cookies.txt` do YouTube e aponte `DARKCLIP_COOKIES` para ele. Use uma conta secundária: usar cookies em servidor pode levar a bloqueio da conta.
4. Ou baixe o vídeo pelo celular e envie o arquivo no app. Sem legenda, o PC transcreve com `faster-whisper`.

## Configuração (`.env`)
Veja `.env.example`. Itens principais: `ANTHROPIC_API_KEY`, `DARKCLIP_TOKEN`, `DARKCLIP_VOICE`, `DARKCLIP_PRESET` (use `ultrafast` no celular), `POSTIZ_API_KEY` e `POSTIZ_YOUTUBE_ID`.

## Estrutura
```
darkclip/download.py    yt-dlp (vídeo + legenda manual/automática)
darkclip/transcribe.py  VTT com tempo por palavra → segmentos; fallback faster-whisper
darkclip/ai.py          Claude (saída JSON estruturada) / heurística; roteiros dark
darkclip/signals.py     heatmap, capítulos, energia do áudio, risadas → nota final
darkclip/reframe.py     detecção de rosto/cena, câmera virtual, tela dividida
darkclip/render.py      ffmpeg: layouts, jump cuts, zoom, grade dark, legendas ASS, barra de progresso
darkclip/tts.py         edge-tts com tempo por palavra
darkclip/publish.py     Postiz CLI → YouTube Shorts
darkclip/pipeline.py    jobs (fila, progresso, limpeza)
server.py               API FastAPI + PWA
web/                    app mobile (PWA instalável)
```

## Repositórios de referência (para estudar ou integrar)
| Projeto | Para quê |
|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | download (já usado) |
| [SamurAIGPT/AI-Youtube-Shorts-Generator](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator) | LLM + Whisper + face tracking com suavização |
| [mutonby/openshorts](https://github.com/mutonby/openshorts) | plataforma self-hosted (MIT) de cortes 9:16 |
| [FujiwaraChoki/supoclip](https://github.com/FujiwaraChoki/supoclip) | alternativa open-source ao OpusClip, com dashboard |
| [Shaarav4795/ClippedAI](https://github.com/Shaarav4795/ClippedAI) | baseado em clipsai, limites de duração para Shorts |
| [artbyjazi/autoclip](https://github.com/artbyjazi/autoclip) | 100% offline (Whisper + Ollama) |
| [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) | vídeos faceless a partir de um tema (estoque + TTS) |
| [FujiwaraChoki/MoneyPrinter](https://github.com/FujiwaraChoki/MoneyPrinter) | automação de Shorts com MoviePy |
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | transcrição local rápida |
| [rany2/edge-tts](https://github.com/rany2/edge-tts) | vozes neurais grátis (já usado) |
| [gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app) | agendamento em 28+ redes (já integrado) |

Leia também o [PLAYBOOK.md](PLAYBOOK.md), com a estratégia do canal.
