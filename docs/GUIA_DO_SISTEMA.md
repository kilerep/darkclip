# 📖 Guia do DarkClip: o que cada função faz

O DarkClip é uma fábrica de cortes que roda no seu PC. Você entrega um vídeo longo (link ou arquivo) e ele devolve Shorts/Reels prontos: escolhidos, enquadrados em pé, legendados, editados e, se quiser, agendados nas redes.

---

## Como ele trabalha (o caminho de um vídeo)

1. **Baixa só o necessário.** Primeiro lê a legenda e o mapa "mais repetidos" do YouTube, sem baixar o vídeo. Depois baixa só os trechos escolhidos.
2. **Transcreve.** Usa a legenda do YouTube ou, se estiver no idioma errado ou não existir, o Whisper no seu PC. Se a legenda veio escrita por frase (TED, legendas manuais), o DarkClip confere se ela está no tempo da fala e corrige o atraso. Depois, em cada corte escolhido, o Whisper escuta o trecho para a legenda mostrar exatamente o que é dito, no tempo certo.
3. **Junta sinais.** Partes mais repetidas, comentários que citam minutos, risadas e gritos no áudio, chat da live e o Gemini assistindo o vídeo.
4. **Escolhe os cortes.** Uma IA lê tudo isso e escolhe os melhores trechos, com começo, meio e fim. Ela segue o seu **Perfil do canal** e as suas **notas 👍/👎**.
5. **Edita.** Coloca o vídeo em pé (seguindo o rosto, webcam + jogo ou fundo desfocado), legenda animada, cortes de silêncio, zoom, efeitos sonoros, gancho e barra de progresso.
6. **Entrega e agenda.** O corte aparece em Resultados. Dali você baixa, posta ou agenda.

### Quem escolhe os cortes (do melhor para o mais simples)
| Ordem | Motor | Quando entra |
|---|---|---|
| 1 | **Claude** | Se houver chave do Claude no `.env` |
| 2 | **Ollama** (IA offline no PC) | Se estiver configurado |
| 3 | **Gemini lendo a transcrição** | Sem Claude, com chave do Gemini |
| 4 | **Momentos que o Gemini viu** | Se as IAs de texto falharem |
| 5 | **Regras automáticas** | Sempre funciona, sem internet nem chave |

Se o Gemini estiver lotado (erro 503), o DarkClip espera, tenta de novo e troca para um modelo reserva sozinho.

---

## ✂️ Aba Clipar

**O que fazer:**
- **✂️ Cortes com IA**: o modo principal; acha e edita os melhores trechos.
- **💬 Só legendar**: coloca legenda animada no vídeo inteiro, sem cortar.
- **🔇 Tirar silêncios**: remove as pausas do vídeo inteiro.
- **🔍 Analisar vídeo**: um relatório do vídeo (o que acontece, melhores momentos), sem gerar cortes.

**Links dos vídeos:** um por linha. Funciona com YouTube, Facebook, TikTok, Instagram, Kick e outros. Também dá para **enviar um arquivo** do PC.

**Duração dos cortes:**
| Opção | Para quê |
|---|---|
| Auto (20–60s) | Shorts em geral |
| Curtos (15–30s) | Piadas e reações rápidas |
| **Longos (45–90s)** | **Gameplay com contexto** (o recomendado para você) |
| Facebook (1–3 min) | Vídeos mais longos para o Facebook |
| Podcast (9–16 min) | Cortes longos de conversa |
| Personalizado | Você escolhe o mínimo e o máximo |

**Quantidade de cortes:** de 1 a 30. Se o vídeo for curto, sai o máximo que couber sem repetir trecho.

**Proporção:** 9:16 (Shorts/Reels/TikTok), 4:5 (feed), 1:1 (quadrado) ou original.

**Distância da câmera:** Padrão ou Mais longe (mostra mais do cenário).

**Enquadramento:**
| Opção | O que faz |
|---|---|
| **Automático ✨** | Decide sozinho, cena por cena (o recomendado) |
| Seguir rosto | Câmera virtual que acompanha a pessoa. Se o rosto some por mais de 1 s (de costas, de lado, plateia), mostra o quadro inteiro até ele voltar, em vez de ficar parada num braço |
| Tela dividida | Duas pessoas, uma em cima e outra embaixo |
| 🎮 Gamer | Webcam em cima, jogo embaixo. Se a webcam ocupar a tela inteira, troca para o rosto só naqueles segundos |
| Fundo desfocado | Mostra a tela inteira com fundo borrado em cima e embaixo |
| Corte central | Só o meio da tela, sem faixas |

**⏱️ Só um pedaço / dividir em partes:** para lives longas. Escolha De/Até ou divida em partes de 15, 30 ou 60 min (o DarkClip corta cada parte em ordem).

**🎣 Gancho e Final:** como o corte prende no começo e termina. Detalhes em [GANCHOS.md](GANCHOS.md).
- Gancho: 🤖 Automático (a IA escolhe por corte), ⏩ Prévia do melhor momento (abre com 2–3 s do clímax e volta ao começo), ❓ Pergunta, ⏳ Espera até o fim, 😱 Afirmação chocante, 🎬 POV, 🎮 Começa na ação, ou Sem gancho.
- Final: 🤖 Automático, 🔁 Loop (o fim se dissolve no primeiro quadro e o replay parece continuação) ou Normal.

**O que procurar? (opcional):** um pedido para este vídeo, ex.: "a parte do susto".
**Nicho do canal:** ajuda a IA e gera as hashtags.
**Idioma das legendas:** Português, Inglês ou Espanhol.
**Estilo da legenda:** Amarela (palavra atual), Verde, Caixa vermelha, Minimalista ou **Frases** (amarela em itálico, 2–4 palavras por vez, sem destaque palavra a palavra, o estilo dos Shorts estudados).

**Caixinhas** (o app lembra suas escolhas):
| Caixinha | O que faz |
|---|---|
| Legenda animada | Legenda palavra por palavra |
| Remover silêncios | Tira pausas sem fala, mas mantém sons altos do jogo |
| Zoom de impacto | Zoom alternado que dá ritmo |
| 🔊 Efeitos sonoros | Whoosh nos cortes e impacto no gancho (gerados por código, sem direitos autorais) |
| Visual dark | Mais contraste e borda escura. **Desligue para gameplay** |
| Gancho no topo | Frase de impacto nos 3 primeiros segundos |
| Barra de progresso | Barrinha que segura a pessoa até o fim |
| 🔍 Zoom no rosto na reação | Nos gritos, sustos e risadas, o vídeo aproxima por ~1,5 s. No modo 🎮 Gamer, corta para a webcam em tela cheia (técnica do HAYLIGHTS) |
| Download inteligente | Baixa só os trechos (muito mais rápido) |
| 💬 Comentários e chat | Lê o que o público mais comentou |
| 👁️ Gemini assiste o vídeo | A IA vê imagem e som (grátis com link do YouTube durante a prévia do Google) |

**Trilha de fundo:** uma música sua, baixinha por baixo da fala.

---

## 🎙️ Aba História

Cria Shorts narrados do zero, sem vídeo de origem.
- **💡 Ideias para hoje:** a IA sugere temas para o seu nicho, usando o que está em alta no Brasil (Google Trends).
- **Tema:** a IA escreve o roteiro.
- **Formato:** História (mistério, caso real), 🏆 Top 5, 🤯 3 curiosidades, ❓ Quiz (A, B ou C) ou 🎯 Desafio.
- **…ou cole seu roteiro pronto.**
- **Voz:** narração gerada por IA (grátis).
- **Vídeo de fundo e trilha:** opcionais.

---

## 🎬 Aba Resultados

Cada trabalho mostra o progresso e, no fim, os cortes.
- **📜 Ver detalhes:** cada passo do que o DarkClip fez, inclusive o motor que escolheu e o custo de IA.
- **💡 Como resolver:** quando dá erro, aparece a dica do que fazer.

Em cada corte:
| Item | O que é |
|---|---|
| Nota (número vermelho) | Chance de viralizar, juntando IA e sinais do público |
| Chips | 🔥 parte mais repetida, 💬 comentários, 👁️ Gemini, ⚡ energia do áudio, enquadramento usado, segundos de silêncio cortados, tipo de gancho (⏩ prévia, ❓ pergunta…) e 🔁 loop |
| Gancho / Fluxo / Valor / Tendência | Notas de 0 a 100 dadas pela IA (quando uma IA escolheu o corte) |
| Descrição / por que viraliza | Texto do post e o motivo da escolha |
| 📤 Postar | Abre o compartilhamento do celular com o vídeo e o texto |
| ⬇️ Baixar · 📋 Copiar texto | Baixa o vídeo · copia título, descrição e hashtags |
| ✏️ Editar | Muda início/fim (botões −1/+1), texto e tipo do gancho, final (loop), título, palavras em destaque, enquadramento, legenda, e refaz só esse corte |
| 📅 Planejar | Coloca no calendário da aba Canal |
| **👍 / 👎 + motivo** | **Ensina o seu gosto.** As notas viram exemplos para a IA, e 2 reclamações de "Começa sem contexto" fazem os cortes recuarem mais no começo |

**🎨 Versões para as redes** (em cada corte) e **🎨 Versões de todos** (no trabalho): geram o corte com os modelos escolhidos na aba Canal. Cada versão aparece com miniatura, os ícones das redes que vão usá-la, ⬇️ Baixar e 📤 Postar. Na postagem automática, cada rede recebe a sua versão sozinha. Redes com "Tela cheia" usam o corte normal, sem gerar nada a mais. Se você editar o corte, as versões somem e precisam ser geradas de novo.

**📅 Agendar todos:** espalha todos os cortes de um trabalho no calendário.

---

## 📅 Aba Canal (Central do Canal)

- **📈 Meu canal:** cole o link do canal; o DarkClip lê inscritos, Shorts e views (grátis, sem senha).
- **🎯 Perfil do canal:** o que é um bom corte para você. Vale para **todos** os cortes, sem repetir.
- **💰 Caminho da monetização:** quanto falta para o Programa de Parcerias do YouTube.
- **🧠 O que funciona no seu canal:** compara seus Shorts por duração, horário, estilo de legenda, enquadramento e formato, usando as views reais (precisa de pelo menos 4 Shorts postados), e mostra o resumo das suas notas 👍/👎.
- **📅 Próximos posts / Horários de postagem:** calendário; você define os horários (ex.: 12:00, 18:00, 21:00) e quantos posts por dia. Com conta conectada e "postar sozinho", o DarkClip publica na hora (o PC precisa estar ligado).
- **🏆 Mais vistos / ✅ Já postados:** histórico do canal.
- **🎨 Modelos por rede:** o mesmo corte com uma cara diferente em cada rede. Você escolhe um modelo para TikTok, YouTube, Instagram, Facebook e Kwai, escreve o @ do canal e, se quiser, envia uma imagem de fundo. As prévias mostram como cada modelo fica.

| Modelo | Como fica |
|---|---|
| 🎬 Tela cheia | O corte normal, ocupando a tela toda |
| 📰 Manchete | Título fixo em cima, vídeo em cartão, @ embaixo, fundo desfocado do próprio vídeo |
| 🃏 Cartão degradê | Fundo degradê animado roxo e rosa, borda branca, legenda em caixa |
| ⚡ Neon gamer | Fundo escuro com degradê ciano, borda neon, legenda verde |
| ⬛ Minimal | Fundo preto, vídeo grande, só o @ e legenda discreta |
| 🖼️ Meu fundo | A sua imagem de fundo, com título e @ |

Cada modelo também troca o estilo da legenda, para as versões ficarem bem diferentes. Se o gancho dos 3 primeiros segundos repetir o título fixo, ele some para não aparecer duas vezes.

---

## 🔗 Aba Contas

- **📘 Facebook + 📸 Instagram:** conecta pela Meta (ID do app, chave secreta e token). Posta Reels e vídeos.
- **▶️ YouTube:** conecta pelo Google (Client ID e secret). Projetos não verificados pelo Google sobem como **privado**.
- **🎵 TikTok · Kwai:** não têm API aberta. Use 📤 Postar: abre o app com o vídeo e o texto copiados.

Os tokens ficam só no seu PC (`data/contas.json`).

---

## ⚙️ Aba Ajustes

- **Endereço do servidor e token:** para o celular falar com o PC.
- **❓ Problemas comuns:** respostas rápidas para os erros mais frequentes.

---

## Fora do app

| Arquivo / comando | Para quê |
|---|---|
| `install_windows.bat` | Instala ou atualiza os programas |
| `start_windows.bat` | Abre o DarkClip |
| `verificar_windows.bat` | Diagnóstico: mostra ✅/❌ de cada peça, testa a chave do Gemini e confere se o detector de rostos YuNet está funcionando |
| `registrar_claude_windows.bat` | Liga o DarkClip ao Claude Code (uma vez só) |

### 🤖 O Claude usando o DarkClip (servidor MCP)
Depois de registrar, o Claude Code ganha estas ferramentas:
| Ferramenta | O que faz |
|---|---|
| `status` | Confere se o DarkClip está aberto |
| `cortar_video` | Cria cortes de um link ou arquivo (com gancho e final à escolha) |
| `esperar_job` | Acompanha até ficar pronto |
| `ver_job` / `listar_jobs` | Mostra os trabalhos e os cortes |
| `avaliar_corte` | Dá 👍/👎 com motivo |
| `editar_corte` | Refaz um corte (início, fim, gancho, título, enquadramento) |
| `agendar_corte` | Coloca no calendário ou posta sozinho |
| `gerar_versoes` | Gera as versões com os modelos de cada rede |
| `ver_canal` / `definir_perfil_do_canal` | Lê e muda o perfil do canal |

### Skills do Claude Code (dentro da pasta do projeto)
| Skill | O que faz |
|---|---|
| `/assistir-video` | O Claude "assiste" um vídeo por quadros + fala e explica o que acontece |
| `/analisar-comentarios` | Descobre pelos comentários as partes que o público mais curtiu |
| `/editar-video` | Segunda passada de edição: zoom, tremor, câmera lenta, quadro congelado com texto, texto pop-up e sons |

---

## Arquivo `.env` (configurações)
| Linha | Para quê |
|---|---|
| `GEMINI_API_KEY` | Chave do Gemini (grátis) |
| `ANTHROPIC_API_KEY` | Chave do Claude (opcional, paga) |
| `DARKCLIP_GEMINI_FALLBACKS` | Modelos reserva quando o Gemini está lotado |
| `DARKCLIP_WHISPER_MODEL` | `base` (rápido), `small` (padrão) ou `medium` (mais preciso) |
| `DARKCLIP_TOKEN` | Senha do app (criada sozinha) |
| `DARKCLIP_OLLAMA_MODEL` | IA offline (opcional) |

## Postar o mesmo conteúdo em várias redes
- Postar o **seu próprio** vídeo em várias redes é permitido. O que as redes derrubam é repost de conteúdo de outras pessoas e vídeo com marca d'água de outro app. O DarkClip nunca coloca marca d'água.
- Os modelos dão uma cara própria ao seu canal em cada rede, mas **não tornam original** um corte de vídeo de outro criador. O Facebook diz que reduz o alcance de conteúdo não original. O que pesa é a sua edição, o seu comentário e ter permissão para cortar o conteúdo.

## Segurança
- As chaves e tokens **nunca** aparecem no "Ver detalhes" nem nos erros: o DarkClip troca por •••.
- Antes de mexer no `.env`, ele guarda uma cópia em `.env.bak`.

## Custos
- **Gemini com link do YouTube:** grátis durante a prévia do Google.
- **Claude:** pago por uso. O "📜 Ver detalhes" mostra o custo real de cada trabalho.
- **Regras automáticas, Whisper, edição e efeitos:** grátis, rodam no seu PC.
