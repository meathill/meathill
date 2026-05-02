#!/usr/bin/env python3
"""Carve internal silences (gaps between consecutive transcript segments where
no speech happens for more than --min-gap seconds) out of the cut list.

Reads:
  out/02_transcript.json
  out/03_cut_list.json
Writes back:
  out/03_cut_list.json   (in-place; old contents not preserved)
  out/03_cut_list.bak.json  (backup of the previous list)
"""
import argparse, json, sys, shutil
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--min-gap", type=float, default=15.0,
                    help="seconds; gaps of speech longer than this are cut out")
    ap.add_argument("--keep-pad", type=float, default=0.5,
                    help="leave this much speech audible on each side of a gap")
    args = ap.parse_args()

    out_dir = Path(args.video).resolve().parent / "out"
    tr = json.loads((out_dir / "02_transcript.json").read_text(encoding="utf-8"))
    cuts = json.loads((out_dir / "03_cut_list.json").read_text(encoding="utf-8"))
    if (out_dir / "03_cut_list.bak.json").exists():
        # Already once carved — refuse to double-carve
        print("[skip] 03_cut_list.bak.json exists, looks already carved", file=sys.stderr)
        sys.exit(0)
    shutil.copy(out_dir / "03_cut_list.json", out_dir / "03_cut_list.bak.json")

    new_cuts = []
    for c in cuts:
        s, e = float(c["start"]), float(c["end"])
        reason = c.get("reason", "")
        # Overlap-aware: include any seg whose [start,end] intersects [s,e],
        # then clamp to [s,e]. This avoids false-positive "tail dead air" when
        # the cut boundary chops mid-sentence.
        clamped = []
        for seg in tr["segments"]:
            if seg["end"] <= s - 0.1 or seg["start"] >= e + 0.1:
                continue
            a = max(seg["start"], s); b = min(seg["end"], e)
            if b - a > 0.1:
                clamped.append((a, b))
        bounds = []
        if clamped:
            if clamped[0][0] - s > args.min_gap:
                bounds.append(("lead", s, clamped[0][0]))
            for i in range(len(clamped)-1):
                gap = clamped[i+1][0] - clamped[i][1]
                if gap > args.min_gap:
                    bounds.append(("mid", clamped[i][1], clamped[i+1][0]))
            if e - clamped[-1][1] > args.min_gap:
                bounds.append(("tail", clamped[-1][1], e))

        if not bounds:
            new_cuts.append(c)
            continue

        # walk through the range, splitting at each gap
        cursor = s
        for kind, ga, gb in bounds:
            keep_end = ga + args.keep_pad if kind != "lead" else s
            if keep_end > cursor + 0.5:
                new_cuts.append({
                    "start": round(cursor, 3),
                    "end": round(keep_end, 3),
                    "reason": reason + f" [前]"
                })
            cursor = max(cursor, gb - args.keep_pad)
        if e > cursor + 0.5:
            new_cuts.append({
                "start": round(cursor, 3),
                "end": round(e, 3),
                "reason": reason + " [后]"
            })

    # sanity: sort + non-overlap
    new_cuts.sort(key=lambda c: c["start"])
    for i in range(len(new_cuts)-1):
        if new_cuts[i]["end"] > new_cuts[i+1]["start"] + 0.01:
            print(f"[warn] overlap: {new_cuts[i]} vs {new_cuts[i+1]}", file=sys.stderr)

    (out_dir / "03_cut_list.json").write_text(
        json.dumps(new_cuts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total_old = sum(c['end']-c['start'] for c in cuts)
    total_new = sum(c['end']-c['start'] for c in new_cuts)
    print(f"[ok] {len(cuts)} segs ({total_old:.0f}s) -> {len(new_cuts)} segs ({total_new:.0f}s); cut {total_old-total_new:.0f}s of internal silence")
    for c in new_cuts:
        print(f"  {c['start']:.0f}-{c['end']:.0f}  {c['reason']}")

if __name__ == "__main__":
    main()
