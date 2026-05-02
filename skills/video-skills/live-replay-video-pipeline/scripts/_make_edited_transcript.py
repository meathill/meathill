#!/usr/bin/env python3
"""Produce a human-readable transcript whose timestamps are aligned to the
edited video. Input: 02_transcript.json + 03_cut_list.json. Output:
out/_edited_transcript.txt (used by the LLM step that generates chapters)."""
import json, sys
from pathlib import Path

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
    cuts = sorted(
        [(float(c["start"]), float(c["end"])) for c in
         json.loads((out_dir / "03_cut_list.json").read_text(encoding="utf-8"))],
        key=lambda x: x[0],
    )
    cum = []; acc = 0.0
    for s, e in cuts:
        cum.append(acc); acc += (e - s)
    total = acc

    lines = [f"# Edited timeline duration: {hms(total)} ({total:.1f}s)\n"]
    for seg in transcript["segments"]:
        s, e = float(seg["start"]), float(seg["end"])
        for i, (cs, ce) in enumerate(cuts):
            os_, oe = max(s, cs), min(e, ce)
            if oe - os_ < 0.05: continue
            ms = cum[i] + (os_ - cs); me = cum[i] + (oe - cs)
            text = seg["text"].strip()
            if not text: continue
            lines.append(f"[{hms(ms)}-{hms(me)}] {text}")
            break
    out_txt = out_dir / "_edited_transcript.txt"
    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_txt}")

if __name__ == "__main__":
    main()
