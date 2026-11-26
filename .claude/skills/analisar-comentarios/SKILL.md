---
name: analisar-comentarios
description: Analisa os comentários de um vídeo do YouTube para descobrir quais partes mais chamam a atenção do público (timestamps citados, frases repetidas, reações como "kkkk" e 😂) e sugere os melhores trechos para cortes/Shorts. Use quando o usuário pedir para analisar comentários, descobrir a melhor parte de um vídeo pelo público, ou validar trechos antes de clipar.
---

# /analisar-comentarios

Descobre **onde o público presta atenção** num vídeo, a partir dos comentários.

## Como rodar

Na raiz do projeto DarkClip:

```bash
python -m darkclip.comments "<URL do vídeo>" --max 800 --lang pt --json /tmp/comentarios.json
```

- `--max`: quantos comentários ler (os mais curtidos vêm primeiro). 300–1000 é um bom intervalo; mais que isso fica lento e pode gerar erro 429 do YouTube.
- `--lang`: idioma da legenda usada para casar **frases citadas** com o momento exato da fala.
- `--no-transcript`: pula a legenda (só usa comentários com timestamp).

O script imprime um relatório em Markdown e, com `--json`, salva a análise completa (curva de atenção por segundo, picos e comentários de cada pico).

## Como o script pontua

| Sinal | Como é detectado | Peso |
|---|---|---|
| Timestamp citado (`2:31`, `1:02:10`) | regex no texto | 1 + ln(1 + curtidas) |
| Frase citada sem timestamp | ≥ 3 palavras significativas e ≥ 60% de sobreposição com a transcrição | ×0,8 |
| Reação (kkkk, 😂, "morri", "arrepiei", "melhor parte") | lista de padrões | ×1,3 |
| Comentário fixado | flag do YouTube | +1 |

Cada menção espalha atenção de 2 s antes até 18 s depois do instante citado, com pico em ~4 s. A curva é normalizada (0–1) e os picos ficam a pelo menos 25 s um do outro.

## Como apresentar ao usuário

1. Rode o script e leia o relatório. Se precisar de detalhes, leia o JSON.
2. Explique em português simples, para cada pico (até 5):
   - o intervalo (`m:ss–m:ss`) e a nota de atenção;
   - **o que o público diz** sobre aquele momento (cite 1–2 comentários curtos);
   - se vale um Short e por quê (reação forte, piada, revelação, polêmica).
3. Se houver poucos comentários ligados a momentos (`mapped` baixo), diga isso claramente: a análise vale pouco nesse vídeo. Sugira então o mapa de calor "Mais repetidos" ou a análise com IA do DarkClip.
4. Feche com os temas mais citados, que servem como ideias de títulos e ganchos.

## Integração com o DarkClip

A nota de cada clipe no DarkClip já usa este sinal (💬) junto com a IA, o heatmap e a energia do áudio. A opção "Analisar comentários" fica ligada por padrão no modo inteligente. Esta skill serve para investigar um vídeo **antes** de clipar, ou para explicar por que um trecho foi escolhido.

## Erros comuns

- `429 Too Many Requests`: o YouTube limitou os pedidos. Espere de 5 a 10 minutos ou reduza `--max`.
- `Sign in to confirm you're not a bot`: acontece em servidores e VPS. Rode no PC ou no celular, ou configure `DARKCLIP_COOKIES` (veja o README).
- Vídeo com comentários desativados: o relatório sai vazio. Avise o usuário.
