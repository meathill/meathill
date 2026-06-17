#!/usr/bin/env python3
"""Clean spoken filler (口癖) from the transcript TEXT only — timestamps untouched.

Subtitles + chapter/publish copy read cleanly while the video audio stays natural.
Uses a MiMo chat model (default mimo-v2.5) via the same token as the ASR step, so
no second vendor is needed. Backs up the original to out/02_transcript.raw.json and
rewrites out/02_transcript.json + out/02_transcript.txt with cleaned `text`.

Removes 呃/嗯/啊/噢/哈 and obvious stutters/immediate repeats; keeps meaning, never
merges/splits/reorders, never touches technical terms. Per batch: if the model
returns the wrong count, that batch keeps its originals.

Dependency-free: curl (secrets via -K stdin) + stdlib. Creds from env or
~/.config/live-replay/secrets.env (MIMO_API_KEY, MIMO_BASE_URL).
"""
import argparse, json, subprocess, sys, os, tempfile
from pathlib import Path

SECRETS = Path.home() / ".config" / "live-replay" / "secrets.env"
MIMO_BASE_DEFAULT = "https://api.xiaomimimo.com/v1"
SYS_PROMPT = (
    "你是中文技术直播的字幕校对。删掉口癖：句中的语气词 呃/嗯/啊/噢/哦/唉 和口头禅 哈，"
    "以及明显的重复词和口吃（如「我我」「这个这个」「就是就是」）。但要求：保持原意、"
    "不改写措辞、不要合并或拆分句子、不要改动技术术语和英文词、不要补全或润色。"
    "句末自然的 呢/吧 可保留。输出 JSON 对象 {\"lines\": [...]}，长度必须与输入完全相同，"
    "第 i 项是第 i 句清理后的文本（若该句无需改动则原样返回）。")


def hms(t: float) -> str:
    t = max(0.0, float(t))
    h = int(t // 3600); m = int((t % 3600) // 60); s = t - h*3600 - m*60
    return f"{h:02d}:{m:02d}:{s:06.3f}" if h else f"{m:02d}:{s:06.3f}"


def load_creds():
    env = {}
    if SECRETS.exists():
        for line in SECRETS.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("export "):
                s = s[7:].strip()
            if "=" in s:
                k, v = s.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    key = (os.environ.get("MIMO_API_KEY") or env.get("MIMO_API_KEY")
           or os.environ.get("MIMO_API_TOKEN") or env.get("MIMO_API_TOKEN"))
    base = os.environ.get("MIMO_BASE_URL") or env.get("MIMO_BASE_URL") or MIMO_BASE_DEFAULT
    return key, base


def chat_clean(lines, key, base, model):
    body = {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": SYS_PROMPT},
                         {"role": "user", "content": json.dumps({"lines": lines}, ensure_ascii=False)}]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False)
        bf = f.name
    try:
        cfg = [f'url = "{base}/chat/completions"',
               f'header = "Authorization: Bearer {key}"',
               f'header = "api-key: {key}"',
               'header = "Content-Type: application/json"',
               f'data-binary = "@{bf}"']
        r = subprocess.run(["curl", "-sS", "--max-time", "180", "-K", "-"],
                           input="\n".join(cfg) + "\n", capture_output=True, text=True)
    finally:
        os.unlink(bf)
    if r.returncode != 0:
        raise RuntimeError(f"curl failed: {r.stderr[:300]}")
    content = json.loads(r.stdout)["choices"][0]["message"]["content"]
    return json.loads(content)["lines"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--model", default="mimo-v2.5")
    ap.add_argument("--batch", type=int, default=40)
    args = ap.parse_args()
    vid = Path(args.video).resolve()
    out_dir = vid.parent / "out"
    tj = out_dir / "02_transcript.json"
    transcript = json.loads(tj.read_text(encoding="utf-8"))
    segs = transcript["segments"]
    key, base = load_creds()
    if not key:
        print("[err] no MIMO_API_KEY in env or", SECRETS); sys.exit(2)

    raw = out_dir / "02_transcript.raw.json"
    if not raw.exists():
        raw.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[ok] backed up original -> {raw.name}")

    n = len(segs); changed = 0
    for i in range(0, n, args.batch):
        chunk = segs[i:i + args.batch]
        originals = [s["text"] for s in chunk]
        try:
            cleaned = chat_clean(originals, key, base, args.model)
        except Exception as ex:
            print(f"[warn] batch {i//args.batch} failed ({ex}); keep originals"); continue
        if len(cleaned) != len(chunk):
            print(f"[warn] batch {i//args.batch} length mismatch "
                  f"({len(cleaned)}!={len(chunk)}); keep originals"); continue
        for s, t in zip(chunk, cleaned):
            t = (t or "").strip()
            if t and t != s["text"]:
                s["text"] = t; changed += 1
        print(f"[ok] cleaned {i+1}-{min(i+args.batch, n)} / {n}", flush=True)

    transcript["filler_cleaned"] = True
    tj.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"[{hms(s['start'])} -> {hms(s['end'])}] {s['text']}" for s in segs]
    (out_dir / "02_transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] cleaned {changed}/{n} segments; rewrote 02_transcript.json/.txt "
          f"(original kept at {raw.name})")


if __name__ == "__main__":
    main()
