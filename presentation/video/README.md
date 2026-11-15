# Introduction video (≈ 90 s)

`hashatlas_intro.mp4`: 1920×1080, 30 fps, English narration with English subtitles drawn in the frame.
`hashatlas_intro.srt` is the same subtitle text as a sidecar file, for players that support it. It is played on slide 2 of
`presentation/HashAtlas.pptx`, before the talk.

| Part | Time | What the audience sees |
|---|---|---|
| Genesis | 0:00–0:14 | 3 Jan 2009: one laptop, block #0, a 50 BTC reward; the chain starts to grow |
| Hash power | 0:14–0:30 | 17 years of real weekly hash rate (log scale) with the CPU → GPU → FPGA → ASIC eras |
| The lottery | 0:30–0:46 | 16,362 squares, one orange: the yearly odds for a 1.2 TH/s home miner; 22 solo blocks in 2025 |
| Fingerprint | 0:46–0:59 | the 32-bit version field with the rolled bits 13–28; block fullness; the coinbase tag struck out (label, never input) |
| Questions | 0:59–1:22 | 975,494 blocks, then Q1 classify · Q2 cluster + rules · Q3 decide |
| Title | 1:22–1:30 | HashAtlas logo, question, team, URL |

**Voice.** Microsoft Edge neural TTS, `en-US-SteffanNeural`, a calm "news" register that is less overused online
than the common defaults (Guy, Christopher, Andrew, Brian). To change it, edit `voice` in `narration.json`
(`en-GB-ThomasNeural` is a good British alternative) and rebuild.

**Style.** Same "Ledger" brand as the dashboard, slides and link banner: charcoal ink, paper white, Bitcoin orange;
Caladea/Cambria headings, Inter body, JetBrains Mono figures. Every on-screen number comes from the pipeline outputs.

**Rebuild.** `./make_video.sh` (needs `uv` and `ffmpeg`; ~20 min on a laptop CPU). `QUALITY=l ./make_video.sh` makes a quick draft.
The narration is synthesised by Microsoft's online TTS service; only the script text in `narration.json` is sent.
