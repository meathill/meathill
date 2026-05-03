#!/usr/bin/env python3
"""Convert out/06_chapters.json (or any chapters JSON) into a `HH:MM:SS title`
text file suitable for pasting into Bilibili / YouTube descriptions.

Bilibili's chapter parser REQUIRES strict `HH:MM:SS` (zero-padded hour)
timestamps — `M:SS` or `H:MM:SS` (no leading zero) won't be recognized.
YouTube accepts the strict form too. So always emit `HH:MM:SS`.
"""
import argparse, json, sys
from pathlib import Path

def hhmmss(t: float) -> str:
    s = int(t); h = s // 3600; m = (s % 3600) // 60; sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="Path to source video (used to locate out/)")
    ap.add_argument("--source", default="06_chapters.json",
                    help="Filename inside out/ (default: 06_chapters.json; "
                         "use 08_final_chapters.json if you want the slate-aware version)")
    ap.add_argument("--target", default=None,
                    help="Output filename inside out/ (default: <source>.txt)")
    args = ap.parse_args()

    out = Path(args.video).resolve().parent / "out"
    src = out / args.source
    if not src.exists():
        print(f"[err] {src} not found", file=sys.stderr); sys.exit(2)
    chapters = json.loads(src.read_text(encoding="utf-8"))

    target_name = args.target or src.with_suffix(".txt").name
    target = out / target_name
    lines = [f"{hhmmss(c['start'])} {c['title']}" for c in chapters]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {target} ({len(chapters)} chapters)")
    print(target.read_text())

    # B 站章节标题硬上限 16 字，超过会被截断 / 不识别。warn.
    overlong = [(i, c["title"], len(c["title"]))
                for i, c in enumerate(chapters, start=1) if len(c["title"]) > 16]
    if overlong:
        print()
        print(f"[warn] {len(overlong)} 个章节标题 >16 字，B 站会截断或不识别：",
              file=sys.stderr)
        for i, t, n in overlong:
            print(f"  {i}: {n} 字 — {t}", file=sys.stderr)
        print("  → 回到 06_chapters.json 改短再跑一遍 06b。", file=sys.stderr)

if __name__ == "__main__":
    main()
