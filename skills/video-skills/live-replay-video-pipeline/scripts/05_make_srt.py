#!/usr/bin/env python3
"""Project transcript onto the (possibly speed-warped) edited timeline, emit SRT.

Uses _cuts for speed-aware mapping: a point t inside kept segment i maps to
cum[i] + (t - start)/speed[i]. Cues that fall inside a sped-up (speed != 1.0)
segment are DROPPED -- a time-lapse has no intelligible speech."""
import json, sys
from pathlib import Path

import _cuts


def srt_ts(t: float) -> str:
    if t < 0: t = 0
    h = int(t // 3600); m = int((t % 3600) // 60); s = t - h*3600 - m*60
    ms = int(round((s - int(s)) * 1000))
    sec = int(s)
    if ms == 1000:
        sec += 1; ms = 0
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def main():
    if len(sys.argv) < 2:
        print("usage: 05_make_srt.py <video_path>")
        sys.exit(2)
    vid = Path(sys.argv[1]).resolve()
    out_dir = vid.parent / "out"
    transcript = json.loads((out_dir / "02_transcript.json").read_text(encoding="utf-8"))
    segs = _cuts.load_segments(out_dir)
    cum, edited_total = _cuts.build_cum(segs)

    srt = []
    idx = 1
    for seg in transcript["segments"]:
        s, e = float(seg["start"]), float(seg["end"])
        text = seg["text"].strip()
        if not text:
            continue
        # find any kept range that overlaps [s,e] and clip to it
        for i, (cs, ce, sp) in enumerate(segs):
            os_, oe = max(s, cs), min(e, ce)
            if oe - os_ < 0.05:      # no/short overlap
                continue
            if sp != 1.0:            # no subtitles over a time-lapse
                continue
            ms = cum[i] + (os_ - cs) / sp
            me = cum[i] + (oe - cs) / sp
            srt.append(f"{idx}\n{srt_ts(ms)} --> {srt_ts(me)}\n{text}\n")
            idx += 1

    out_srt = out_dir / "05_subtitles.srt"
    out_srt.write_text("\n".join(srt), encoding="utf-8")
    print(f"[ok] wrote {out_srt} ({idx-1} cues, edited total={edited_total:.2f}s)")


if __name__ == "__main__":
    main()
