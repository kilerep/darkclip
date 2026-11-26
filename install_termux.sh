#!/data/data/com.termux/files/usr/bin/bash
# DarkClip — instalação 100% no celular Android (Termux do F-Droid ou GitHub, NÃO o da Play Store).
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"

# Comando "darkclip" como programa de verdade em $PREFIX/bin (funciona na hora, sem reiniciar o Termux)
printf '#!/data/data/com.termux/files/usr/bin/bash\nexec bash "%s/iniciar_celular.sh" "$@"\n' "$DIR" > "$PREFIX/bin/darkclip"
chmod +x "$PREFIX/bin/darkclip"
trap 'echo; echo "❌ A instalação parou com erro (veja as linhas acima). Copie a mensagem e rode de novo: bash $DIR/install_termux.sh"' ERR

echo "==> 1/5 Atualizando o Termux"
pkg update -y && pkg upgrade -y -o Dpkg::Options::="--force-confnew"

echo "==> 2/5 Instalando programas (Python, ffmpeg, Node, numpy, compiladores)"
pkg install -y python ffmpeg nodejs python-numpy rust binutils clang make termux-tools
pkg install -y opencv-python 2>/dev/null \
  || echo "   (opcional) OpenCV indisponível: o modo 'Seguir rosto' usará corte central"

echo "==> 3/5 Instalando bibliotecas Python (na 1ª vez leva 10-25 min: compila partes em Rust)"
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"   # exigido pelo maturin/Rust no Android
pip install "yt-dlp[default]" fastapi uvicorn python-multipart anthropic edge-tts httpx

echo "==> 4/5 Configurando"
[ -f .env ] || cp .env.example .env
sed -i 's/^DARKCLIP_PRESET=.*/DARKCLIP_PRESET=ultrafast    # celular: mais rápido/' .env
chmod +x start.sh iniciar_celular.sh

echo "==> 5/5 Criando atalhos"
mkdir -p ~/.shortcuts
cat > ~/.shortcuts/DarkClip <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec bash "$DIR/iniciar_celular.sh"
EOF
chmod +x ~/.shortcuts/DarkClip

echo "==> Verificando"
python -c "import fastapi, uvicorn, anthropic, edge_tts, yt_dlp, numpy; print('   bibliotecas OK')"
ffmpeg -hide_banner -filters 2>/dev/null | grep -q " ass " && echo "   ffmpeg com legendas OK" || echo "   ⚠️ ffmpeg sem filtro de legendas (ass)"
echo
echo "✅ Pronto! Para abrir: digite  darkclip  (ou use o widget do Termux:Widget)."
echo "   O app abre sozinho no navegador em http://127.0.0.1:8787"
