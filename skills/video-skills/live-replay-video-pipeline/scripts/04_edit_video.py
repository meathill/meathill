#!/usr/bin/env python3
"""Apply cut list to the source video. Tries `-c copy` (fast, stream-copy)
first; if a part comes out empty due to keyframe misalignment, falls back to
re-encoding that part. Concats parts with concat demuxer."""
import json, subprocess, sys, shutil
from pathlib import Path

def run(cmd):
    print("[run]", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=False, capture_output=True, text=True)

def cut_part(vid: Path, s: float, e: float, out: Path) -> bool:
    """Try stream-copy first; fall back to re-encode if too small."""
    cmd_copy = [
        "ffmpeg", "-y",
        "-ss", f"{s:.3f}",
        "-i", str(vid),
        "-t", f"{e-s:.3f}",
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        str(out),
    ]
    r = run(cmd_copy)
    if out.exists() and out.stat().st_size > 100_000:
        # sanity: probe duration
        p = subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(out)],
            capture_output=True, text=True,
        )
        try:
            dur = float((p.stdout or "0").strip())
        except ValueError:
            dur = 0
        if dur > (e - s) * 0.7:
            return True
    print("[warn] stream-copy short or failed, re-encoding part", flush=True)
    cmd_re = [
        "ffmpeg", "-y",
        "-ss", f"{s:.3f}", "-to", f"{e:.3f}",
        "-i", str(vid),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        "-avoid_negative_ts", "make_zero",
        str(out),
    ]
    r = run(cmd_re)
    return r.returncode == 0 and out.exists() and out.stat().st_size > 0

def main():
    if len(sys.argv) < 2:
        print("usage: 04_edit_video.py <video_path>")
        sys.exit(2)
    vid = Path(sys.argv[1]).resolve()
    out_dir = vid.parent / "out"
    cuts = json.loads((out_dir / "03_cut_list.json").read_text(encoding="utf-8"))
    edited = out_dir / "04_edited.mp4"
    work = out_dir / "_edit_work"
    work.mkdir(exist_ok=True)
    parts = []
    for i, c in enumerate(cuts):
        part = work / f"part_{i:03d}.mp4"
        ok = cut_part(vid, float(c["start"]), float(c["end"]), part)
        if not ok:
            print(f"[err] failed to cut {c}")
            sys.exit(2)
        parts.append(part)
        print(f"[ok] part {i}: {part} ({part.stat().st_size} bytes)")

    listing = work / "concat.txt"
    listing.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in parts), encoding="utf-8"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c", "copy",
        "-movflags", "+faststart",
        str(edited),
    ]
    run(cmd)
    if not edited.exists():
        # fallback: re-encode the concat
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(edited),
        ]
        run(cmd)
    shutil.rmtree(work, ignore_errors=True)
    print(f"[ok] wrote {edited} ({edited.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
