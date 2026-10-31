#!/usr/bin/env bash
# Studio video (TikTok / Reels / Shorts 9:16, 1080x1920): pasang semula alat pada sesi awan baharu.
# Tampal kandungan fail ini ke "Setup script" dalam tetapan environment (menu environment > Edit),
# atau jalankan sendiri: bash setup_studio.sh
# Node 22+, npm, Python 3, uv, Git, FFmpeg/FFprobe dan Claude Code sudah ada dalam imej asas.
set -e

# 1. Video-Use (https://github.com/browser-use/video-use, ikut install.md)
mkdir -p ~/Developer ~/.claude/skills
test -d ~/Developer/video-use || git clone https://github.com/browser-use/video-use ~/Developer/video-use
(cd ~/Developer/video-use && git pull --ff-only || true; uv sync)
ln -sfn ~/Developer/video-use ~/.claude/skills/video-use
# Kunci ElevenLabs TIDAK disimpan di sini: letak ELEVENLABS_API_KEY sebagai rahsia environment.

# 2. yt-dlp (muat turun video rujukan)
uv tool install yt-dlp || uv tool upgrade yt-dlp

# 3. HyperFrames: plugin Claude Code rasmi + CLI dan Chrome untuk render
claude plugin marketplace add heygen-com/hyperframes || true
claude plugin install hyperframes@hyperframes || true
npx --yes hyperframes@latest browser ensure || true

echo "Studio video sedia."
