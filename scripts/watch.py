#!/usr/bin/env python3
"""ootto-watch — give Claude eyes + ears on any online video.

Downloads a video (yt-dlp), samples key frames (ffmpeg, duration-aware), and gets a transcript
(native captions when available, else local faster-whisper). Writes frames + a timestamped
transcript + an index so Claude can read the visuals and the words aligned on one timeline.

Usage:
    python scripts/watch.py "<video-url>" [--out watch_out] [--max-frames 60] [--every SECONDS] [--no-whisper]

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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--out", default="watch_out")
    ap.add_argument("--max-frames", type=int, default=80)
    ap.add_argument("--every", type=float, default=0.0, help="seconds between frames (0 = auto by duration)")
    ap.add_argument("--no-whisper", action="store_true")
    a = ap.parse_args()

    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    print(f"→ downloading {a.url}")
    vid = download(a.url, out)
    dur = duration_s(vid)
    fps = frame_rate(dur, a.every, a.max_frames)
    print(f"→ {dur:.0f}s video · sampling ~{fps:.2f} fps")
    n = extract_frames(vid, out, fps)
    text = transcribe(vid, out, a.no_whisper)
    (out / "transcript.txt").write_text(text, encoding="utf-8")
    print(f"\n✓ {n} frames → {out/'frames'}")
    print(f"✓ transcript ({len(text.split())} words) → {out/'transcript.txt'}")
    print(f"✓ index → {out/'index.json'}")
    print("\nNow: read the frames (as images) + transcript.txt, aligned by index.json timestamps, and answer grounded in both.")


if __name__ == "__main__":
    main()
