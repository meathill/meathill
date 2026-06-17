#!/usr/bin/env python3
"""Transcribe out/01_audio.wav via cloud ASR and emit the pipeline's standard
out/02_transcript.json + out/02_transcript.txt.

Local whisper is weak on Chinese<->English code-switching + technical jargon.
This adapter is MiMo-first:

  --probe-mimo        call MiMo-V2.5-ASR on a short clip and DUMP the raw response.
  --engine mimo       (default) MiMo gives the most accurate text but NO timestamps,
                      so we segment the audio at real silences (silencedetect), send
                      each ~100s chunk to MiMo concurrently, then split each chunk's
                      punctuated text into sentence cues with time distributed by
                      character count. Chunk boundaries are real timestamps.
  --engine whisper1   whisper-1 verbose_json (segment timestamps) + GPT-4o glossary
                      correction. Needs OPENAI_API_KEY.

Dependency-free: `curl` (secrets via -K stdin config, never argv) + ffmpeg.
Creds from env or ~/.config/live-replay/secrets.env
(MIMO_API_KEY, MIMO_BASE_URL, OPENAI_API_KEY).
"""
import argparse, json, subprocess, sys, os, base64, tempfile, re, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

SECRETS = Path.home() / ".config" / "live-replay" / "secrets.env"
MIMO_BASE_DEFAULT = "https://api.xiaomimimo.com/v1"

GLOSSARY = ["Codex", "Claude", "Claude Code", "Cloudflare", "Workers", "R2", "D1", "KV",
            "Vectorize", "OpenNext", "Next.js", "shadcn", "Zustand", "TiDB", "TiDB Cloud",
            "monorepo", "Headless", "agents.md", "Anthropic", "OpenAI", "Vite",
            "TypeScript", "API", "SDK", "vibe coding", "prompt"]
WHISPER_PROMPT = "技术编程直播，中英文混说。常见术语：" + "、".join(GLOSSARY) + "。"


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
    openai_key = os.environ.get("OPENAI_API_KEY") or env.get("OPENAI_API_KEY")
    mimo_key = (os.environ.get("MIMO_API_KEY") or env.get("MIMO_API_KEY")
                or os.environ.get("MIMO_API_TOKEN") or env.get("MIMO_API_TOKEN"))
    mimo_base = (os.environ.get("MIMO_BASE_URL") or env.get("MIMO_BASE_URL")
                 or MIMO_BASE_DEFAULT)
    return openai_key, mimo_key, mimo_base


def curl(config_lines, want_json=True, timeout=3600):
    """Run curl with a -K config supplied on stdin (keeps secrets out of argv)."""
    cfg = "\n".join(config_lines) + "\n"
    r = subprocess.run(["curl", "-sS", "--max-time", str(timeout), "-K", "-"],
                       input=cfg, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl failed ({r.returncode}): {r.stderr[:600]}")
    if not want_json:
        return r.stdout
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"non-JSON response: {r.stdout[:1000]}")


def ff(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def ffprobe_duration(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def compress_opus(wav: Path, out: Path, kbps: int = 24):
    ff(["ffmpeg", "-y", "-i", str(wav), "-c:a", "libopus", "-b:a", f"{kbps}k",
        "-ac", "1", "-ar", "16000", str(out)])


def clip_wav(wav: Path, out: Path, start: float, dur: float):
    ff(["ffmpeg", "-y", "-ss", f"{start}", "-i", str(wav), "-t", f"{dur}",
        "-c", "copy", str(out)])


def write_outputs(out_dir: Path, transcript: dict):
    (out_dir / "02_transcript.json").write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"[{hms(s['start'])} -> {hms(s['end'])}] {s['text']}"
             for s in transcript["segments"]]
    (out_dir / "02_transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] wrote 02_transcript.json/.txt "
          f"({len(transcript['segments'])} segments, model={transcript.get('model')})")


# ---------------- whisper-1 (needs OPENAI_API_KEY) ----------------

def whisper1(audio: Path, openai_key: str) -> dict:
    print(f"[info] whisper-1 transcribing {audio.name} ({audio.stat().st_size//1024}KB) ...",
          flush=True)
    cfg = [
        'url = "https://api.openai.com/v1/audio/transcriptions"',
        f'header = "Authorization: Bearer {openai_key}"',
        f'form = "file=@{audio}"',
        'form = "model=whisper-1"',
        'form = "response_format=verbose_json"',
        'form = "timestamp_granularities[]=segment"',
        'form = "language=zh"',
        f'form = "prompt={WHISPER_PROMPT}"',
    ]
    data = curl(cfg, want_json=True, timeout=3600)
    if "segments" not in data:
        raise RuntimeError(f"whisper-1 unexpected response: {json.dumps(data)[:800]}")
    segs = []
    for i, s in enumerate(data["segments"]):
        text = (s.get("text") or "").strip()
        if not text:
            continue
        segs.append({"id": i, "start": round(float(s["start"]), 3),
                     "end": round(float(s["end"]), 3), "text": text})
    return {"language": data.get("language", "zh"), "duration": data.get("duration", 0),
            "model": "whisper-1", "segments": segs}


def gpt4o_correct(segments, openai_key: str, model: str = "gpt-4o", batch: int = 40):
    sys_prompt = (
        "你是中文技术编程直播的字幕校对。输入是 ASR 自动转写的句子数组（中英混说），"
        "可能把英文技术术语/专有名词识别错。请只做最小校正：修正明显的识别错误，尤其是"
        "技术术语拼写（如 " + "、".join(GLOSSARY[:14]) + " 等）。严格要求：不增删句子、"
        "不合并不拆分、不改顺序、不改变原意、保持口语原貌。输出 JSON 对象 "
        '{"texts": [...]}，texts 长度必须与输入句子数组完全相同，第 i 项是第 i 句校正后的文本。')
    out = list(segments)
    n = len(segments)
    for i in range(0, n, batch):
        chunk = segments[i:i + batch]
        user = json.dumps({"sentences": [s["text"] for s in chunk]}, ensure_ascii=False)
        body = {"model": model, "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": sys_prompt},
                             {"role": "user", "content": user}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
            bodyfile = f.name
        try:
            cfg = ['url = "https://api.openai.com/v1/chat/completions"',
                   f'header = "Authorization: Bearer {openai_key}"',
                   'header = "Content-Type: application/json"',
                   f'data-binary = "@{bodyfile}"']
            resp = curl(cfg, want_json=True, timeout=600)
        finally:
            os.unlink(bodyfile)
        try:
            content = resp["choices"][0]["message"]["content"]
            texts = json.loads(content)["texts"]
        except (KeyError, IndexError, json.JSONDecodeError) as ex:
            print(f"[warn] correction batch {i//batch} failed ({ex}); keeping originals",
                  flush=True)
            continue
        for j, t in enumerate(texts[:len(chunk)]):
            t = (t or "").strip()
            if t:
                out[i + j] = {**chunk[j], "text": t}
        print(f"[ok] corrected sentences {i+1}-{min(i+batch, n)} / {n}", flush=True)
    return out


# ---------------- MiMo (default; text only, timestamps via silence chunking) ----

def mimo_call(clip: Path, mimo_key: str, mimo_base: str, asr_options=None, mime="audio/wav"):
    b64 = base64.b64encode(clip.read_bytes()).decode("ascii")
    msg = {"role": "user", "content": [
        {"type": "input_audio", "input_audio": {"data": f"data:{mime};base64,{b64}"}}]}
    body = {"model": "mimo-v2.5-asr", "messages": [msg]}
    if asr_options:
        body["asr_options"] = asr_options
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False)
        bodyfile = f.name
    try:
        cfg = [f'url = "{mimo_base}/chat/completions"',
               f'header = "Authorization: Bearer {mimo_key}"',
               f'header = "api-key: {mimo_key}"',
               'header = "Content-Type: application/json"',
               f'data-binary = "@{bodyfile}"']
        return curl(cfg, want_json=True, timeout=600)
    finally:
        os.unlink(bodyfile)


def mimo_text(wav: Path, start: float, end: float, key: str, base: str, retries: int = 2) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".wav"); os.close(fd)
    clip = Path(tmp)
    try:
        clip_wav(wav, clip, start, end - start)
        for attempt in range(retries + 1):
            try:
                resp = mimo_call(clip, key, base, asr_options={"language": "auto"})
                return (resp["choices"][0]["message"]["content"] or "").strip()
            except Exception as ex:
                if attempt >= retries:
                    print(f"[warn] chunk {start:.0f}-{end:.0f}s failed: {ex}", flush=True)
                    return ""
    finally:
        clip.unlink(missing_ok=True)
    return ""


def detect_silences(wav: Path, noise="-30dB", min_sil=0.5):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav),
                        "-af", f"silencedetect=noise={noise}:d={min_sil}", "-f", "null", "-"],
                       capture_output=True, text=True)
    sils = []; cur = None
    for line in r.stderr.splitlines():
        m = re.search(r"silence_start:\s*([0-9.]+)", line)
        if m:
            cur = float(m.group(1)); continue
        m = re.search(r"silence_end:\s*([0-9.]+)", line)
        if m and cur is not None:
            sils.append((cur, float(m.group(1)))); cur = None
    return sils


def speech_runs(sils, dur):
    runs = []; prev = 0.0
    for s, e in sils:
        if s > prev + 0.05:
            runs.append((prev, s))
        prev = e
    if dur > prev + 0.05:
        runs.append((prev, dur))
    return runs or [(0.0, dur)]


def plan_chunks(runs, target=100.0, maxlen=200.0):
    chunks = []; cs = None; ce = None
    for s, e in runs:
        if cs is None:
            cs, ce = s, e
        else:
            ce = e
        if ce - cs >= target:
            chunks.append((cs, ce)); cs = ce = None
    if cs is not None:
        chunks.append((cs, ce))
    out = []
    for s, e in chunks:
        if e - s > maxlen:
            n = int((e - s) // maxlen) + 1
            step = (e - s) / n
            for k in range(n):
                out.append((s + k*step, e if k == n-1 else s + (k+1)*step))
        else:
            out.append((s, e))
    return out


def split_sentences(text):
    parts = [p.strip() for p in re.split(r"(?<=[。！？!?…])", text) if p.strip()]
    out = []
    for p in parts:
        if len(p) > 34:                      # break long sentences on commas for readable cues
            buf = ""
            for piece in re.split(r"(?<=[，,、])", p):
                buf += piece
                if len(buf) >= 16:
                    out.append(buf.strip()); buf = ""
            if buf.strip():
                out.append(buf.strip())
        else:
            out.append(p)
    return out


def split_text_to_segments(text, t0, t1, idx0):
    sents = split_sentences(text)
    if not sents:
        return []
    total = sum(len(s) for s in sents) or 1
    segs = []; cur = t0
    for k, s in enumerate(sents):
        dur = (t1 - t0) * (len(s) / total)
        st = cur
        en = t1 if k == len(sents) - 1 else min(t1, cur + dur)
        segs.append({"id": idx0 + k, "start": round(st, 3), "end": round(en, 3), "text": s})
        cur = en
    return segs


def mimo_transcribe(wav: Path, key: str, base: str, target=100.0, maxlen=200.0, concurrency=4):
    dur = ffprobe_duration(wav)
    sils = detect_silences(wav)
    runs = speech_runs(sils, dur)
    chunks = plan_chunks(runs, target, maxlen)
    print(f"[info] {len(sils)} silences -> {len(runs)} speech runs -> {len(chunks)} chunks "
          f"(~{target:.0f}s each), MiMo concurrency={concurrency}", flush=True)
    done = [0]; lock = threading.Lock()

    def work(item):
        i, (s, e) = item
        txt = mimo_text(wav, s, e, key, base)
        with lock:
            done[0] += 1
            print(f"[mimo] {done[0]}/{len(chunks)}  {hms(s)}-{hms(e)}  {len(txt)} chars",
                  flush=True)
        return i, txt

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        results = list(ex.map(work, enumerate(chunks)))
    results.sort()

    segments = []; idx = 0
    for (i, txt), (s, e) in zip(results, chunks):
        if not txt:
            continue
        segs = split_text_to_segments(txt, s, e, idx)
        segments.extend(segs); idx += len(segs)
    return {"language": "zh", "duration": dur, "model": "mimo-v2.5-asr", "segments": segments}


def probe_mimo(wav: Path, mimo_key: str, mimo_base: str):
    print(f"[probe] MiMo base={mimo_base}")
    clip = wav.parent / "_mimo_probe.wav"
    clip_wav(wav, clip, start=300, dur=15)
    for opt in (None, {"language": "auto"}, {"language": "auto", "enable_timestamp": True},
                {"language": "auto", "timestamp": True}, {"format": "srt"}):
        print(f"\n[probe] asr_options={opt!r}")
        try:
            resp = mimo_call(clip, mimo_key, mimo_base, asr_options=opt)
            print(json.dumps(resp, ensure_ascii=False, indent=2)[:2500])
        except Exception as ex:
            print(f"[probe] error: {ex}")
    clip.unlink(missing_ok=True)


# ---------------- main ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--engine", choices=["mimo", "whisper1"], default="mimo")
    ap.add_argument("--probe-mimo", action="store_true")
    ap.add_argument("--no-correct", action="store_true", help="whisper1: skip GPT-4o pass")
    ap.add_argument("--correct-model", default="gpt-4o")
    ap.add_argument("--chunk-target", type=float, default=100.0)
    ap.add_argument("--chunk-max", type=float, default=200.0)
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()

    vid = Path(args.video).resolve()
    out_dir = vid.parent / "out"
    wav = out_dir / "01_audio.wav"
    if not wav.exists():
        print(f"[err] {wav} not found; run 01_extract_audio.py first")
        sys.exit(2)
    openai_key, mimo_key, mimo_base = load_creds()

    if args.probe_mimo:
        if not mimo_key:
            print("[err] no MIMO_API_KEY in env or", SECRETS); sys.exit(2)
        probe_mimo(wav, mimo_key, mimo_base)
        return

    if args.engine == "mimo":
        if not mimo_key:
            print("[err] no MIMO_API_KEY in env or", SECRETS); sys.exit(2)
        transcript = mimo_transcribe(wav, mimo_key, mimo_base,
                                     target=args.chunk_target, maxlen=args.chunk_max,
                                     concurrency=args.concurrency)
        write_outputs(out_dir, transcript)
    elif args.engine == "whisper1":
        if not openai_key:
            print("[err] no OPENAI_API_KEY in env or", SECRETS); sys.exit(2)
        ogg = out_dir / "01_audio.ogg"
        if not ogg.exists():
            print("[info] compressing audio to opus/ogg for upload ...", flush=True)
            compress_opus(wav, ogg)
        transcript = whisper1(ogg, openai_key)
        if not args.no_correct:
            print(f"[info] GPT-4o correction pass ({args.correct_model}) over "
                  f"{len(transcript['segments'])} sentences ...", flush=True)
            transcript["segments"] = gpt4o_correct(
                transcript["segments"], openai_key, model=args.correct_model)
            transcript["model"] = f"whisper-1+{args.correct_model}"
        write_outputs(out_dir, transcript)


if __name__ == "__main__":
    main()
