---
name: editar-video
description: Edita cortes de gameplay e Shorts/Reels como um editor de CapCut/Submagic, aplicando zoom de impacto, tremor, câmera lenta ou acelerada, quadro congelado com texto, texto pop-up ("KKKK", "ELE NÃO VIU 💀"), efeitos sonoros e aparo, sempre em cima dos momentos certos do clipe. Use sempre que o usuário pedir para editar, melhorar, deixar mais dinâmico, "dar uma tapa", colocar efeito, meme, zoom, slow, texto ou som em um vídeo ou clipe do DarkClip, ou quando reclamar que um corte ficou parado ou sem graça, mesmo que não diga a palavra "editar".
---

# /editar-video

O DarkClip já entrega o clipe com legenda, jump cuts, zoom alternado e whoosh. Esta skill é a **segunda passada**: você assiste o clipe, encontra os 2–4 momentos que merecem destaque e aplica efeitos pontuais, como um editor humano faria. O objetivo é retenção: quem assiste não pode sentir vontade de arrastar para o próximo vídeo.

As ferramentas estão em `scripts/editar.py` (só ffmpeg + módulos do DarkClip; não precisa de chave de API). Rode tudo **da raiz do projeto DarkClip**. Cada comando grava um arquivo novo e **nunca altera o original**.

## 1. Achar o clipe

- Clipes do app ficam em `data/jobs/<id>/clip_01.mp4`, `clip_02.mp4`… O job mais recente é a pasta com data mais nova.
- Ao lado de cada clipe existe `clip_XX.ass`: a legenda já no **tempo final do clipe** (depois dos jump cuts). Leia esse arquivo para saber o segundo exato de cada fala. É bem mais confiável que o `transcript.json`, cujos tempos são do vídeo original.
- Se o usuário mandou um arquivo próprio, use o caminho dele.

## 2. Assistir antes de mexer

```bash
python .claude/skills/editar-video/scripts/editar.py info clip_01.mp4
python .claude/skills/editar-video/scripts/editar.py quadros clip_01.mp4 --n 12
```

- `info` mostra resolução, duração, volume (LUFS), silêncios e tela preta, e já aponta problemas.
- `quadros` gera **uma imagem em grade** com N quadros e imprime o segundo de cada um. Leia a imagem com a ferramenta Read. Para olhar um trecho de perto, use `--de 8 --ate 14 --n 8`.
- Junte o que se vê (quadros) com o que se fala (`.ass`) e escreva para si a **linha do tempo**: setup → tensão → **clímax/reação** → desfecho.

## 3. Planejar (antes de rodar qualquer efeito)

Monte uma lista curta, no máximo um efeito forte a cada ~4 s. Efeito demais cansa e parece amador. Veja `references/receitas.md` para saber que efeito combina com cada momento. Resumo:

| Momento no clipe | Efeito | Comando |
|---|---|---|
| Reação/grito, "NÃO!", susto | zoom rápido + hit | `zoom --em T --dur 1 --forca 1.3 --som` |
| Explosão, batida, falha absurda | tremor curto | `tremor --em T --dur 0.5 --som` |
| Jogada épica, "olha isso" | câmera lenta | `lento --em T --dur 1.5 --fator 0.5` |
| Espera chata (carregando, andando) | acelerar | `lento --em T --dur 4 --fator 2` |
| Antes do desastre ("ele não sabia…") | quadro congelado + texto | `congelar --em T --dur 1 --texto "ELE NÃO VIU 💀" --som` |
| Piada, fala marcante | texto pop-up | `texto --em T --dur 1.5 --texto "KKKKK" --pos topo` |
| Troca de cena sem som | whoosh | `som --em T --tipo whoosh` |
| Começo morno / fim arrastado | aparar | `aparar --de 1.2 --ate 47` |

Regras que importam:
- **Os 3 primeiros segundos são o gancho.** Se o clipe começa parado, apare o início ou coloque o primeiro efeito antes de 1,5 s.
- **O efeito cai NO momento, não depois.** Use o tempo da palavra no `.ass` ou o quadro exato; o zoom entra ~0,1 s antes do pico.
- **Texto na tela não pode cobrir a legenda** (que fica perto do meio/baixo). Prefira `--pos topo` para textos extras.
- Câmera lenta e quadro congelado **mudam a duração** e deslocam tudo o que vem depois: aplique-os **por último**, do fim para o começo, ou recalcule os tempos.
- Não repita o mesmo efeito duas vezes seguidas. Variar é o que dá ritmo.

## 4. Aplicar em cadeia

Cada passo usa a saída do anterior. Use `-o` para nomes claros e termine com `_editado.mp4`:

```bash
E=.claude/skills/editar-video/scripts/editar.py
python $E zoom     data/jobs/X/clip_01.mp4 --em 3.4 --dur 1 --som           -o /tmp/p1.mp4
python $E texto    /tmp/p1.mp4 --em 9.2 --dur 1.5 --texto "KKKKK" --pos topo -o /tmp/p2.mp4
python $E congelar /tmp/p2.mp4 --em 21.0 --dur 1 --texto "ELE NÃO VIU 💀" --som -o data/jobs/X/clip_01_editado.mp4
```

No Windows (cmd), troque `$E` pelo caminho inteiro e use pastas do próprio projeto em vez de `/tmp`.

## 5. Conferir e entregar

1. `info` no arquivo final: a duração faz sentido? O volume ficou perto de -14 LUFS?
2. `quadros` no final, focando nos trechos editados, e **olhe as imagens**. O zoom está no rosto/ação? O texto está legível e sem cobrir a legenda?
3. Responda ao usuário em português simples:
   - o que você mudou e em que segundo (lista curta);
   - por que cada efeito ajuda (ex.: "zoom no grito para a reação bater mais forte");
   - onde está o arquivo final;
   - o que ele pode pedir de diferente ("quer o texto em vermelho?", "mais exagerado?").

## Quando NÃO usar o script

Mudanças estruturais ficam melhores no próprio DarkClip, que refaz tudo junto (legenda, jump cuts, zoom alternado):
- mudar início/fim, enquadramento (gamer, blur, seguir rosto), estilo da legenda ou gancho → botão **✏️ Editar** no app (aba Resultados) e "Refazer";
- legenda errada → corrija no editor do app e refaça;
- só depois disso aplique os efeitos desta skill no clipe novo.

## Problemas comuns

- `ffmpeg falhou` com `ass`: o ffmpeg não tem libass; rode `python -m darkclip.doctor`.
- Texto com emoji aparece como quadrado: a fonte do sistema não tem emoji. Use texto sem emoji ou troque por "!!!".
- Efeito no lugar errado depois de um `lento`/`congelar`: os tempos mudaram; recalcule a partir do arquivo novo com `quadros`.
