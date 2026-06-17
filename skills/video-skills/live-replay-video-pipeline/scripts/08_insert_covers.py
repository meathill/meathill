#!/usr/bin/env python3
"""Insert chapter cover slates into the edited video.

Reads:
  out/04_edited.mp4
  out/06_chapters.json
  out/covers/<idx>_<title>.png
Writes:
  out/08_final.mp4                  # video with title slates
  out/08_final_subtitles.srt        # SRT with timestamps shifted to match
  out/08_final_chapters.txt         # YouTube/B-station chapter list (final video)
  out/08_final_chapters.json        # JSON form

Strategy:
  - Build a slate mp4 from each PNG (3s, silent), encoded with the SAME video
    params as 04_edited.mp4 so the concat demuxer can stream-copy them.
  - Cut 04_edited.mp4 into 8 chapter parts using -ss BEFORE -c copy. With a
    2-second GOP, boundaries drift up to 2s — visually invisible.
  - Concat: slate1 + chap1 + slate2 + chap2 + ... + slate8 + chap8
  - Reproject SRT and chapters by adding (i * SLATE_SEC) to every timestamp
    inside chapter i (1-indexed).
"""
import argparse, json, subprocess, sys, shutil
from pathlib import Path

SLATE_SEC = 3.0

def run(cmd, **kw):
    print("[run]", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)

def probe_fps(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe","-v","error","-select_streams","v:0",
         "-show_entries","stream=r_frame_rate","-of","default=nk=1:np=0", str(p)],
        capture_output=True, text=True,
    )
    val = (r.stdout or "").strip() or "30/1"
    try:
        num, den = val.split("/"); fps = float(num) / float(den)
    except Exception:
        fps = 30.0
    return fps if fps > 0 else 30.0


def probe_timescale(p: Path) -> int:
    r = subprocess.run(
        ["ffprobe","-v","error","-select_streams","v:0",
         "-show_entries","stream=time_base","-of","default=nk=1:np=0", str(p)],
        capture_output=True, text=True,
    )
    tb = (r.stdout or "").strip() or "1/90000"
    try:
        return int(tb.split("/")[1])
    except Exception:
        return 90000


def make_slate(png: Path, out: Path, fps: float, timescale: int, dur: float = SLATE_SEC):
    """Render a still PNG as a short silent mp4 whose video fps + timebase MATCH
    04_edited.mp4, so the concat demuxer can stream-copy slate + chapter parts
    (works for the 30fps speed path and the 60fps no-speed path alike)."""
    fps_s = f"{fps:.6g}"
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", fps_s, "-t", f"{dur:.3f}", "-i", str(png),
        "-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", fps_s,
        "-video_track_timescale", str(timescale),
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        "-shortest",
        str(out),
    ]
    run(cmd)

def cut_chapter(src: Path, s: float, e: float, out: Path):
    """Stream-copy [s, e] out of src. May drift to nearest preceding keyframe."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{s:.3f}",
        "-i", str(src),
        "-t", f"{e-s:.3f}",
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        str(out),
    ]
    run(cmd)

def srt_ts(t: float) -> str:
    if t < 0: t = 0
    h = int(t // 3600); m = int((t % 3600) // 60); s = t - h*3600 - m*60
    ms = int(round((s - int(s)) * 1000))
    sec = int(s)
    if ms == 1000: sec += 1; ms = 0
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

def shift_srt(src_srt: Path, dst_srt: Path, chapters):
    """Shift every cue by SLATE_SEC * i where i = 1..N is the chapter the cue
    falls into (1-indexed). Cues at exact chapter boundary go into the chapter
    that begins there."""
    text = src_srt.read_text(encoding="utf-8")
    blocks = [b for b in text.strip().split("\n\n") if b.strip()]
    out_blocks = []
    out_idx = 1
    for b in blocks:
        lines = b.splitlines()
        # find the timing line (HH:MM:SS,mmm --> HH:MM:SS,mmm)
        timing_idx = None
        for j, ln in enumerate(lines):
            if "-->" in ln:
                timing_idx = j; break
        if timing_idx is None: continue
        ts_a, ts_b = [t.strip() for t in lines[timing_idx].split("-->")]
        def to_sec(s):
            h,m,rest = s.split(":"); sec,ms = rest.split(",")
            return int(h)*3600+int(m)*60+int(sec)+int(ms)/1000
        a = to_sec(ts_a); b2 = to_sec(ts_b)
        # which chapter does cue START fall into? Add SLATE_SEC * chapter_idx
        chap_idx = 1
        for i, ch in enumerate(chapters):
            if ch["start"] <= a < ch["end"]:
                chap_idx = i + 1
                break
        offset = SLATE_SEC * chap_idx
        new_a = a + offset
        new_b = b2 + offset
        text_lines = lines[timing_idx+1:]
        out_blocks.append(
            f"{out_idx}\n{srt_ts(new_a)} --> {srt_ts(new_b)}\n" + "\n".join(text_lines)
        )
        out_idx += 1
    dst_srt.write_text("\n\n".join(out_blocks) + "\n", encoding="utf-8")
    print(f"[ok] wrote shifted SRT: {dst_srt} ({out_idx-1} cues)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    args = ap.parse_args()
    vid = Path(args.video).resolve()
    out_dir = vid.parent / "out"
    edited = out_dir / "04_edited.mp4"
    chapters = json.loads((out_dir / "06_chapters.json").read_text(encoding="utf-8"))
    covers_dir = out_dir / "covers"
    work = out_dir / "_insert_work"
    work.mkdir(exist_ok=True)

    # 1. Build slates
    cover_files = sorted(covers_dir.glob("*.png"))
    if len(cover_files) != len(chapters):
        print(f"[err] {len(cover_files)} covers vs {len(chapters)} chapters",
              file=sys.stderr)
        sys.exit(2)
    edited_fps = probe_fps(edited)
    edited_ts = probe_timescale(edited)
    print(f"[info] matching slates to edited.mp4: {edited_fps:g}fps, timescale {edited_ts}")
    slates = []
    for i, cov in enumerate(cover_files, start=1):
        slate = work / f"slate_{i:02d}.mp4"
        if not slate.exists() or slate.stat().st_size == 0:
            make_slate(cov, slate, edited_fps, edited_ts)
        slates.append(slate)

    # 2. Cut chapter parts from edited.mp4
    parts = []
    for i, ch in enumerate(chapters, start=1):
        part = work / f"chap_{i:02d}.mp4"
        if not part.exists() or part.stat().st_size == 0:
            cut_chapter(edited, float(ch["start"]), float(ch["end"]), part)
        parts.append(part)

    # 3. Concat: slate1+chap1+slate2+chap2+...
    listing = work / "concat.txt"
    interleaved = []
    for s, p in zip(slates, parts):
        interleaved.append(s); interleaved.append(p)
    listing.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in interleaved), encoding="utf-8"
    )
    final = out_dir / "08_final.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c", "copy",
        str(final),
    ]
    run(cmd)
    print(f"[ok] final video: {final} ({final.stat().st_size} bytes)")

    # 4. Shift SRT
    shift_srt(out_dir / "05_subtitles.srt",
              out_dir / "08_final_subtitles.srt",
              chapters)

    # 5. Compute final chapter timestamps (each chapter starts at its slate)
    final_chs = []
    cum = 0.0
    for i, ch in enumerate(chapters, start=1):
        seg_dur = float(ch["end"]) - float(ch["start"])
        chap_start = cum  # slate begins
        chap_end = cum + SLATE_SEC + seg_dur
        final_chs.append({
            "title": ch["title"],
            "start": round(chap_start, 1),
            "end": round(chap_end, 1),
        })
        cum = chap_end
    (out_dir / "08_final_chapters.json").write_text(
        json.dumps(final_chs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # B 站章节要严格 HH:MM:SS（小时也要零填充），YouTube 也吃这个格式
    lines = []
    for c in final_chs:
        s = int(c["start"]); h = s // 3600; m = (s % 3600) // 60; sec = s % 60
        ts = f"{h:02d}:{m:02d}:{sec:02d}"
        lines.append(f"{ts} {c['title']}")
    (out_dir / "08_final_chapters.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("[ok] final chapters:")
    print((out_dir / "08_final_chapters.txt").read_text())
    shutil.rmtree(work, ignore_errors=True)  # 成功后清掉 _insert_work（否则会遗留数 GB 中间片段）

if __name__ == "__main__":
    main()
