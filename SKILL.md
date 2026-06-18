---
name: watch-video
description: Give Claude eyes and ears on any online video. Downloads a video from a URL (YouTube, Instagram, X, Vimeo, and 1000+ yt-dlp sites), extracts key frames, and gets a transcript (native captions, else local Whisper), then hands the frames + timestamped transcript to Claude so it can answer grounded in what's actually on screen AND said. Use whenever the user shares a video link and wants it watched, summarized, broken down, or turned into a script/notes.
---

# watch-video — let Claude actually watch a video

Most tools only read a transcript and miss everything visual. This skill gives Claude the **frames + the words, aligned on one timeline**, so it can reason about cuts, on-screen text, demos, and pacing — not just the audio.

## How to use it

When the user gives a video URL:

1. Run the helper (it downloads, samples frames, and transcribes):
   ```
   python scripts/watch.py "<VIDEO_URL>" --out watch_out
   ```
   Useful flags: `--max-frames 60` (cap frames), `--no-whisper` (captions only, fully free/offline), `--every 0` (auto-pace by duration).

2. It writes:
   - `watch_out/frames/f000.jpg …` — sampled frames (named by index)
   - `watch_out/transcript.txt` — the spoken words
   - `watch_out/index.json` — `[{frame, t, file}]` so each frame maps to its timestamp

3. **Read the frames as images** (use the Read tool on the PNG/JPGs) alongside `transcript.txt`, lining each frame up with what's being said at its `t`. Then answer the user's request (summary, breakdown, hook analysis, study notes, a fresh script, etc.) grounded in BOTH the visuals and the audio.

## Notes
- Captions are used when the platform has them (free). Otherwise it falls back to local `faster-whisper` (also free, runs on CPU). Pass `--no-whisper` to skip transcription entirely.
- For long videos, frames are sampled sparsely (duration-aware) so the frame count stays manageable for vision.
