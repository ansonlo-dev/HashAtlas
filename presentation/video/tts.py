"""Build the Edge TTS voice track, scene timeline and English subtitles.

Pad the narration to target_s. Write build/timeline.json for scene.py,
build/narration.wav and hashatlas_intro.srt.
Run from presentation/video:
  uv run --no-project --python 3.12 --with edge-tts python tts.py
"""
import asyncio, json, subprocess
from pathlib import Path

import edge_tts

HERE = Path(__file__).parent
B = HERE / "build"
B.mkdir(exist_ok=True)
cfg = json.loads((HERE / "narration.json").read_text())
GAP, LEAD, TAIL = 0.45, 0.7, 2.6  # Seconds between lines, before scenes and after the last line.


def dur(p: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p),
    ]))


async def synth():
    clips = []
    for si, sc in enumerate(cfg["scenes"]):
        for li, text in enumerate(sc["lines"]):
            mp3 = B / f"line_{si}_{li}.mp3"
            if not mp3.exists() or mp3.stat().st_size == 0:
                await edge_tts.Communicate(text, cfg["voice"], rate=cfg["rate"]).save(str(mp3))
            wav = mp3.with_suffix(".wav")
            subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", "48000", "-ac", "2", str(wav),
            ], check=True)
            clips.append({
                "scene": sc["id"], "si": si, "li": li, "text": text,
                "wav": wav.name, "dur": round(dur(wav), 3),
            })
    return clips


clips = asyncio.run(synth())
speech = sum(c["dur"] for c in clips)
n_scenes = len(cfg["scenes"])
base = speech + GAP * (len(clips) - n_scenes) + LEAD * n_scenes + TAIL
slack = cfg["target_s"] - base
if slack < 0:
    raise SystemExit(f"narration too long by {-slack:.1f}s: shorten lines or raise the rate")
lead = LEAD + slack / n_scenes  # Split spare time evenly between scene openings.

t, scenes = 0.0, []
for si, sc in enumerate(cfg["scenes"]):
    start = t
    t += lead
    lines = []
    for c in [c for c in clips if c["si"] == si]:
        c["start"] = round(t, 3)
        c["end"] = round(t + c["dur"], 3)
        lines.append(c)
        t = c["end"] + GAP
    t -= GAP
    if si == n_scenes - 1:
        t += TAIL
    scenes.append({"id": sc["id"], "start": round(start, 3), "end": round(t, 3), "lines": lines})
total = round(t, 3)

# Delay clips to their start times, mix them and pad to the target duration.
inputs, filters = [], []
for i, c in enumerate(clips):
    inputs += ["-i", str(B / c["wav"])]
    ms = int(c["start"] * 1000)
    filters.append(f"[{i}]adelay={ms}|{ms}[a{i}]")
mix = "".join(f"[a{i}]" for i in range(len(clips)))
filters.append(f"{mix}amix=inputs={len(clips)}:normalize=0,apad,atrim=0:{total},loudnorm=I=-16:TP=-1.5:LRA=11[out]")
subprocess.run([
    "ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
    "-map", "[out]", "-ar", "48000", str(B / "narration.wav"),
], check=True)


def stamp(x):
    h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


caps = cfg.get("captions", {})
srt = []
for i, c in enumerate(clips, 1):
    c["caption"] = caps.get(c["text"], c["text"])
    srt.append(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'] + 0.25)}\n{c['caption']}\n")
(HERE / "hashatlas_intro.srt").write_text("\n".join(srt))
(B / "timeline.json").write_text(json.dumps({"total_s": total, "voice": cfg["voice"], "scenes": scenes}, indent=1))
(B / "timing.json").write_text(json.dumps({"total_s": round(total)}))
print(f"speech {speech:.1f}s, total {total:.1f}s, lead per scene {lead:.2f}s")
for s in scenes:
    print(f"  {s['id']:12s} {s['start']:6.2f} → {s['end']:6.2f}")
