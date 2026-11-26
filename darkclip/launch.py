"""Abre o DarkClip numa janela própria (modo aplicativo do Edge/Chrome) assim que o servidor estiver no ar.

  python -m darkclip.launch          # usado por start_windows.bat / start.sh
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser

from .setup_env import ensure_env

PORT = int(os.environ.get("PORT", "8787"))


def wait_server(timeout: float = 60) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=1):
                return True
        except OSError:
            time.sleep(0.7)
    return False


def open_app(url: str) -> None:
    flags = [f"--app={url}", "--window-size=480,900"]
    if sys.platform.startswith("win"):
        for exe in ("msedge", "chrome"):
            try:  # "start" acha o Edge/Chrome mesmo fora do PATH
                subprocess.Popen(["cmd", "/c", "start", "", exe, *flags], creationflags=0x08000000)
                return
            except OSError:
                continue
    elif sys.platform == "darwin":
        for app in ("Google Chrome", "Microsoft Edge"):
            if os.path.exists(f"/Applications/{app}.app"):
                subprocess.Popen(["open", "-na", app, "--args", *flags])
                return
    else:
        for exe in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            if shutil.which(exe):
                subprocess.Popen([exe, *flags], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
    webbrowser.open(url)


def main() -> None:
    token = ensure_env()
    if wait_server():
        open_app(f"http://127.0.0.1:{PORT}/?token={token}")


if __name__ == "__main__":
    main()
