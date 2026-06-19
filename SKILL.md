---
name: watch-video
description: Give Claude eyes and ears on any online video, then analyze it. Downloads a video from a URL (YouTube, Instagram, X, Vimeo, and 1000+ yt-dlp sites), extracts key frames, and gets a transcript (native captions, else local Whisper), then hands the frames + timestamped transcript to Claude so it can produce a full breakdown — hook, format, storytelling structure, pacing and visual layout — grounded in what's actually on screen AND said. Pass several URLs to batch-analyze dozens at once and surface the patterns the best ones share. Use whenever the user shares a video link (or many) and wants it watched, analyzed, broken down, summarized, or turned into a script/notes.
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

## Analyze — the full breakdown

Once `watch.py` has run, read the frames + `transcript.txt` aligned by `index.json`, then write a structured breakdown. Ground every point in a specific frame `t` and/or transcript line:

- **Hook (first ~3s)** — exactly what's on screen and said in the opening, and *why* it stops the scroll.
- **Format** — the style (talking-head, faceless motion-graphics, screen-record, split-screen…) and how captions / on-screen text are used.
- **Storytelling structure** — beat by beat: each scene or idea, its timestamp, and what changes on screen at that moment.
- **Pacing** — average beat length, cut rhythm, where it slows or accelerates.
- **Visual layout** — framing, where text sits, the graphics technique, b-roll vs. demo.
- **Transcript** — the full spoken words (from `transcript.txt`).

That's the same breakdown you'd want before modeling a video: hook → format → structure → pacing → layout, all evidence-backed.

## Batch — analyze many at once, find the patterns

Pass several URLs to watch them all in one run:
```
python scripts/watch.py "<url1>" "<url2>" "<url3>" --out batch_out
```
It writes each video to `batch_out/v01, v02, …` (frames + transcript + index per video) plus a `batch_out/batch.json` manifest. **Analyze each** (above), then **compare across all of them** to surface what the strong ones share — repeated **hook shapes**, common **beat lengths / structure**, recurring **visual moves**: the trends, insights and patterns you'd never spot watching one at a time.

## Notes
- Captions are used when the platform has them (free). Otherwise it falls back to local `faster-whisper` (also free, runs on CPU). Pass `--no-whisper` to skip transcription entirely.
- For long videos, frames are sampled sparsely (duration-aware) so the frame count stays manageable for vision.
