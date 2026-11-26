@echo off
chcp 65001 >nul
REM DarkClip - liga o DarkClip ao Claude Code (servidor MCP). Rode uma vez so.
cd /d "%~dp0"
where claude >nul 2>nul
if errorlevel 1 goto semclaude
if not exist ".venv\Scripts\python.exe" goto seminstalar
claude mcp add darkclip -s user -e PYTHONPATH="%~dp0." -- "%~dp0.venv\Scripts\python.exe" -m darkclip.mcp_server
echo.
echo Pronto! Abra o DarkClip - start_windows.bat - e, no Claude Code, peca:
echo     "corta este video em 3 Shorts longos: LINK"
echo Para conferir: claude mcp list
goto fim
:semclaude
echo O Claude Code nao foi encontrado neste PC.
echo Instale pelo site claude.com/claude-code e rode este arquivo de novo.
goto fim
:seminstalar
echo Rode primeiro o install_windows.bat.
:fim
echo.
pause
