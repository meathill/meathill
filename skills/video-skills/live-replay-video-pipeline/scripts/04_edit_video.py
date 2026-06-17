#!/usr/bin/env python3
"""Apply cut list to the source video.

Two paths, chosen automatically from 03_cut_list.json:

* No segment has a "speed" field (or all == 1.0)  -> ORIGINAL fast path:
  stream-copy each kept range (re-encode fallback per part), concat -c copy.
  Behaviour is unchanged / byte-for-byte with previous versions.

* Any segment has speed > 1.0 -> SPEED path: every part (1x and Nx alike) is
  re-encoded to one identical profile so the concat demuxer can -c copy them.
  Nx parts are time-lapsed (setpts=PTS/N) and MUTED (silent stereo track);
  1x parts keep their audio. See _cuts.py for the timeline math used by 05/06.
"""
import json, subprocess, sys, shutil
from pathlib import Path

import _cuts

# Unified re-encode profile for the speed path. Every part shares these exact
# video/audio params + timebase + GOP so `concat -c copy` is always valid.
ENC_V = ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-r", "30", "-video_track_timescale", "90000", "-g", "60", "-keyint_min", "60"]
ENC_A = ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


def run(cmd):
    print("[run]", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def cut_part(vid: Path, s: float, e: float, out: Path) -> bool:
    """Try stream-copy first; fall back to re-encode if too small. (no-speed path)"""
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


def encode_part(vid: Path, s: float, e: float, sp: float, out: Path) -> bool:
    """Re-encode kept range [s,e] to the unified profile (speed path).
    sp == 1.0 -> keep source audio; sp > 1.0 -> setpts speed-up + silent audio."""
    dur = e - s
    if sp == 1.0:
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{s:.3f}", "-i", str(vid), "-t", f"{dur:.3f}",
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", "fps=30,format=yuv420p",
            *ENC_V, *ENC_A,
            "-fps_mode", "cfr", "-avoid_negative_ts", "make_zero",
            str(out),
        ]
    else:
        out_dur = dur / sp
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{s:.3f}", "-i", str(vid),
            "-f", "lavfi", "-t", f"{out_dur:.3f}",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-map", "0:v:0", "-map", "1:a:0", "-t", f"{out_dur:.3f}",
            "-vf", f"setpts=PTS/{sp},fps=30,format=yuv420p",
            *ENC_V, *ENC_A,
            "-fps_mode", "cfr", "-avoid_negative_ts", "make_zero",
            str(out),
        ]
    r = run(cmd)
    ok = r.returncode == 0 and out.exists() and out.stat().st_size > 0
    if not ok:
        print((r.stderr or "")[-1500:], flush=True)
    return ok


def edit_with_speed(vid: Path, edited: Path, work: Path, segs):
    """Speed path: re-encode every part to one profile, then concat -c copy."""
    parts = []
    for i, (s, e, sp) in enumerate(segs):
        part = work / f"part_{i:03d}.mp4"
        if not encode_part(vid, s, e, sp, part):
            print(f"[err] failed to encode part {i} (s={s:.2f} e={e:.2f} sp={sp})")
            sys.exit(2)
        parts.append(part)
        print(f"[ok] part {i}: sp={sp:g} {part.name} ({part.stat().st_size} bytes)")

    listing = work / "concat.txt"
    listing.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts), encoding="utf-8")
    # No +faststart here (it rewrites the whole moov at the end); remux separately.
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c", "copy", "-avoid_negative_ts", "make_zero", str(edited)])
    if not edited.exists() or edited.stat().st_size == 0:
        print("[err] concat failed")
        sys.exit(2)

    # Best-effort faststart remux (copy-only, cheap on a short output).
    fs = edited.with_suffix(".fs.mp4")
    r = run(["ffmpeg", "-y", "-i", str(edited), "-c", "copy",
             "-movflags", "+faststart", str(fs)])
    if r.returncode == 0 and fs.exists() and fs.stat().st_size > 0:
        fs.replace(edited)
    else:
        fs.unlink(missing_ok=True)
    shutil.rmtree(work, ignore_errors=True)
    print(f"[ok] wrote {edited} ({edited.stat().st_size} bytes, speed path)")


def main():
    if len(sys.argv) < 2:
        print("usage: 04_edit_video.py <video_path>")
        sys.exit(2)
    vid = Path(sys.argv[1]).resolve()
    out_dir = vid.parent / "out"
    edited = out_dir / "04_edited.mp4"
    work = out_dir / "_edit_work"
    work.mkdir(exist_ok=True)

    segs = _cuts.load_segments(out_dir)
    if _cuts.any_speed(segs):
        return edit_with_speed(vid, edited, work, segs)

    # ---- original no-speed path (unchanged) ----
    cuts = json.loads((out_dir / "03_cut_list.json").read_text(encoding="utf-8"))
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
