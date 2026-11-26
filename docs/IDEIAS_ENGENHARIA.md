# 🧩 Ideias de engenharia tiradas de sistemas abertos

Fonte principal: **morluto/rea** (REA: Reverse Engineer Anything, licença MIT), lido em modo somente leitura.
Regra do estudo: aprendemos com código aberto e com páginas públicas de produtos. **Não** desmontamos produtos fechados (como o Cut.Pro) para copiar a implementação. O próprio REA proíbe isso no `DISCLAIMER.md`.

## Ideias para o DarkClip (da mais simples para a mais ampla)

1. **Separar observação de palpite nos motivos dos cortes.** O REA separa observações, derivações, inferências e dúvidas (`AGENTS.md`). No DarkClip, cada "motivo" do corte poderia marcar o que veio da transcrição (fato) e o que veio da IA (palpite). Assim você sabe em que confiar.
2. **Erros com código padrão.** O REA tem um contrato de erro em JSON (`docs/error-contract.schema.json`). Hoje nossos erros são frases em português. Com códigos fixos (ex.: `GEMINI_OCUPADO`, `SEM_LEGENDA`), o app e o Claude conseguem agir sozinhos.
3. **Backup antes de alterar arquivos.** O REA exige que mudanças de configuração sejam aditivas, idempotentes e com backup, e que o instalador mostre o que vai mudar antes de escrever (`AGENTS.md`). Podemos aplicar isso no `.env` e nos scripts de instalação.
4. **Um provedor de IA com interface única.** O REA separa os provedores em `src/providers`. No DarkClip, Claude, Gemini e Ollama hoje têm regras espalhadas. Uma interface comum (`escolher_cortes`, `ver_video`, `resumir`) facilitaria trocar ou adicionar modelo, e o plano de reservas do Gemini ficaria no mesmo lugar.
5. **Mesmo fluxo pela linha de comando e pelo Claude.** O REA usa os mesmos fluxos pelo CLI e pelo MCP (`mcp.json`). O DarkClip já tem CLI e servidor web. Um adaptador MCP deixaria o Claude cortar, editar e agendar sem depender da tela.
6. **Ocultar chaves nos registros.** O REA remove credenciais de saídas e evidências. Vale revisar se as chaves e tokens do DarkClip nunca aparecem no log de detalhes ou em erros. (Ainda não verificado.)

## O que não entra
- Ferramentas para analisar apps de terceiros sem autorização, como desmontar o Cut.Pro ou outros produtos fechados.
- Qualquer coisa que contorne proteção, licença ou controle de acesso.

## Ideias de fontes públicas do Cut.Pro (documentação, ajuda e blog)
Lido só o que está publicado para o usuário: documentação da API e do MCP, central de ajuda e blog. Nenhum código interno.

7. **Fluxo de trabalho em etapas, como ferramentas do MCP.** A documentação mostra a sequência `analisar vídeo → criar envio → ver envio → listar cortes → renderizar → baixar`. Isso dá para o Claude usar passo a passo, com cada etapa conferível. Pode virar um servidor MCP local para o DarkClip (como o `npx` deles, mas rodando no seu PC).
8. **Mostrar o preço (ou o custo de IA) antes de gastar.** A documentação diz que o assistente mostra o total e só cobra depois do "sim". Para nós: estimar o custo antes de analisar um vídeo longo.
9. **Central de ajuda dentro do app.** A ajuda deles tem perguntas prontas, como "Meu clipe não fica pronto ou deu erro". Podemos fazer o mesmo com os erros mais comuns do DarkClip: Gemini ocupado, YouTube pedindo verificação, legenda faltando.
10. **Monitorar canal ou live e cortar em lotes.** A API tem uma rota para isso. É o caso das lives da Kick. Ainda precisamos ver se a detecção funciona com a Kick.
11. **Limites e erros documentados.** Eles têm páginas de "Erros" e "Limites de requisição". Reforça o item 2 das ideias de engenharia (códigos de erro fixos).
12. **Miniatura personalizada no Short.** O blog diz que o YouTube liberou miniatura própria nos Shorts para todos os criadores. Já geramos uma miniatura no DarkClip (`thumbnail()`); vale ver se a API do YouTube aceita enviá-la junto com o vídeo.
13. **Conteúdo editado, não repost.** O blog afirma que "a fazenda de repost acabou, o corte editado não". Isso confirma a estratégia do seu canal: cortes com edição própria, com técnica e comentário, e não só recortes do vídeo original.
