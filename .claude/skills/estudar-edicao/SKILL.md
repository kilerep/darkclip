---
name: estudar-edicao
description: Estuda a edição de vídeos de referência (Shorts, Reels, cortes de canais que o dono admira) e transforma o que eles têm em comum num padrão de edição para o DarkClip, com ritmo de cortes, zoom, legenda, textos, sons, gancho e final. Use quando o usuário mandar links de vídeos de que gosta, pedir para aprender com a edição de outro canal, "copiar o estilo" de alguém, montar um padrão de edição, ou perguntar por que um vídeo prende tanto.
---

# /estudar-edicao

O objetivo é aprender a **técnica** (ritmo, zoom, texto, som, gancho, final) e transformar isso em ajustes do DarkClip. Nunca copie o vídeo, a marca, o nome, os personagens ou a identidade visual de outro canal. Se o usuário pedir para ficar "igual" a um canal, explique que vamos usar a técnica, não a identidade.

## 1. Medir cada vídeo (na raiz do projeto, com o `.venv` ativo)

```bash
python -m darkclip.estudo "LINK" --quadros 24
```

- Funciona com link (YouTube, TikTok, Instagram, Facebook, Kick) ou arquivo do PC.
- Gera em `data/estudos/<nome>/`: `RELATORIO.md` (números), `grade.png` (quadros do vídeo inteiro), `inicio.png` (os 3 primeiros segundos) e `dados.json`.
- Se o download pedir verificação ("confirme que não é robô"), peça ao usuário para atualizar o yt-dlp (rodar o `install_windows.bat` de novo) ou baixar o vídeo e passar o arquivo.
- Para analisar a fala com mais detalhe, use também `/assistir-video` no mesmo link.

## 2. Assistir de verdade

Para cada vídeo:
1. Leia o `RELATORIO.md`.
2. Leia `inicio.png` e `grade.png` com a ferramenta Read e olhe com atenção:
   - **legenda:** cor, tamanho, posição, palavras por vez, destaque;
   - **textos extras:** emojis, figurinhas, setas, molduras, nome do canal;
   - **zoom:** o enquadramento muda de tamanho entre quadros vizinhos;
   - **gancho:** o que aparece e o que está escrito nos 3 primeiros segundos;
   - **final:** loop, pergunta ou chamada para seguir.
3. Separe o que você **mediu** (números do relatório) do que você **viu** nos quadros e do que é **palpite**. Entre dois quadros pode ter acontecido algo que você não viu; diga isso.

## 3. Encontrar o padrão

Com 3 ou mais vídeos, monte uma tabela comparando: cortes por minuto, cena média, primeiro corte, silêncio, palavras por minuto, estilo de legenda, uso de zoom, textos e figurinhas, gancho e final. O padrão é o que se repete em **pelo menos 2 vídeos**. O que aparece em um vídeo só é estilo daquele canal, não padrão.

## 4. Registrar

Atualize `docs/ESTUDO_EDICAO.md`:
- uma linha por vídeo na tabela (status ✅ analisado);
- uma seção "Padrão encontrado" com o resumo;
- uma seção "Receita para o DarkClip" com as opções que reproduzem o padrão:

| No vídeo de referência | Opção no DarkClip |
|---|---|
| Cenas de 2–3 s, fala sem pausas | Remover silêncios ✅, Zoom de impacto ✅ |
| Abre com o momento mais forte | 🎣 Gancho: ⏩ Prévia |
| Termina emendando no começo | Final: 🔁 Loop |
| Legenda grande amarela, 2–3 palavras | Estilo: Amarela (palavra atual) |
| Moldura com título fixo | Modelo 📰 Manchete (aba Canal) |
| Muitos textos e sons de meme | Segunda passada com `/editar-video` |

## 5. Mudar o sistema (só com o OK do usuário)

Mostre a receita e pergunte antes de mexer no código. Mudanças possíveis, das mais simples para as mais complexas:
1. **Só usar as opções certas:** muitas vezes o padrão já existe no app. Diga quais escolher.
2. **Mudar padrões do app:** valores iniciais das caixinhas (`web/index.html`), força do zoom (`render.zoom_cuts`/`zoom_expr`), frequência dos efeitos sonoros (`sfx.events_for`).
3. **Recurso novo** (ex.: figurinhas de reação, texto pop-up automático): descreva, estime o trabalho e peça confirmação.

Depois de mudar, rode um corte de teste e compare com os números do estudo, usando `python -m darkclip.estudo clip_01.mp4` no corte gerado. Termine dizendo, em português simples, o que mudou e o que o usuário deve testar.
