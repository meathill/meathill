#!/usr/bin/env python3
"""Extract 16kHz mono PCM16 wav from a video for transcription."""
import sys, subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("usage: 01_extract_audio.py <video_path>")
        sys.exit(2)
    vid = Path(sys.argv[1]).resolve()
    out_dir = vid.parent / "out"
    out_dir.mkdir(exist_ok=True)
    out_wav = out_dir / "01_audio.wav"
    if out_wav.exists() and out_wav.stat().st_size > 0:
        print(f"[skip] {out_wav} already exists ({out_wav.stat().st_size} bytes)")
        return
    cmd = [
        "ffmpeg", "-y", "-i", str(vid),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(out_wav),
    ]
    print("[run]", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"[ok] wrote {out_wav} ({out_wav.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
