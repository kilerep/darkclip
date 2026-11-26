# Tutorial: instalar o DarkClip no PC (Windows 10/11)

⏱️ **Tempo:** 20–40 min na primeira vez, quase tudo esperando downloads · 💾 **Espaço:** ~5 GB livres · 🌐 Internet ligada

> **Já tem o DarkClip instalado?** Pule para [Atualizar para uma versão nova](#atualizar-para-uma-versão-nova). Leva 2 minutos.

---

## Passo 1: Baixar e extrair
1. Baixe o arquivo **`darkclip.zip`** mais recente da conversa com o Claude.
2. Abra a pasta **Downloads**, clique com o botão direito no `darkclip.zip` → **Extrair tudo…**
3. No campo do destino, apague o que estiver escrito e digite **`C:\deploy`** → **Extrair**.
   Vai ficar a pasta **`C:\deploy\darkclip`**.
   > Por que fora da Área de Trabalho? Assim o OneDrive não atrapalha.

## Passo 2: Instalar
1. Abra a pasta **`C:\deploy\darkclip`** e dê **dois cliques** em **`install_windows.bat`**.
2. Se aparecer **"O Windows protegeu o computador"** → **Mais informações** → **Executar assim mesmo**.
3. Uma janela preta instala tudo sozinha: Python, ffmpeg, Node.js e as bibliotecas.
   - **Se ela disser "Python instalado. FECHE esta janela…"**: feche e dê dois cliques no `install_windows.bat` **de novo**. Isso é normal na primeira vez.
   - Se o Windows pedir permissão, clique em **Sim**.
   - As bibliotecas levam **5–10 minutos**. Não feche a janela.
4. No fim aparece **"===== PRONTO! ====="**. Se aparecer **"REINICIE o PC"**, reinicie uma vez.

> Se der erro vermelho ou a janela fechar sozinha: tire um **print** e mande no chat.

## Passo 3: Colocar a chave grátis do Gemini (a IA que assiste os vídeos)
1. Acesse **aistudio.google.com/apikey** e entre com sua conta Google.
2. Clique em **Create API key** e copie a chave (começa com `AIza…`).
3. Na pasta `C:\deploy\darkclip`, clique com o botão direito no arquivo **`.env`** → **Abrir com** → **Bloco de Notas**.
4. Na linha `GEMINI_API_KEY=`, cole a chave **logo depois do `=`**, sem espaço:
   ```
   GEMINI_API_KEY=AIzaSy...sua chave...
   ```
5. **Salve** (Ctrl+S) e feche.

> A chave do Claude (`ANTHROPIC_API_KEY`) é opcional. Sem ela, o Gemini escolhe os cortes e, se ele estiver fora do ar, entram as regras automáticas.
> **Nunca** mande a sua chave no chat nem para ninguém.

## Passo 4: Verificar
Dê dois cliques em **`verificar_windows.bat`**.
- **"🎉 Tudo certo!"** → siga para o Passo 5.
- Algum **❌** → tire um print e mande no chat.

## Passo 5: Abrir e configurar uma vez
1. Dê dois cliques em **`start_windows.bat`**.
2. Se o **Firewall do Windows** perguntar, marque **Redes privadas** → **Permitir acesso**.
3. O DarkClip abre numa **janela própria**. **Deixe a janela preta aberta** enquanto usar.
4. Na aba **📅 Canal**:
   - cole o link do seu canal do YouTube e toque em **Salvar**;
   - em **🎯 Perfil do canal**, escreva o que é um bom corte para você e toque em **Salvar perfil**. Exemplo:
     > Gameplay com humor. Quero reações fortes, sustos e falhas engraçadas. Evite partes de menu, carregamento e fala sobre configurações.

5. Ainda na aba **📅 Canal**, em **🎨 Modelos por rede**: escreva o @ do seu canal, escolha um modelo para cada rede e toque em **Salvar modelos**.

## Passo 6: Primeiro teste
1. Aba **✂️ Clipar** → cole um link → escolha **Longos (45–90s)** e **3 cortes** → **Gerar cortes**.
2. Acompanhe na aba **🎬 Resultados**. Toque em **📜 Ver detalhes** para ver cada passo.
3. Quando os cortes ficarem prontos, dê **👍 ou 👎** em cada um e toque no motivo. É assim que o DarkClip aprende o seu gosto.

## Passo 7 (opcional): Usar pelo celular
1. Celular e PC no **mesmo Wi-Fi**.
2. Na janela preta aparece um endereço assim:
   ```
   http://192.168.0.15:8787/?token=a1b2c3
   ```
3. Digite **exatamente esse endereço** no Chrome do celular. A senha fica salva sozinha.
4. No Chrome: **⋮ → Adicionar à tela inicial**. Vira um app.

## Passo 8 (opcional): Ligar o DarkClip ao Claude
Assim você pede ao Claude Code "corta este vídeo em 3 Shorts longos" e ele faz tudo pelo DarkClip.
1. Precisa ter o **Claude Code** instalado no PC.
2. Dê dois cliques em **`registrar_claude_windows.bat`** (só uma vez).
3. Deixe o DarkClip aberto (`start_windows.bat`) e, no Claude Code, peça o que quiser:
   - "corta este vídeo em 3 Shorts longos: LINK"
   - "mostra os cortes do último trabalho e agenda o melhor para amanhã às 18h"
   - "dá 👎 no corte 2 com o motivo Começa sem contexto"

---

## Atualizar para uma versão nova
1. **Feche** a janela preta do DarkClip.
2. Extraia o zip novo em **`C:\deploy`** e, quando o Windows perguntar, escolha **Substituir os arquivos no destino**.
3. Abra o `start_windows.bat` de novo.

> O `.env` (suas chaves), o `.venv` (programas instalados) e a pasta `data` (vídeos, notas, calendário) **não são apagados**.
> Se a versão nova pedir biblioteca nova, o `verificar_windows.bat` avisa: aí é só rodar o `install_windows.bat` de novo.

## Dia a dia
| Quero… | Faço… |
|---|---|
| Abrir o DarkClip | Dois cliques em `start_windows.bat` |
| Ver se está tudo ok | Dois cliques em `verificar_windows.bat` |
| Onde ficam os vídeos | `C:\deploy\darkclip\data\jobs\` |
| Ajuda quando algo dá errado | Aba **⚙️ Ajustes → ❓ Problemas comuns**, ou o 💡 que aparece embaixo do erro |

## Problemas comuns
| O que aparece | O que fazer |
|---|---|
| "Sign in to confirm you're not a bot" (YouTube) | Rode o `install_windows.bat` de novo (atualiza o yt-dlp). Se continuar, veja "cookies" no README |
| "Gemini ocupado (503)" | O Google estava lotado. O DarkClip tenta de novo e troca de modelo sozinho; os cortes saem mesmo assim |
| Parado em "Transcrevendo" por muito tempo | Na 1ª vez ele baixa o Whisper (~480 MB). Para ir mais rápido: `DARKCLIP_WHISPER_MODEL=base` no `.env` |
| A janela não abre o app | Abra o navegador em `http://127.0.0.1:8787` |
| Celular não conecta | Mesmo Wi-Fi? Firewall liberou "Redes privadas"? Use o endereço com `?token=` |
| "ffmpeg não é reconhecido" | Reinicie o PC (o PATH só atualiza depois de reiniciar) |
| Qualquer outro erro | Print do `verificar_windows.bat` + "📜 Ver detalhes" do trabalho, e mande no chat |
