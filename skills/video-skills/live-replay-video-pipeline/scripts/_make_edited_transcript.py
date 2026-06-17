#!/usr/bin/env python3
"""Produce a human-readable transcript whose timestamps are aligned to the
edited video. Input: 02_transcript.json + 03_cut_list.json. Output:
out/_edited_transcript.txt (used by the LLM step that generates chapters).

Speed-aware via _cuts: sped-up (speed != 1.0) segments carry no intelligible
speech, so each is collapsed to a single ⏩ marker line at its edited-timeline
position, letting the chapter author see where the time-lapses sit."""
import json, sys
from pathlib import Path

import _cuts


def hms(t: float) -> str:
    if t < 0: t = 0
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t - h*3600 - m*60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def main():
    if len(sys.argv) < 2:
        print("usage: _make_edited_transcript.py <video_path>")
        sys.exit(2)
    vid = Path(sys.argv[1]).resolve()
    out_dir = vid.parent / "out"
    transcript = json.loads((out_dir / "02_transcript.json").read_text(encoding="utf-8"))
    raw = sorted(
        json.loads((out_dir / "03_cut_list.json").read_text(encoding="utf-8")),
        key=lambda c: float(c["start"]),
    )
    segs = [(float(c["start"]), float(c["end"]), float(c.get("speed", 1.0))) for c in raw]
    reasons = [c.get("reason", "") for c in raw]
    cum, total = _cuts.build_cum(segs)

    entries = []  # (edited_start, line)
    # one ⏩ marker per sped-up segment
    for i, (s, e, sp) in enumerate(segs):
        if sp != 1.0:
            ms = cum[i]
            me = cum[i] + (e - s) / sp
            entries.append((ms, f"[{hms(ms)}-{hms(me)}] (⏩ {sp:g}x 时间流逝: {reasons[i]})"))
    # 1x transcript lines
    for seg in transcript["segments"]:
        s, e = float(seg["start"]), float(seg["end"])
        text = seg["text"].strip()
        if not text:
            continue
        for i, (cs, ce, sp) in enumerate(segs):
            if sp != 1.0:
                continue
            os_, oe = max(s, cs), min(e, ce)
            if oe - os_ < 0.05:
                continue
            ms = cum[i] + (os_ - cs) / sp
            me = cum[i] + (oe - cs) / sp
            entries.append((ms, f"[{hms(ms)}-{hms(me)}] {text}"))
            break

    entries.sort(key=lambda x: x[0])
    lines = [f"# Edited timeline duration: {hms(total)} ({total:.1f}s)\n"]
    lines += [t for _, t in entries]
    out_txt = out_dir / "_edited_transcript.txt"
    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_txt}")


if __name__ == "__main__":
    main()
