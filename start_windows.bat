@echo off
chcp 65001 >nul
REM DarkClip - inicia o servidor no PC. Deixe esta janela aberta enquanto usa o app no celular.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m darkclip.setup_env --url
start "" /b .venv\Scripts\pythonw.exe -m darkclip.launch
echo Se o Windows perguntar sobre o Firewall, clique em "Permitir acesso" (rede privada).
python -m uvicorn server:app --host 0.0.0.0 --port 8787
pause
