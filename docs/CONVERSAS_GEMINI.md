# Conversas com o Gemini

Registro das conversas tidas com o Gemini (gemini.google.com) sobre o DarkClip.
Regra deste arquivo: **o que o Gemini viu no código fica separado do que é opinião dele.**
Nada aqui foi aplicado ao código ainda — é material de decisão.

---

## 2026-11-26 — Cortes de gameplay, gancho dos 3 primeiros segundos e legenda

- **Onde:** gemini.google.com, conversa "Otimização do DarkClip para Gameplay"
  (link: https://gemini.google.com/app/fe9a85da180db845 — só abre na conta do dono).
- **Modelo:** Gemini no modo "Auto".
- **O que foi enviado:** trechos reais de `darkclip/ai.py` (regras do prompt em `_select_claude`,
  núcleo do `_select_heuristic`, lista `HOOK_WORDS`), de `darkclip/hooks.py`
  (`HOOK_TYPES`, `decide()`, `peak_window()`, `valid_teaser()`) e de `darkclip/render.py`
  (dicionário `STYLES`, cabeçalho ASS do `build_ass()`, agrupamento em blocos e destaque palavra a palavra).
- **O que NÃO foi enviado** (e que o próprio Gemini marcou como suposição): o formato exato da
  transcrição com timestamps, como os sinais 👁️/⚡/😂 entram no prompt, a implementação de
  `_with_context`, de `pick_teaser` e do remapeamento de tempos do jump cut, e como o ffmpeg
  monta a prévia e queima a legenda.
- **Pedido explícito:** separar "o que viu no código" de "opinião", e dizer, a cada número,
  se é medido, convenção da indústria ou chute.

### Frente 1 — Escolha dos cortes em gameplay

#### A) O que o Gemini viu no código (descrição, não julgamento)

- O prompt de `_select_claude` exige: duração entre `min_s` e `max_s` sem sobreposição; trecho que
  faça sentido sozinho; prender nos 2 primeiros segundos; o fim conter o desfecho, escrito em `payoff`;
  recuar o início e nunca encurtar o fim; não começar com conjunção ou muleta; ignorar intro,
  inscrição, patrocínio e despedida; variar assuntos; e tratar os sinais do público (🔥 💬) como
  mais importantes que a opinião da própria IA. As notas são `hook`, `flow`, `value`, `trend` de 0 a 100.
- O `_select_heuristic` soma:
  `score = hook*2 + q + numbers*0.5 + density*2 + opener + closing - abs(dur-target)*0.05`,
  mais `heat*12` e `talk*10`. O `opener` leva −15 quando o trecho começa em letra minúscula ou com
  palavra de `BAD_START`; `closing` vale 2 quando o trecho termina em `.`, `!` ou `?`.
- `HOOK_WORDS` tem 29 palavras, todas do nicho dark/mistério/crime/dinheiro.

#### B) Opinião e recomendação do Gemini

1. **Onde o desenho atual falha em gameplay** (apontando a regra):
   - A regra "faça sentido sozinho / não comece com conjunção ou muleta" descarta falas reativas
     típicas de gameplay ("E aí, mano, olha isso", "Mas ele tava ali!"), em que o sentido está na tela.
   - A regra "comece na frase mais forte, mesmo pulando a introdução" corta o *setup* visual que cria
     a tensão; e quando o pico é visual ou sonoro e o streamer está calado, não existe "frase mais forte".
   - A exigência de `payoff` em texto falha quando o desfecho é visual (clutch, bug, susto, morte).
   - `density = len(words)/dur` penaliza silêncio tenso, que em gameplay é carga dramática, não vazio.
   - `opener -= 15` por letra minúscula e `closing` por pontuação dependem de pontuação que a
     transcrição automática quase não produz em fala rápida e grito.
   - `HOOK_WORDS` não contém vocabulário de gameplay (clutch, bug, lag, drop, tilt, roubou, morri, quase).
   - Na heurística entram apenas `heat` e `talk`: ⚡ (áudio), 😂 (risada) e 👁️ (visual) não pontuam
     (marcado por ele como suposição, por depender de código não enviado).

2. **Sinais mensuráveis que ele recomenda somar** (sem modelo pesado):
   - **Pico de áudio relativo:** PCM mono a 16 kHz, RMS em janelas de 0,25–0,5 s, normalizado por
     z-score ou percentil *do próprio vídeo*.
   - **Corte de cena:** `ffmpeg select='gt(scene,T)'` ou diferença de histograma — marca respawn,
     death screen, cutscene, e mede o ritmo de edição.
   - **Variação de movimento:** `cv2.absdiff` em escala de cinza ou optical flow Farneback em
     resolução reduzida (160x90 ou 320x180) para rodar rápido.
   - **ROI de HUD/killfeed/placar/webcam:** template matching ou diferença de pixels em regiões
     pequenas. Ele marca como suposição que isso exige calibrar as regiões por jogo.
   - **Chat da live:** mensagens por segundo e taxa de emotes/risada — para ele, um dos sinais mais
     fortes que existem em gameplay ao vivo.

3. **Como mudar o prompt sem quebrar o nicho dark:** tornar o perfil paramétrico (`dark` vs `gameplay`)
   em vez de reescrever as regras. No perfil gameplay, dizer explicitamente que gancho e desfecho
   podem ser visuais ou sonoros, e relaxar a proibição de começar com conjunção quando houver sinal
   forte de ⚡/😂/👁️/🔥. Manter universais: duração, não sobrepor, evitar intro/patrocínio/CTA,
   variedade, e o peso maior dos sinais reais do público.

4. **Substituto do `payoff` em texto:** trocar o campo único por `payoff_type` mais uma descrição curta
   do que acontece na tela ou no áudio (`payoff_visual` / `payoff_audio`), mais uma âncora temporal
   (`payoff_offset_s` ou `end_buffer_s`). No pós-processamento, estender o fim com um pequeno padding
   depois do pico de áudio ou ação, em vez de cortar na pontuação gramatical.

### Frente 2 — Gancho dos 3 primeiros segundos

#### A) O que o Gemini viu no código

- `HOOK_TYPES` define seis tipos (`previa`, `pergunta`, `espera`, `choque`, `pov`, `acao`), com listas
  de textos fixos; `acao` tem lista vazia.
- `decide()` escolhe o tipo pelo modo forçado ou pelo que a IA sugeriu; quando o tipo é `previa` ou
  indefinido, busca a prévia em três níveis: `valid_teaser` (sugestão da IA), `peak_window` (energia)
  e `pick_teaser`. Sem IA, vira `previa` apenas se houver prévia e `dur >= 25`; se pediram prévia e
  não há momento forte, cai para `espera`.
- `peak_window` usa `hop=0.5`, `length=2.4`, `min_db=3.0`, compara com a **mediana do próprio corte**
  e só procura depois de 35% do corte.
- `valid_teaser` rejeita prévias que comecem antes de 25% do corte ou cuja duração não esteja entre
  1,0 s e 4,0 s.

#### B) Opinião e recomendação do Gemini

1. **O que erra nos 3 primeiros segundos:**
   - Uma prévia de 2,4 s mais o texto consome quase toda a janela crítica de 3 segundos e cria
     "dois começos" no clipe.
   - Falta marcação visual separando a prévia do início real (ele marca como suposição sobre o render):
     sem corte seco, zoom ou indicação de flashback, o espectador se confunde sobre o que é presente.
   - Em gameplay a tela já está cheia (HUD, chat, killfeed, webcam); o texto no topo pode cobrir
     informação do jogo.
   - **Os textos fixos são genéricos demais.** "ESPERA O FINAL…", "VAI DAR CERTO?" são clichês que o
     público reconhece como isca vazia. Opinião dele (declarada como chute): em gameplay, **sem texto
     costuma render mais que texto genérico**; texto só quando ele acrescenta contexto que falta.

2. **`peak_window` — valores sugeridos** (todos declarados por ele como chute, não medição):
   - `min_db`: **6,0 a 8,0 dB** acima da mediana, em vez de 3,0 — 3 dB é baixo demais e deixa passar
     respiração e efeito comum.
   - início da busca: **50% a 60%** do corte, em vez de 35%.
   - janela: **1,5 a 2,0 s**, em vez de 2,4 s, para isolar o pico sem diluir.
   - Ressalva dele: a mediana distorce em clipes muito silenciosos ou muito gritados.

3. **`valid_teaser` e o tamanho da prévia:** 2,4 s está numa faixa razoável (ele chama de convenção
   prática de edição: entre ~1,5 s e 3,0 s), mas **deveria variar pelo tipo de momento** — jumpscare ou
   one-tap pedem 1,2–1,8 s; clutch ou falha com reação pedem 2,0–3,0 s (chutes dele). Os limites de
   25% e de 1,0–4,0 s fazem sentido como guarda-corpo.

4. **A prévia nem sempre ajuda.** Ela estraga o clipe quando entrega o desfecho (placar final,
   vitória, item raro, a morte exata), quando quebra uma reviravolta, e quando o corte já abre quente.
   Ajuda quando há setup longo e o flash-forward mostra um fragmento **ambíguo**, de alta tensão,
   sem revelar o resultado.

5. **O que falta frente aos apps maduros** (ele marca como descrição de prática de mercado, suposição
   sobre a implementação interna de terceiros): enquadramento vertical dinâmico mantendo jogo e
   reação legíveis; gancho visual e sonoro sincronizado com a ação (corte de ritmo, zoom, legenda
   dinâmica) em vez de só um texto estático; aparar o "momento morto" dos segundos 0–2 para o clipe
   abrir em movimento; e controlar a poluição visual, para gancho, legenda, marca d'água e HUD não
   disputarem o mesmo espaço nos primeiros 3 segundos.

### Frente 3 — Legenda

#### A) O que o Gemini viu no código

- `STYLES` com cinco estilos; os dinâmicos usam `words 3` / `chars 16` e fonte 80–84 em `PlayResY=1920`;
  `minimal` usa 5 palavras / 26 caracteres e `frases` usa 4 / 22.
- `build_ass()` ancora a legenda com `Alignment 2` e `MarginV = int(H*0.29)` (ou centralizada com
  `Alignment 5` quando `middle`), escala a fonte com `k = min(1.0, H/1920) ** 0.6`, usa `BorderStyle 1`,
  `Outline max(3, bord*k)` e `Shadow 3`; o estilo `Hook` usa `BorderStyle 3`, `Outline 18*k`,
  `Alignment 8` e `MarginV H*0.12`.
- O bloco fecha quando atinge `st['words']`, estoura `st['chars']` ou a última palavra termina em
  `.`, `?` ou `!`.
- A cada palavra ativa o **bloco inteiro é reescrito** num novo `Dialogue`, mudando só a cor; a palavra
  ativa recebe `\fscx110\fscy110` (ou `\bord16` no estilo pill), e a primeira palavra do bloco recebe
  o `pop` de escala 104% → 100%.
- O gancho é um `Dialogue` de 0 até `min(3.5, duration)` com `\fad(150,250)`.

#### B) Opinião e recomendação do Gemini

1. **Blocos de 3 palavras / 16 caracteres:** perto do ideal para leitura rápida, mas o limite de
   16 caracteres é rígido demais para o português — com artigos e preposições o bloco cai muito para
   1 ou 2 palavras e as trocas ficam rápidas demais. Sugestão dele (chute): **2 a 4 palavras e
   18 a 22 caracteres** nos estilos dinâmicos, sempre em uma linha; **4 a 6 palavras e 24 a 30
   caracteres** nos estilos de frase.

2. **Destaque palavra a palavra:** o padrão de manter o bloco parado e mudar só a cor é, para ele,
   o mais legível e o melhor para retenção (estilo Hormozi/Submagic), e 10% de crescimento é sutil o
   bastante para não cansar. **Mas o risco de tremor é real:** no libass, aumentar `\fscx` de uma
   palavra dentro de um bloco centralizado faz a linha inteira ser recalculada e empurra as palavras
   vizinhas; o `\bord16` do estilo pill tem o mesmo efeito. Recomendação: destacar **só por cor**
   (ou peso/brilho, sem mudar largura) e deixar a animação de escala para o bloco inteiro na entrada,
   como o `pop` já faz.

3. **Zona segura em 9:16** (ele declara como convenção da indústria, variando por aparelho e versão
   do app): rodapé com descrição, áudio, perfil e barra de progresso ocupa os **18% a 25% inferiores**
   (chegando a 28–30% com descrição expandida); a coluna de botões à direita ocupa **12% a 16% da
   largura**, entre **35% e 82% da altura**; o topo ocupa os **10% a 14% superiores**.
   Veredito sobre o código: `MarginV = 29%` é **posição segura** e bem escolhida. O cuidado é a
   largura — nessa altura a linha pode encostar nos ícones da direita; ele sugere `MarginL`/`MarginR`
   de 8% a 12% da largura (até ~14% à direita na metade inferior). Sobre o layout gamer: pôr a legenda
   na emenda entre webcam e jogo é, segundo ele, uma das melhores posições possíveis; só conferir que
   `hook_v = top_h + H*0.10` não colide com ela.

4. **Outline 7 + Shadow 3:** suficiente na maioria dos casos, porque o contorno cria contraste local
   letra a letra. Falha com HUD muito poluído, explosões brancas ou chat passando atrás. Opinião
   (declarada como chute/prática): manter o contorno grosso como padrão — fica esteticamente melhor
   que a caixa retangular, que lembra legenda de TV antiga e tampa mais o jogo — e oferecer a caixa
   semitransparente (`BorderStyle 3` com alpha ~40–50%, ex. `&H66000000&`) como **estilo opcional**.

5. **Substituir a quebra por pontuação** (todos os números marcados por ele como chute):
   - **Pausa de áudio:** fechar o bloco quando o intervalo entre palavras for **≥ 0,25–0,35 s**,
     mesmo com 1 ou 2 palavras — sincroniza a troca com a respiração real.
   - **Duração máxima do bloco:** fechar em **1,4–1,8 s** para o bloco não travar na tela.
   - **Fronteira sintática leve:** com o bloco já em ~70% do limite, fechar antes de preposição,
     conjunção ou artigo (que, mas, porque, quando, para, com, e, ou, se) — "ELE NÃO VIU" / "O CARA"
     em vez de "ELE NÃO" / "VIU O CARA".
   - Manter `.`, `?`, `!` como **bônus**, nunca como regra única.

6. **O que mais daria retenção e o código não faz:**
   - **Dicionário de correção de termos de jogo** antes de gerar o ASS (clutch, nerf, buff, drop,
     flash, smoke, ranked, tilt, GG): erro grosseiro de transcrição derruba a credibilidade na hora.
   - **Variar o estilo nos picos:** quando o bloco coincide com pico de áudio, aumentar a fonte do
     bloco inteiro em 15–20%, trocar de estilo ou aplicar rotação leve (`\frz` entre −2° e +2°).
   - **Emoji contextual pontual**, no máximo 1 a cada 4–6 segundos, só em palavras de emoção forte.
   - **Ponte visual nos jump cuts:** micro overlap de 1–2 quadros na legenda em volta dos cortes secos,
     para o texto não piscar.
   - **Revisão antes de queimar:** expor um arquivo intermediário editável (JSON/SRT) para corrigir
     um nome próprio sem reprocessar transcrição e seleção.

### Observações de quem conduziu a conversa (Claude Code)

- Vários números do Gemini são **chute declarado por ele mesmo**, não medição: `min_db` 6–8 dB,
  busca a partir de 50–60%, janela de 1,5–2,0 s, pausa de 0,25–0,35 s, bloco de 1,4–1,8 s,
  18–22 caracteres. Antes de virar padrão, devem ser testados num vídeo de gameplay real e comparados
  com o comportamento atual.
- Os percentuais de zona segura em 9:16 são convenção, não medição desta data; valem como ponto de
  partida, não como especificação das plataformas.
- O ponto do **reflow do libass** ao usar `\fscx110` numa palavra dentro de linha centralizada é
  verificável sem IA: basta renderizar um clipe e olhar quadro a quadro. É o item mais fácil de
  confirmar ou descartar.
- O Gemini não viu `_with_context`, `pick_teaser`, o remapeamento do jump cut nem o render em si.
  Qualquer afirmação sobre essas partes é suposição dele.

---

## 2026-11-26 (parte 2) — Como analisar o vídeo, e o que falta para ser a melhor ferramenta

Mesma conversa do Gemini ("Otimização do DarkClip para Gameplay"), continuando depois das
três primeiras frentes.

### Frente 4 — Pipeline de análise (resolução e fps)

O dono lembrou que o Gemini já tinha dito, numa conversa anterior, que analisar o vídeo em
qualidade baixa e fps baixo rende mais. Esta rodada foi para fechar isso com número.

#### A) Fatos técnicos verificáveis que ele trouxe

- Pixels por quadro em 16:9: 1080p = 2.073.600; 480p (854x480) = 409.920 (~5x menos);
  360p (640x360) = 230.400 (~9x menos); 240p (426x240) = 102.240 (~20x menos);
  144p (256x144) = 36.864 (~56x menos).
- Intervalo entre quadros: 2 fps = 500 ms; 5 fps = 200 ms; 10 fps = 100 ms; 15 fps = 66,7 ms.
  Evento mais curto que o intervalo pode cair inteiro entre duas amostras e não aparecer em quadro nenhum.
- MP4 e WebM têm índice de busca (moov atom / Cues), então dá para pedir faixas de bytes (HTTP Range)
  e ler só um trecho, desde que o servidor aceite `Accept-Ranges`.
- O YouTube serve áudio e vídeo em faixas separadas (DASH), então dá para baixar só o áudio
  (~48–128 kbps) sem tocar no vídeo.

#### B) Recomendação dele

1. **Para analisar: 360p (640x360) a 4–6 fps** (chute dele). Em 360p são 9x menos pixels que 1080p,
   e entre 4 e 6 fps (167 a 250 ms) ainda se pega reação facial, susto, troca de câmera e início de
   luta. Abaixo disso perde contexto; acima de 480p/10–15 fps no vídeo inteiro o ganho não paga.
2. **O que se perde:** em 240p, uma fonte de HUD que tinha 16–20 px em 1080p fica com 3,5–4,5 px —
   **killfeed e número de HUD não sobrevivem**. Sobrevivem: barra de vida pela cor, flash de dano na
   borda, tela de morte/vitória, e a webcam se ocupar 15–20% da tela. Para ler texto de HUD o mínimo
   prático é 480p, ou recortar a região de interesse em resolução maior antes de reduzir o resto.
   A 5 fps sobrevive macro-movimento (perseguição, tiroteio de mais de 1 s, reação do corpo); some
   flick shot e one-tap (< 150 ms), muzzle flash de 1 quadro, bug de física de 1–2 quadros.
   Ressalva útil dele: mesmo quando o evento cai entre quadros, a **consequência** (HUD mudando,
   reação facial logo depois) aparece nos quadros seguintes.
3. **Funil de dois passes — ele recomenda com força:**
   - *Passe 1, barato, vídeo inteiro:* áudio completo + proxy 144p–240p a 2–3 fps; energia do áudio
     (hop 0,25–0,5 s, z-score), transcrição e palavras-gatilho, chat, corte de cena por scene score e
     `cv2.absdiff` em 160x90. Saída: 15 a 30 janelas candidatas; de 180 minutos de VOD sobram
     10 a 20 minutos úteis (taxa estimada por ele).
   - *Passe 2, caro, só nos candidatos:* 360p–480p a 6–10 fps, com Gemini validando o tipo de evento,
     o gancho e o desfecho visual — e **YuNet já aqui**, não só no render, para saber antes se há
     webcam ativa e se houve expressão forte.
4. **Quadros para IA de visão:** 360p–480p por quadro; JPEG qualidade 70–80 (`-q:v 4..6`) — abaixo de
   60 aparece bloco no texto, acima de 85 o arquivo quase dobra sem ganho. Para triagem de trecho
   longo, 15 a 30 quadros por minuto; para inspecionar um candidato de 20–40 s, 1 a 2 quadros por
   segundo. Contact sheet 3x3 com o tempo queimado em cada célula dá mais informação por chamada,
   desde que cada célula tenha ao menos 320x180; um quadro por vez só quando precisa ler detalhe fino.
   Observação dele: o próprio Gemini já amostra vídeo internamente (~1 fps em vídeo longo), então
   mandar o clipe curto em 360p/480p direto pode dispensar a grade.
5. **Não baixar o vídeo inteiro:** áudio de 2 horas pesa 50–110 MB contra 2–8 GB do 1080p. Ordem
   sugerida: (a) só áudio + metadados, roda whisper e energia; (b) proxy de vídeo com
   `bestvideo[height<=360]` (80–250 MB num vídeo longo); (c) `--download-sections "*INICIO-FIM"`
   em 1080p só nos trechos aprovados.
6. **Onde rodar cena e movimento:** nem no áudio (não tem informação visual) nem no 1080p final
   (desperdício). Depois dos sinais de áudio, num proxy de baixa resolução pedido ao yt-dlp, lendo
   direto de um pipe do ffmpeg para o NumPy:
   `ffmpeg -i proxy.mp4 -vf "fps=3,scale=160:90,format=gray" -f rawvideo pipe:1` — 14.400 bytes por
   quadro, cerca de 155 MB para uma hora de vídeo, sem salvar PNG em disco.

> **Ressalva de quem conduziu:** "qualidade baixa deixa tirar mais detalhe" não é bem assim.
> Resolução baixa **não acrescenta** detalhe nenhum — ela só torna cada quadro tão barato que dá para
> olhar **muito mais quadros** pelo mesmo custo, e para varrer o vídeo inteiro em vez de só trechos.
> Os próprios números do Gemini mostram o limite: a 240p o killfeed e o número de HUD somem.

### Frente 5 — O que falta para ser a melhor ferramenta

Foi enviada a lista completa do que o DarkClip já tem e do que já está no roadmap, para ele não
recomendar o que já existe.

#### B) Opinião dele (não há fato novo de código nesta parte)

1. **A melhoria única que ele escolheu:** ajuste automático das **fronteiras do corte** — início e
   fim do arco — cruzando a escolha da IA com áudio, fala e evento visual. Argumento: um Short morre
   mais por começar com enrolação, começar tarde demais ou terminar antes do desfecho do que por
   falta de efeito visual. O DarkClip já tem os sinais; falta a etapa de refino de borda.
2. **Ordem por impacto/esforço** (horas são chute dele):
   1. Filtro anti-enrolação no começo e anti-corte do desfecho — impacto alto, 4–8 h.
   2. Normalização de gíria e termo gamer PT-BR antes do ASS e do prompt — alto, 3–6 h.
   3. Áudio primeiro + proxy leve nos candidatos — alto (em velocidade, não em estética), 6–12 h.
   4. Reranking relativo entre os melhores candidatos — médio-alto, 4–8 h.
   5. Ritmo da legenda (quebra por pausa) e fim do tremor na palavra ativa — médio, 4–8 h.
   6. Gancho mais criterioso (sem texto genérico quando o início já prende) — médio, 3–6 h.
   7. VAD simples para não cortar em silêncio longo — médio, 4–8 h.
   8. Zoom leve e som só em pico real — médio-baixo, 6–10 h.
   9. Empacotar como .exe — baixo para a qualidade do corte, 1–3 dias.
   10. Mais integrações e métricas de rede antes de fechar o núcleo de edição — baixo, 2–5 dias.
3. **Concorrentes** (ele marca tudo como suposição de mercado, sem acesso ao código deles).
   O que o público percebe: ritmo enxuto sem pausa morta, legenda muito legível e bem quebrada,
   enquadramento vertical consistente, e arco com começo-meio-fim em vez de pedaço solto.
   O que é marketing: "nota viral" prometendo prever viralização, excesso de preset e efeito, e a
   promessa de um clique salvar qualquer vídeo.
4. **Onde o DarkClip já está melhor:** combinar sinais reais do público (heatmap, comentários com
   tempo, chat de live) com energia e visão, em vez de só transcrição; layout de gameplay e reação,
   que ferramenta genérica de talking head resolve mal; e funcionar offline, sem caixa-preta, com
   feedback do dono e controle de custo.
5. **Onde ele acha que há esforço com pouco retorno:** espalhar em PWA, MCP, formatos de exportação,
   empacotamento e integrações sociais antes de fechar o ciclo seleção → gancho → enquadramento →
   legenda em gameplay; excesso de tipos de gancho e de modelo visual quando um conjunto menor e bem
   calibrado é mais consistente; e **mexer em número fino sem medir antes e depois** num conjunto
   fixo de 10 a 15 cortes reais de teste.
6. **Métrica antes de publicar:** um `clip_quality_score` de 0 a 100 (pesos são chute dele), somando
   abertura limpa (0–25: pune silêncio inicial, muleta e hesitação nos primeiros 1,5–2,0 s),
   fechamento completo (0–25: termina em pausa natural ou depois do pico, com margem),
   densidade de sinal útil (0–25: fala relevante, picos, heatmap/comentários/chat, sinal visual) e
   qualidade técnica (0–25: áudio estourado, estalo no jump cut, perda do sujeito no enquadramento).
   Rejeitar abaixo de 55/100, ou usar a nota para reordenar antes de gastar render.

---

## 2026-11-26 — Teste do tremor da legenda (medido aqui, não é opinião)

O Gemini afirmou que `\fscx110\fscy110` na palavra ativa, dentro de um bloco centralizado,
faz o libass recalcular a linha e empurrar as palavras vizinhas. **Isso foi medido e confirmou-se.**

**Como foi medido:** `render.build_ass()` gerou o ASS real do estilo `amarelo` com as palavras
"ELE NAO VIU" (uma por segundo), queimado com ffmpeg sobre fundo preto 1080x1920, um PNG a cada
0,2 s, e a posição horizontal de cada letra medida pela coluna de pixels acesos.

**Resultado** (posição da primeira letra de cada palavra, em pixels):

| destaque em | "ELE" começa em | "NAO" começa em | "VIU" começa em |
|---|---|---|---|
| ELE (0,6–1,4 s) | 298 | 480 | 662 |
| NAO (1,6–2,4 s) | 297 | **465** | 663 |
| VIU (2,6–3,6 s) | 299 | 466 | **649** |

- As palavras saltam até **15 px na horizontal** a cada troca de destaque — "NAO" pula 15 px e
  "VIU" pula 14 px. Em tela de 1080 px de largura, é cerca de 1,4% da largura, três vezes por bloco.
- A largura das letras confirma que o `\fscx110` está sendo aplicado (a letra "N" vai de 43 para
  47 px, o "A" de 54 para 60 px).

**Teste da correção:** o mesmo ASS com o `\fscx110\fscy110` removido (destaque só por cor) foi
renderizado e medido do mesmo jeito. As letras ficam em **[305, 356, 401, 473, 522, 579, 655, 710, 731]**
do começo ao fim, com uma única variação de 1 px em uma letra (suavização de borda). **O tremor some.**

Conclusão: a recomendação do Gemini neste ponto está certa e é barata de aplicar — tirar
`\fscx110\fscy110` do destaque e, se quiser o "pulo", animar o bloco inteiro na entrada, como o
`pop` já faz na primeira palavra. Falta decidir com o dono se o destaque só por cor é suficiente
visualmente, já que ele perde o efeito de "crescer".

### Correção aplicada em 2026-11-26

Em `darkclip/render.py`, no destaque da palavra ativa, o `\fscx110\fscy110` foi removido —
o destaque agora é só pela cor:

```python
# antes
parts.append(f"{{\\c{st['hl']}\\fscx110\\fscy110}}{txt}{{\\r}}")
# depois
parts.append(f"{{\\c{st['hl']}}}{txt}{{\\r}}")
```

O `pop` de entrada do bloco (`\t(0,80,\fscx104...)`) **foi mantido**: ele anima o bloco inteiro,
não uma palavra isolada, então não desloca nada.

**Medição depois da correção**, nos cinco estilos:

| estilo | deslocamento máximo das letras |
|---|---|
| `amarelo` | 1 px (suavização de borda) |
| `verde` | 1 px (suavização de borda) |
| `caixa` | 0 px — ver nota abaixo |
| `frases` | sem destaque palavra a palavra |
| `minimal` | sem destaque palavra a palavra |

**Nota sobre o estilo `caixa`:** ele nunca teve tremor. Usa `\bord16` em vez de `\fscx`, e contorno
não muda o espaçamento no libass. As letras ficam exatamente nas mesmas colunas
(316/364/408, 476/522/577, 649/702/722) nos três estados do destaque; o que muda é só o
contorno de 16 px desenhado em volta da palavra ativa, que estende a mancha de pixels uns 15 px
para cada lado. Nenhuma mudança foi feita nesse estilo.

**O que mudou visualmente:** a palavra ativa não cresce mais 10%; fica marcada só pela cor
(amarelo no estilo `amarelo`, verde no `verde`). Se o efeito de crescer fizer falta, a alternativa
sem tremor é engrossar o contorno da palavra ativa (`\bord`), como o estilo `caixa` já faz.

### Conferência num clipe real (2026-11-26)

O teste anterior foi em fundo preto sintético. Este foi feito com imagem de verdade: os primeiros
9 segundos de `data/jobs/20261125-193951-a886f/src/clip_01_src.mp4`, em 1080x1920 com fundo
desfocado, e as palavras com tempo lidas do próprio `clip_01.ass` que o DarkClip gerou nesse job.
Estilo `amarelo`. Arquivos em `data/previews/tremor/`: `antes.mp4`, `depois.mp4` e
`comparacao.mp4` (lado a lado).

Medição no bloco "BEM TUDO VAMOS", enquanto o destaque anda pelas três palavras:

| | salto máximo de uma letra |
|---|---|
| antes (com `\fscx110`) | **22 px** |
| depois (só cor) | 3 px |

Os 22 px são maiores que os 15 px medidos no teste sintético porque as palavras deste bloco são
mais largas, então o 10% de aumento desloca mais.

**Achado secundário, não planejado:** dos 28 blocos de legenda desses 9 segundos, a maioria tem
**uma palavra só** — "AÍ?", "DINHEIRO,", "DINHEIRO,". O limite de `chars 16` do estilo estoura com
duas palavras portuguesas comuns ("DINHEIRO, DINHEIRO," tem 19 caracteres). Isso confirma na prática
a crítica do Gemini na Frente 3: com `chars 16`, o bloco vira uma palavra por vez em boa parte da
fala, e o destaque palavra a palavra perde o sentido, porque não há bloco para destacar dentro.
Nenhuma mudança foi feita nesse ponto ainda.

### Correção de um número do registro acima

O parágrafo "Achado secundário" diz que, dos 28 blocos daqueles 9 segundos, a maioria tinha uma
palavra só. **Está errado.** Os 28 são eventos `Dialogue` do ASS, e o `build_ass()` escreve **um
evento por palavra destacada**, não um por bloco. Contando blocos de verdade (texto distinto),
são 13 blocos: 3 de uma palavra, 4 de duas e 6 de três. O problema existe, mas atinge 3 de 13
blocos, não a maioria.

### `chars` de 16 para 18 (2026-11-26)

Aplicado em `darkclip/render.py`, nos três estilos com destaque palavra a palavra
(`amarelo`, `verde`, `caixa`). `minimal` (26) e `frases` (22) não foram tocados.

**Por que 18 e não os 18–22 que o Gemini sugeriu:** 20 foi testado e **quebra em duas linhas** no
pior caso. Medindo a largura do bloco renderizado em 1080x1920, com fonte 84 e contorno 7:

| | largura máxima | quebrou em duas linhas |
|---|---|---|
| `chars 18` | 865 px (de 960 úteis) | nenhum caso |
| `chars 20` | 865 px | "AQUELA MULHER GRANDE" |

Casos testados: "DINHEIRO, DINHEIRO,", "AQUELA MULHER GRANDE", "QUANDO VOCE ACHOU",
"ELE NAO VIU NADA", "PRECISO DE DINHEIRO", "COMECOU A CHOVER".

**Efeito nos mesmos 9 segundos de vídeo real:**

| | blocos de 1 palavra | de 2 | de 3 |
|---|---|---|---|
| `chars 16` | 3 | 4 | 6 |
| `chars 18` | 2 | 2 | 8 |

Vídeos em `data/previews/tremor2/`: `depois.mp4` (resultado final) e `chars_16_vs_18.mp4`
(lado a lado com o render de `chars 16`).

Nota: 18 é um teto por contagem de caracteres, que é uma aproximação grosseira da largura real —
"WWW" e "iii" contam igual. O jeito certo seria medir a largura do texto antes de fechar o bloco,
mas isso é uma mudança maior e não foi feita.

### Teste da CLI inteira (2026-11-26)

Comando, rodado com o Python do `.venv` do projeto:

```
python -m darkclip.cli clip --file data/jobs/20261125-193951-a886f/src/clip_01_src.mp4 \
    -n 1 --min 20 --max 45 --style amarelo --no-visual --no-comments
```

Resultado: `data/jobs/20261126-212104-38254/clip_01.mp4` — layout gamer, 16,9 s, 6 jump cuts,
nota 85, motor Gemini (o Claude não foi usado nesta execução), custo US$ 0,027.

Conferência no `clip_01.ass` gerado pela execução real:

- `fscx110` aparece **0 vezes** — a correção do tremor está valendo no caminho normal, não só no teste.
- Os blocos ficaram quase todos com 3 palavras ("SERÁ QUE É", "POLÍCIA OU O", "NÃO, ERA VAGABUNDO",
  "PEGAR O CARRO", "AGORA E VAZAR"), com poucos de 1 palavra, que são restos de frase ("VAMBORA.",
  "FORA.", "LUCIA!"). É o comportamento esperado com `chars 18`.

#### Dois tropeços de ambiente encontrados no caminho

1. **O Python global não serve.** Rodando com o `python` do PATH
   (`C:\Users\...\Python314\python.exe`), o job morre com
   "Vídeo sem legendas e faster-whisper não instalado". O `faster_whisper` está instalado só no
   `.venv` do projeto. Quem for rodar pela linha de comando precisa usar
   `.venv\Scripts\python.exe` (ou ativar o ambiente antes).
2. **Emoji derruba o job quando a saída não é UTF-8.** Com a saída do terminal em cp1252, a linha
   de log "🧠 Gemini lendo a transcrição…" levanta
   `'charmap' codec can't encode character '\U0001f9e0'` e o job inteiro para, depois da
   transcrição já estar pronta. Contornado com `PYTHONIOENCODING=utf-8`.
   Isso contraria a regra do projeto de que nada opcional pode derrubar o job inteiro — aqui quem
   derruba é a própria mensagem de progresso. **Não foi corrigido**, só registrado.

### Decisão do dono (2026-11-26)

**Sem emoji nos vídeos.** A sugestão do Gemini de "emoji contextual pontual" na legenda
(Frente 3, item 6) está **descartada** a pedido do dono. O mesmo vale para a ideia de emoji em
palavra-chave que está no roadmap. Fica na mesma linha das figurinhas, que já existem no código e
ficam desligadas por preferência dele.

O dono aprovou o resultado do clipe gerado com o destaque só por cor e `chars 18`.

### Conserto do emoji que derrubava o job (2026-11-26)

Novo `safe_print()` em `darkclip/pipeline.py`, usado pelo `Job.step()` e pelas duas linhas finais
da `darkclip/cli.py` (o título do corte vem da IA e também pode trazer emoji). Se o terminal não
conseguir escrever um caractere, ele vira `?` e o job segue; antes, o `print()` levantava
`UnicodeEncodeError` e matava o job depois da transcrição pronta.

**Reproduzido e conferido**, com a saída forçada em cp1252:

| | resultado |
|---|---|
| `print("\U0001F9E0 ...")` | `UnicodeEncodeError: charmap codec can't encode character` |
| `safe_print("\U0001F9E0 ...")` | escreve `? Gemini lendo a transcricao...` |

**CLI inteira rodada de novo sem o `PYTHONIOENCODING=utf-8`** (a condição que quebrava):
terminou, com a linha aparecendo como `? Gemini lendo a transcrição...`. Saída em
`data/jobs/20261126-213531-8754e/clip_01.mp4`, nota 82, gamer, 16,9 s, 6 cortes.

Isso não muda nada no vídeo: só o que aparece no terminal.

---

## 2026-11-26 — Refino das fronteiras do corte (a melhoria nº 1 do Gemini)

Implementado em `darkclip/ai.py`. Roda **depois** que o motor escolheu o trecho, para todos os
motores (Claude, Ollama, Gemini, momentos do Gemini e regras automáticas), dentro de
`select_clips()`. Envolvido em `try/except`: se falhar, o corte original passa e o job segue.

### As três regras

| função | o que faz |
|---|---|
| `_trim_opening()` | Pula até 3 trechos iniciais que são **só muleta** ("ah, então, tipo"), e só se ainda sobrar `min_s` de clipe. |
| `_finish_sentence()` | Termina a frase em curso em vez de cortar no meio dela. Vale para os dois motores; antes só a heurística fazia isso, via `_with_context`. |
| `_extend_tail()` | Se logo depois do fim há um pico de som ≥ 5 dB acima da **mediana do próprio corte**, estende até o som cair. |

O fim **nunca encurta**, tudo respeita `start + max_s + 8`, e um corte não invade o seguinte.
O que mudou fica registrado em `clip["edges"]`, por exemplo `{'desfecho': 3.78}`.

### Calibragem do limiar do som (medido, 15 janelas de 25 s de um vídeo de ação real)

| `rise` | disparou | extensão média | máxima |
|---|---|---|---|
| 3,0 dB | 14/15 | 2,25 s | 4,48 s |
| 4,0 dB | 10/15 | 1,74 s | 4,48 s |
| **5,0 dB** | **6/15** | **1,25 s** | **3,80 s** |
| 8,0 dB | 0/15 | — | — |

Escolhido 5,0 dB, que é o mesmo limiar que o `reacoes.py` já usa para achar reação.

### Trava que o teste obrigou a colocar

Com o limiar em 5 dB, os 6 disparos do rastro de som caíam **todos dentro de fala**: a regra não
estava pegando reação, estava pegando a frase seguinte, e o corte crescia uma frase por vez.
Numa rodada real da CLI isso esticou o corte de 37,42 s para 41,20 s, puxando a frase
"Tem nitro, tem nitro, tá", que não era o desfecho de nada.

Correção: pico que cai dentro de uma frase **que começa depois do fim** não conta. Terminar a frase
em curso é trabalho do `_finish_sentence`. Depois da trava, nas mesmas 15 janelas:

| | disparos |
|---|---|
| frase terminada | 14/15 (média +0,93 s, máx +2,62 s) |
| rastro de som | 1/15 |

### O que foi conferido

- Cinco casos sintéticos: enrolação no começo, frase cortada, risada depois do fim, caso em que
  aparar deixaria o clipe curto demais (não apara) e teto de `max_s` (respeitado).
- CLI inteira, três vezes, no mesmo vídeo. Na última rodada o Gemini escolheu 14,84 → 36,72 e o
  refino **não mudou nada** (`edges=None`) — o trecho já terminava em frase fechada e não havia
  pico fora de fala. É o comportamento conservador esperado.

### Limitação conhecida

`_trim_opening()` **nunca disparou** nos dados reais (0 de 15 janelas). Ele só sabe pular um
trecho inteiro, e os trechos da transcrição são frases ("Aí, entendeu?"), não muletas isoladas.
Para aparar a muleta **dentro** da primeira frase seria preciso tempo por palavra na seleção, que
hoje só existe depois, na hora de montar a legenda. Fica como ideia, não como coisa feita.
