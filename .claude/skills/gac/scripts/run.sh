#!/bin/bash
# Run a GAC script with its tools. Works in the claude.ai sandbox (Linux, ffmpeg already there)
# and in Claude Code on a Mac (builds a private venv with its own ffmpeg the first time).
# Usage: bash run.sh build.py timeline.json OUT.mp4 [--preview 8]
DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$1"; shift
PKGS='numpy pillow opencv-python-headless<5'
[ "$SCRIPT" = transcribe.py ] && PKGS="$PKGS faster-whisper av<16"   # av 16+ breaks faster-whisper 1.2
CHECK='import numpy, PIL, cv2'; [ "$SCRIPT" = transcribe.py ] && CHECK="$CHECK, faster_whisper"
if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null && [ "$(uname)" != Darwin ]; then
  # sandbox: system Python, install what is missing (quietly, once per chat)
  python3 -c "$CHECK" 2>/dev/null || { echo "Memasang alat video (sekali sahaja)..." >&2
    pip install -q $PKGS 2>/dev/null || pip install -q --break-system-packages $PKGS >&2 || { echo "pip install gagal" >&2; exit 1; }; }
  PY=python3
else
  VENV="${GAC_VENV:-$HOME/.local/share/gac/venv}"
  [ -x "$HOME/.local/share/edit-video-pro/venv/bin/python" ] && [ -z "$GAC_VENV" ] && [ ! -x "$VENV/bin/python" ] && VENV="$HOME/.local/share/edit-video-pro/venv"
  if [ ! -x "$VENV/bin/python" ]; then
    echo "Memasang alat video (sekali sahaja, 1-3 minit)..." >&2
    python3 -m venv "$VENV" && "$VENV/bin/pip" install -q --upgrade pip >&2 || { echo "venv gagal" >&2; exit 1; }
  fi
  "$VENV/bin/python" -c "$CHECK, static_ffmpeg" 2>/dev/null || "$VENV/bin/pip" install -q $PKGS static-ffmpeg >&2 || { echo "pip install gagal" >&2; exit 1; }
  "$VENV/bin/static_ffmpeg_paths" >/dev/null 2>&1
  FF="$("$VENV/bin/python" -W ignore -c 'import static_ffmpeg,os;print(os.path.dirname(static_ffmpeg.__file__))' 2>/dev/null)/bin"
  FFD="$(dirname "$(find "$FF" -name ffmpeg -type f | head -1)")"
  export PATH="$FFD:$VENV/bin:$PATH"; PY="$VENV/bin/python"
fi
exec "$PY" -W ignore "$DIR/$SCRIPT" "$@"
