# Conectar suas contas (postagem automática)

> Faça isto **no PC**, uma vez só. Os tokens ficam salvos apenas no seu computador (`data/contas.json`).

## Facebook (Página) + Instagram (conta profissional)

**Antes:** você precisa ser administrador de uma **Página** do Facebook. Para o Instagram, a conta precisa ser **profissional** (Criador ou Empresa) e estar **ligada à Página**: no app do Instagram, Configurações → Central de Contas.

### 1. Criar o seu app na Meta (5 min, grátis)
1. Acesse **developers.facebook.com** → *Meus apps* → **Criar app**.
2. Escolha o caso de uso de **gerenciar Páginas / publicar conteúdo** (ou "Outro" → tipo **Empresa**), dê um nome (ex.: "DarkClip do Fulano") e crie.
3. Deixe o app em **modo de desenvolvimento**. Nesse modo ele funciona para você, que é administrador, **sem precisar de análise da Meta**.
4. Em *Configurações do app → Básico*, copie o **ID do app** e a **Chave secreta do app**.

### 2. Gerar o token
1. Abra o **Graph API Explorer** (developers.facebook.com/tools/explorer).
2. À direita, escolha o **seu app** em "Meta App".
3. Em **Permissões**, adicione:
   - `pages_show_list`, `pages_read_engagement`, `pages_manage_posts` (postar na Página);
   - `instagram_basic`, `instagram_content_publish` (postar no Instagram);
   - `business_management` (se a Página estiver num Gerenciador de Negócios);
   - se aparecer `publish_video`, marque também.
4. Clique em **Gerar token de acesso**, faça login, autorize a Página (e o Instagram) e **copie o token**.

### 3. Colar no DarkClip
Aba **🔗 Contas** → cole o ID do app, a chave secreta e o token → **Conectar Facebook/Instagram**.
O DarkClip troca o token curto por um de longa duração e lista suas Páginas e o Instagram ligado.

**Como posta:**
- **Facebook:** vídeos de até 90 s viram **Reels** da Página; acima disso, sobem como vídeo normal da Página, o formato bom para cortes longos de 1 a 3 minutos.
- **Instagram:** **Reels**, também no feed. O arquivo sai direto do seu PC.

## YouTube

> ⚠️ **Regra do Google:** apps não verificados (criados depois de 28/07/2020) só conseguem enviar vídeos **privados** pela API. O DarkClip envia e avisa; você abre o **YouTube Studio** no celular e muda para **Público** com um toque. Para liberar de vez, peça a auditoria do projeto em support.google.com/youtube/contact/yt_api_form.

1. Acesse **console.cloud.google.com** → crie um **projeto** (ex.: "darkclip").
2. *APIs e serviços → Biblioteca* → ative a **YouTube Data API v3**.
3. *Tela de consentimento OAuth*:
   - tipo **Externo**;
   - preencha nome e e-mail;
   - em **Usuários de teste**, adicione o **seu e-mail do YouTube**.
4. *Credenciais* → **Criar credenciais → ID do cliente OAuth** → tipo **App para computador** → copie o **Client ID** e o **Client secret**.
5. No DarkClip (**no PC**): aba **🔗 Contas** → cole os dois → **Conectar com Google** → autorize na janela do Google.

**Atenção:** enquanto o app estiver em "Teste" no Google, a autorização **vence a cada 7 dias**, e você precisa clicar em "Conectar com Google" de novo. Para não vencer, publique o app em *Tela de consentimento → Publicar app*. Vai aparecer um aviso de "app não verificado"; para uso pessoal, clique em *Avançado → continuar*.

## TikTok e Kwai
Não têm API aberta para postar sozinho: a do TikTok exige aprovação da empresa, e sem ela os posts ficam privados. Use **📤 Postar**: abre o app com o vídeo, e o texto já vai copiado.

## Como agendar
1. Aba **Resultados** → **📅 Planejar** no clipe → escolha a data e a conta → **OK** em "Postar automaticamente".
2. Na hora marcada o DarkClip envia sozinho. **O PC precisa estar ligado com o DarkClip aberto.**
3. Se der erro, ele tenta de novo 2 vezes (a cada 15 min) e mostra a mensagem na aba **📅 Canal**.

## Problemas comuns
| Mensagem | O que fazer |
|---|---|
| "token vencido ou sem permissão" | Gere um token novo no Graph API Explorer com todas as permissões e conecte de novo |
| "Nenhuma Página encontrada" | Ao gerar o token, marque a Página na tela de autorização |
| Instagram não aparece | A conta precisa ser profissional e estar ligada à Página |
| YouTube "renovar acesso… 7 dias" | Clique em Conectar com Google de novo (ou publique o app no Google Cloud) |
| Vídeo do YouTube ficou privado | Normal sem auditoria: mude para Público no YouTube Studio |
