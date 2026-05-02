#!/usr/bin/env python3
"""Project transcript onto edited timeline and emit SRT."""
import json, sys
from pathlib import Path

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
    cuts = json.loads((out_dir / "03_cut_list.json").read_text(encoding="utf-8"))
    cuts = sorted([(float(c["start"]), float(c["end"])) for c in cuts], key=lambda x: x[0])

    # Build mapping from original time -> edited time for points inside kept ranges.
    # cumulative offset before each kept range:
    cum = []
    acc = 0.0
    for s, e in cuts:
        cum.append(acc)
        acc += (e - s)
    edited_total = acc

    def map_time(t: float):
        # returns mapped time or None if cut
        for i, (s, e) in enumerate(cuts):
            if s <= t <= e:
                return cum[i] + (t - s)
        return None

    srt = []
    idx = 1
    for seg in transcript["segments"]:
        s, e = float(seg["start"]), float(seg["end"])
        # find any kept range that overlaps [s,e] and clip to it
        for i, (cs, ce) in enumerate(cuts):
            os_, oe = max(s, cs), min(e, ce)
            if oe - os_ < 0.05:  # too short to be a subtitle
                continue
            ms = cum[i] + (os_ - cs)
            me = cum[i] + (oe - cs)
            text = seg["text"].strip()
            if not text:
                continue
            srt.append(f"{idx}\n{srt_ts(ms)} --> {srt_ts(me)}\n{text}\n")
            idx += 1

    out_srt = out_dir / "05_subtitles.srt"
    out_srt.write_text("\n".join(srt), encoding="utf-8")
    print(f"[ok] wrote {out_srt} ({idx-1} cues, edited total={edited_total:.2f}s)")

if __name__ == "__main__":
    main()
