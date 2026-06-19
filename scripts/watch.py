#!/usr/bin/env python3
"""ootto-watch — give Claude eyes + ears on any online video, then break it down.

Downloads a video (yt-dlp), samples key frames (ffmpeg, duration-aware), and gets a transcript
(native captions when available, else local faster-whisper). Writes frames + a timestamped
transcript + an index so Claude can read the visuals and the words aligned on one timeline —
then analyze the hook, format, structure, pacing and visual layout (see SKILL.md → Analyze).

Usage:
    python scripts/watch.py "<video-url>" [--out watch_out] [--max-frames 80] [--every SECONDS] [--no-whisper]
    python scripts/watch.py "<url1>" "<url2>" "<url3>" --out batch_out   # batch: many at once → patterns

Requirements: yt-dlp, ffmpeg/ffprobe on PATH. Optional: faster-whisper (pip) for caption-less videos.
Original implementation — MIT licensed (see LICENSE).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def _need(binary):
    if not shutil.which(binary):
        sys.exit(f"Missing dependency: '{binary}'. Install it and retry.")


def download(url: str, out: Path) -> Path:
    """Pull the video (+ English auto-captions if present) with yt-dlp."""
    _need("yt-dlp")
    _run(["yt-dlp", "-f", "mp4/best", "--write-subs", "--write-auto-subs",
          "--sub-langs", "en.*", "--convert-subs", "srt",
          "-o", str(out / "video.%(ext)s"), url])
    vid = next((p for p in out.glob("video.*") if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")), None)
    if not vid:
        sys.exit("Download failed: no video file produced.")
    return vid


def duration_s(vid: Path) -> float:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(vid)]).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def frame_rate(dur: float, every: float, max_frames: int) -> float:
    """Frames-per-second to sample. Duration-aware so long videos stay sparse."""
    if every and every > 0:
        return 1.0 / every
    if dur <= 0:
        return 0.5
    target = 30 if dur <= 30 else 40 if dur <= 60 else 60 if dur <= 180 else 80 if dur <= 600 else 100
    target = min(target, max_frames)
    return max(0.1, target / dur)


def extract_frames(vid: Path, out: Path, fps: float):
    fdir = out / "frames"
    if fdir.exists():
        shutil.rmtree(fdir)
    fdir.mkdir(parents=True)
    _need("ffmpeg")
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(vid),
          "-vf", f"fps={fps},scale=512:-2", "-q:v", "3", str(fdir / "f%03d.jpg")])
    frames = sorted(fdir.glob("f*.jpg"))
    index = [{"frame": i, "t": round(i / fps, 2), "file": f"frames/{p.name}"} for i, p in enumerate(frames)]
    (out / "index.json").write_text(json.dumps(index, indent=2))
    return len(frames)


def _srt_to_text(srt: Path) -> str:
    lines = []
    for ln in srt.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = ln.strip()
        if not s or s.isdigit() or "-->" in s:
            continue
        lines.append(re.sub(r"<[^>]+>", "", s))
    # dedupe consecutive repeats common in auto-captions
    out, prev = [], None
    for s in lines:
        if s != prev:
            out.append(s)
        prev = s
    return " ".join(out)


def transcribe(vid: Path, out: Path, no_whisper: bool) -> str:
    srt = next(out.glob("video*.srt"), None)
    if srt:
        return _srt_to_text(srt)
    if no_whisper:
        return ""
    try:
        from faster_whisper import WhisperModel
    except Exception:
        print("  (no captions + faster-whisper not installed → skipping transcript; pip install faster-whisper)")
        return ""
    print("  transcribing with faster-whisper (local)…")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(str(vid), language="en")
    return " ".join(s.text.strip() for s in segs).strip()


def watch_one(url: str, out: Path, max_frames: int, every: float, no_whisper: bool) -> dict:
    """Download + frame-sample + transcribe ONE video into `out`. Returns a manifest row."""
    out.mkdir(parents=True, exist_ok=True)
    print(f"→ downloading {url}")
    vid = download(url, out)
    dur = duration_s(vid)
    fps = frame_rate(dur, every, max_frames)
    print(f"→ {dur:.0f}s video · sampling ~{fps:.2f} fps")
    n = extract_frames(vid, out, fps)
    text = transcribe(vid, out, no_whisper)
    (out / "transcript.txt").write_text(text, encoding="utf-8")
    print(f"✓ {n} frames · transcript {len(text.split())} words → {out}")
    return {"url": url, "dir": str(out), "frames": n, "duration_s": round(dur, 1), "words": len(text.split())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+", help="one or more video URLs (pass several for a batch)")
    ap.add_argument("--out", default="watch_out")
    ap.add_argument("--max-frames", type=int, default=80)
    ap.add_argument("--every", type=float, default=0.0, help="seconds between frames (0 = auto by duration)")
    ap.add_argument("--no-whisper", action="store_true")
    a = ap.parse_args()
    base = Path(a.out).resolve()

    if len(a.urls) == 1:
        watch_one(a.urls[0], base, a.max_frames, a.every, a.no_whisper)
        print(f"\n✓ index → {base / 'index.json'}")
        print("\nNow: read the frames (as images) + transcript.txt, aligned by index.json timestamps,")
        print("then write the full breakdown — hook · format · structure · pacing · visual layout (see SKILL.md → Analyze).")
        return

    # batch: many videos at once → one manifest so Claude can compare them for patterns
    base.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, u in enumerate(a.urls, 1):
        sub = base / f"v{i:02d}"
        print(f"\n=== [{i}/{len(a.urls)}] ===")
        try:
            manifest.append(watch_one(u, sub, a.max_frames, a.every, a.no_whisper))
        except SystemExit as e:
            print(f"  ! skipped {u}: {e}")
    (base / "batch.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n✓ batch of {len(manifest)} videos → {base} (manifest: batch.json)")
    print("Now: analyze each (SKILL.md → Analyze), then compare ALL of them to surface the shared")
    print("hook shapes, beat lengths/structure and recurring visual moves — the patterns (SKILL.md → Batch).")


if __name__ == "__main__":
    main()
