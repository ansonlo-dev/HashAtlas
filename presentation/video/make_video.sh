#!/bin/sh
# Build hashatlas_intro.mp4, hashatlas_intro.srt and the slide poster.
# tts.py supplies narration and timing; scene.py renders the animation and captions.
# ffmpeg adds the voice and ambient audio, then exports H.264/AAC at 1080p30.
# Usage: ./make_video.sh (QUALITY=l for a 480p15 draft)
set -e
cd "$(dirname "$0")"
Q="${QUALITY:-h}"
PY="uv run --no-project --python 3.12"
$PY --with edge-tts python tts.py
if [ "$Q" = "l" ]; then FPS=15; else FPS=30; fi
timeout 3600 $PY --with manim==0.19.0 --with "pillow<11" manim -q"$Q" --fps "$FPS" scene.py Intro --media_dir build/media --disable_caching
SRC=$(ls -t build/media/videos/scene/*/Intro.mp4 | head -1)
T=$(python3 -c "import json;print(json.load(open('build/timeline.json'))['total_s'])")
# Ambient bed: filtered brown noise + a soft 55 Hz tone, ~30 dB under the voice, faded in and out.
ffmpeg -y -v error -i "$SRC" -i build/narration.wav \
  -f lavfi -t "$T" -i "anoisesrc=color=brown:amplitude=0.5:seed=7,lowpass=f=320,highpass=f=40" \
  -f lavfi -t "$T" -i "sine=frequency=55:sample_rate=48000" \
  -filter_complex "[2]volume=0.035[n];[3]volume=0.012[s];[n][s]amix=inputs=2:normalize=0,afade=t=in:d=2,afade=t=out:st=$(python3 -c "print($T-3)"):d=3,aformat=channel_layouts=stereo[bed];[1][bed]amix=inputs=2:normalize=0:duration=first[a]" \
  -map 0:v -map "[a]" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
  -metadata title="HashAtlas: Can a small Bitcoin miner still win?" -metadata comment="CDS3004 Data Mining - Team HashAtlas" \
  -t "$T" hashatlas_intro.mp4
ffmpeg -y -v error -ss "$(python3 -c "print($T-3.5)")" -i hashatlas_intro.mp4 -frames:v 1 poster.png
echo "wrote hashatlas_intro.mp4 ($(ffprobe -v error -show_entries format=duration -of csv=p=0 hashatlas_intro.mp4)s), hashatlas_intro.srt, poster.png"
