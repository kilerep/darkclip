@echo off
chcp 65001 >nul
REM DarkClip - instalação no Windows 10/11. Dê dois cliques neste arquivo.
cd /d "%~dp0"
echo.
echo ===== DarkClip - instalacao =====
echo.

REM O Windows tem um "python" falso (atalho da Microsoft Store): por isso testamos a versao de verdade.
python --version >nul 2>&1 || (
  where winget >nul 2>&1 || (
    echo [!] Instale o Python 3.12 pelo site python.org/downloads
    echo     IMPORTANTE: marque a caixinha "Add python.exe to PATH" na primeira tela.
    echo     Depois rode este arquivo de novo.
    pause & exit /b 1
  )
  echo [1/5] Instalando Python 3.12...
  winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
  echo.
  echo Python instalado. FECHE esta janela e de dois cliques em install_windows.bat de novo.
  pause & exit /b 0
)
for /f "tokens=2" %%v in ('python --version') do echo [ok] Python %%v

ffmpeg -version >nul 2>&1 || (
  echo [2/5] Instalando ffmpeg - edicao de video...
  winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements || echo [!] Instale o ffmpeg manualmente: veja docs\INSTALAR_PC.md
  set REINICIAR=1
)
node --version >nul 2>&1 || (
  echo [3/5] Instalando Node.js - necessario para baixar do YouTube...
  winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements || echo [!] Instale o Node.js LTS pelo site nodejs.org
  set REINICIAR=1
)

echo [4/5] Criando ambiente Python e instalando bibliotecas (pode levar 5-10 minutos)...
if not exist .venv (python -m venv .venv || (echo [!] Falha ao criar o ambiente Python & pause & exit /b 1))
call .venv\Scripts\activate.bat
python -m pip install -U pip -q
pip install -r requirements.txt || (echo [!] Falha ao instalar bibliotecas. Tire um print desta tela. & pause & exit /b 1)

echo [5/5] Detector de rostos YuNet (opcional)...
if exist darkclip\models\face_detection_yunet_2023mar.onnx goto yunet_ok
curl -sfL -o darkclip\models\face_detection_yunet_2023mar.onnx https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx || curl -sfL -o darkclip\models\face_detection_yunet_2023mar.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx || echo (sem YuNet: usando o detector padrao)
:yunet_ok

python -m darkclip.setup_env
echo.
echo ===== PRONTO! =====
if defined REINICIAR echo  * O ffmpeg/Node acabaram de ser instalados: REINICIE o PC uma vez antes de usar.
echo  1. Abra o arquivo .env com o Bloco de Notas e cole a chave do Gemini em GEMINI_API_KEY=
echo  2. De dois cliques em verificar_windows.bat para conferir se esta tudo certo
echo  3. Para usar: dois cliques em start_windows.bat
echo.
pause
