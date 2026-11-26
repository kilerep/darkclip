# 🎞️ Biblioteca de estudo de edição

Vídeos de referência que o dono do projeto curte. A ideia é estudar **a técnica** (ritmo, zoom, texto, som, gancho) e transformar isso em regras do DarkClip. Não copiar vídeo, estilo exato nem identidade de canal.

| Referência | Formato | Cena média | 1º corte | Silêncio | Fala | Status |
|---|---|---|---|---|---|---|
| Victor Ludgero — "Matinho, Moisés e Nicolas Cage: GTA V" (https://youtu.be/u2ZjE2axBSY) | horizontal, 12 min | 5,05 s (13/min) | 10,9 s (texto aos 1,5 s) | 0,8% | 83/min | ✅ analisado |
| HAYLIGHTS, edição de thiagod (https://youtu.be/np795dBR79c) | horizontal, 24 min | 1,52 s (44/min) | 1,65 s | 3,5% | 108/min | ✅ analisado |
| oguxtamedia — "A saga da BMW batida do Celso" (https://youtube.com/shorts/bqm5QxQMpCw) | vertical, 2 min 36 s | 1,73 s (35/min) | 1,0 s | 4,5% | 248/min | ✅ analisado |
| oguxtamedia — "ACF fez na remap na máquina de refrigerante" (https://youtube.com/shorts/DuXiMLo5bHA) | vertical, 2 min 22 s | 1,81 s (33/min) | 1,2 s | 0,7% | 189/min | ✅ analisado |
| Canal player94 | — | — | — | — | — | ⏳ aguardando links |

## Como analisar (no PC)
Na pasta do DarkClip, com o `.venv` ativo, rode um comando por vídeo:

```bash
python -m darkclip.estudo "LINK DO VIDEO" --quadros 24
```

Depois, no Claude Code, peça: **/estudar-edicao**. Ele lê os relatórios e as imagens, encontra o padrão e escreve a "Receita para o DarkClip" aqui.

## Observações do print (oguxtamedia)
- Legenda **amarela, grande, com contorno preto**, no terço do meio-baixo, uma frase por vez. Já existe parecido no DarkClip: estilo "Amarela (palavra atual)".
- **Figurinha de desenho** (anime) ao lado da legenda, como reação. O DarkClip ainda não tem figurinhas.
- **Nome do canal** em texto grudado no topo, com contorno, como marca.
- **Close no rosto** do personagem, fundo de garagem de carros: a história é contada com a pessoa em destaque.
- Limite: é só um quadro. Ritmo, zoom, cortes e som precisam do vídeo inteiro.

## Padrão encontrado (4 vídeos, 25/11/2026)
O que se repete em pelo menos 2 vídeos:
1. **Algo novo antes de 1,5 s** (4/4): corte, texto ou meme logo no começo.
2. **Figurinhas e memes de reação** (4/4): imagens pequenas junto da frase (oguxtamedia, em quase todo quadro), memes em tela cheia (sol com rosto no Ludgero, colagem no HAYLIGHTS).
3. **Quase sem pausas** (4/4): 0,7% a 4,5% de silêncio.
4. **Texto curto por frase** (3/4): 2 a 4 palavras, contorno preto. Ludgero: branco, centro, só nas frases engraçadas. oguxtamedia: amarelo/branco itálico, quase o tempo todo.
5. **Comentários do editor** em estilo diferente (3/4): "*100% modo sério*", "ACF horas depois:", "QUE ISSO ACF KKKKK" (laranja, grande, inclinado).
6. **Close/zoom no rosto na reação** (3/4): HAYLIGHTS corta para o rosto em tela cheia; oguxtamedia dá zoom no rosto e no gesto.
7. **Cena nova a cada 1,5–2 s nos Shorts** (3/3 Shorts/compilações).
8. **@ do canal na tela** (3/4).
9. **Série / suspense no final** (2/4): "PARTE 6 de 7", "não será a única coisa quebrada nesta saga".
10. **Troca de layout no momento forte** (2/4): Ludgero esconde a webcam na frase; HAYLIGHTS corta para o rosto.

## Receita para o DarkClip
Já dá para usar hoje: duração Curtos/Auto, Remover silêncios ✅, Zoom ✅, Efeitos sonoros ✅, Gancho 🎮 Começa na ação ou ⏩ Prévia, modelo com @ do canal.
Construído (25/11): 🔍 zoom no rosto na reação (gamer: webcam em tela cheia) e estilo de legenda **Frases**.
Descartado pelo dono: figurinhas de reação.
Próximos: comentários do editor escritos pela IA ("*100% modo sério*") → final de série ("PARTE 1" + suspense).
