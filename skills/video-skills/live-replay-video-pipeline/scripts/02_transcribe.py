#!/usr/bin/env python3
"""Transcribe audio with faster-whisper. Saves JSON + human-readable TXT."""
import argparse, json, sys
from pathlib import Path

def hms(t: float) -> str:
    t = max(0.0, float(t))
    h = int(t // 3600); m = int((t % 3600) // 60); s = t - h*3600 - m*60
    return f"{h:02d}:{m:02d}:{s:06.3f}" if h else f"{m:02d}:{s:06.3f}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="Path to source video (used to locate out/ dir & 01_audio.wav)")
    ap.add_argument("--model", default="base", help="tiny | base | small | medium | large-v3")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--compute-type", default="int8")
    args = ap.parse_args()

    vid = Path(args.video).resolve()
    out_dir = vid.parent / "out"
    audio = out_dir / "01_audio.wav"
    if not audio.exists():
        print(f"[err] {audio} not found. Run 01_extract_audio.py first.")
        sys.exit(2)

    out_json = out_dir / "02_transcript.json"
    out_txt = out_dir / "02_transcript.txt"
    if out_json.exists() and out_txt.exists():
        print(f"[skip] transcript already exists at {out_json}")
        return

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[err] faster-whisper not installed. pip install faster-whisper --break-system-packages")
        sys.exit(2)

    print(f"[info] loading model {args.model} (compute_type={args.compute_type})")
    model = WhisperModel(args.model, device="cpu", compute_type=args.compute_type)

    print(f"[info] transcribing {audio}")
    segments, info = model.transcribe(
        str(audio),
        language=args.lang,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        beam_size=5,
        condition_on_previous_text=False,
    )

    out_segments = []
    txt_lines = []
    for seg in segments:
        s = {
            "id": seg.id,
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
        }
        if seg.words:
            s["words"] = [
                {"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word}
                for w in seg.words
            ]
        out_segments.append(s)
        line = f"[{hms(seg.start)} -> {hms(seg.end)}] {seg.text.strip()}"
        txt_lines.append(line)
        print(line, flush=True)

    out_json.write_text(json.dumps({
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "model": args.model,
        "segments": out_segments,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    out_txt.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote {out_json} and {out_txt}")

if __name__ == "__main__":
    main()
