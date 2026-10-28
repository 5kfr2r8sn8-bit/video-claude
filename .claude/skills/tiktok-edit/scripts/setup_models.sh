#!/usr/bin/env bash
# Muat turun model Whisper (sherpa-onnx, int8) dan Silero VAD dari GitHub Releases.
set -euo pipefail
MODEL=${1:-small}
DIR=${TIKTOK_MODELS:-$HOME/.cache/tiktok-edit/models}
BASE=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
mkdir -p "$DIR" && cd "$DIR"

if [ ! -f "sherpa-onnx-whisper-$MODEL/$MODEL-encoder.int8.onnx" ]; then
  echo "Muat turun whisper-$MODEL ..."
  curl -fsSL -o "whisper-$MODEL.tar.bz2" "$BASE/sherpa-onnx-whisper-$MODEL.tar.bz2"
  tar xjf "whisper-$MODEL.tar.bz2" && rm "whisper-$MODEL.tar.bz2"
  rm -f "sherpa-onnx-whisper-$MODEL/$MODEL-encoder.onnx" "sherpa-onnx-whisper-$MODEL/$MODEL-decoder.onnx"
fi
[ -f silero_vad.onnx ] || curl -fsSL -o silero_vad.onnx "$BASE/silero_vad.onnx"
echo "Model sedia di $DIR"
