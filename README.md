# ootto-watch 👀 — let Claude actually *watch* a video

A Claude skill that gives Claude **eyes + ears** on any online video. Most tools only read the transcript and miss everything visual — this hands Claude the **frames and the words, aligned on one timeline**, so it can reason about cuts, on-screen text, demos, hooks, and pacing.

Paste a link → it downloads the video, samples key frames, transcribes the audio, and Claude reads both.

## Install

**Claude Code** (drop the skill in):
```bash
git clone https://github.com/Ootto-AI/ootto-watch ~/.claude/skills/watch-video
```

**claude.ai (web):** zip this folder and add it under Settings → Capabilities → Skills.

Then just tell Claude: *"watch this video: <url>"*.

## How it works

1. **Download** — `yt-dlp` pulls the video (+ native captions if present) from YouTube, Instagram, X, Vimeo, and 1000+ sites.
2. **Frames** — `ffmpeg` samples key frames, duration-aware (a 30s clip gets ~30 frames; a 30-min lecture stays sparse) and scales them down for fast vision.
3. **Transcript** — native captions when available (free); otherwise local `faster-whisper` (also free, CPU). `--no-whisper` to skip.
4. **Watch** — Claude reads the frames as images alongside the timestamped transcript (`index.json`) and answers grounded in *both*.

## Requirements
- `yt-dlp` and `ffmpeg`/`ffprobe` on PATH
- (optional) `pip install faster-whisper` — only needed for videos without captions

## Run it directly
```bash
python scripts/watch.py "https://youtu.be/…" --out watch_out --max-frames 60
# writes watch_out/frames/*.jpg, transcript.txt, index.json
```

## License
MIT © Ootto-AI. Built by [@jayantcreates.ai](https://instagram.com/jayantcreates.ai). This is an original implementation; the "give Claude video input" idea is a community pattern with several great open-source takes (e.g. `bradautomates/claude-video`, `devinilabs/claude-watch`) — go star those too.
