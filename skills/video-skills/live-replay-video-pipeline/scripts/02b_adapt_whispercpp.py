#!/usr/bin/env python3
"""Convert whisper.cpp output JSON to the pipeline's standard transcript shape.

whisper.cpp JSON shape (with -oj):
{
  "systeminfo": "...",
  "model": {...},
  "params": {...},
  "result": {"language": "zh"},
  "transcription": [
    {"timestamps": {"from": "00:00:01,200", "to": "00:00:04,500"},
     "offsets":   {"from": 1200, "to": 4500},          # ms
     "text": "  你好，今天我们来讲...",
     "tokens":    [{...}, ...]                          # optional, ignored
    },
    ...
  ]
}
"""
import json, sys, re
from pathlib import Path

def hms(t: float) -> str:
    if t < 0: t = 0
    h = int(t // 3600); m = int((t % 3600) // 60); s = t - h*3600 - m*60
    return f"{h:02d}:{m:02d}:{s:06.3f}" if h else f"{m:02d}:{s:06.3f}"

def main():
    if len(sys.argv) != 4:
        print("usage: 02b_adapt_whispercpp.py <whispercpp.json> <out.json> <out.txt>")
        sys.exit(2)
    src = Path(sys.argv[1])
    dst_json = Path(sys.argv[2])
    dst_txt = Path(sys.argv[3])
    data = json.loads(src.read_text(encoding="utf-8"))

    segments = []
    for i, seg in enumerate(data.get("transcription", [])):
        offsets = seg.get("offsets") or {}
        start = offsets.get("from", 0) / 1000.0
        end = offsets.get("to", 0) / 1000.0
        text = (seg.get("text") or "").strip()
        if end <= start or not text:
            continue
        segments.append({"id": i, "start": round(start, 3), "end": round(end, 3), "text": text})

    # heuristic merge into sentence-ish chunks for nicer SRT (whisper.cpp can be very fragmented)
    merged = []
    for s in segments:
        if (
            merged
            and (s["start"] - merged[-1]["end"]) < 0.5
            and len(merged[-1]["text"]) < 30
            and not re.search(r"[。！？!?…]\s*$", merged[-1]["text"])
        ):
            merged[-1]["end"] = s["end"]
            merged[-1]["text"] += s["text"]
        else:
            merged.append(dict(s))
    for i, s in enumerate(merged):
        s["id"] = i

    out = {
        "language": data.get("result", {}).get("language", "zh"),
        "duration": merged[-1]["end"] if merged else 0,
        "model": "whisper.cpp",
        "segments": merged,
    }
    dst_json.parent.mkdir(parents=True, exist_ok=True)
    dst_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    txt_lines = [f"[{hms(s['start'])} -> {hms(s['end'])}] {s['text']}" for s in merged]
    dst_txt.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {dst_json} ({len(merged)} segments) and {dst_txt}")

if __name__ == "__main__":
    main()
