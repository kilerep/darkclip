#!/usr/bin/env bash
# Instalação no PC/servidor (Linux/macOS). Requer python3 >= 3.10 e ffmpeg.
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "Instale o ffmpeg (apt install ffmpeg / brew install ffmpeg)"; exit 1; }
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip -q
pip install -r requirements.txt
python3 -m darkclip.setup_env
# Detector de rostos YuNet (mais preciso que o Haar padrão) — opcional
[ -s darkclip/models/face_detection_yunet_2023mar.onnx ] || (curl -sfL -o darkclip/models/face_detection_yunet_2023mar.onnx https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx \
  || curl -sfL -o darkclip/models/face_detection_yunet_2023mar.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx) \
  && echo "YuNet instalado" || echo "(opcional) YuNet não baixado: usando detector Haar"
echo
echo "Pronto. Coloque GEMINI_API_KEY e ANTHROPIC_API_KEY no arquivo .env e inicie com: ./start.sh"
