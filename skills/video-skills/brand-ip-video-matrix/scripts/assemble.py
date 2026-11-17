#!/usr/bin/env python3
"""
按 JSON 规格装配一条竖版短片。

用法:
    python3 assemble.py spec.json

规格字段（相对路径按当前工作目录解析）:
    out            输出的 1080x1920 交付版路径（必填）
    master         可选，768x1368 母版输出路径
    segments       [{"src": ..., "len": 秒}]，按顺序拼接
    music          {"src":..., "gain":0.30, "offset":0.0}   可选
    water          {"src":..., "gain":0.34, "offset":0.0}   可选
    voice          [{"src":..., "start": 秒, "atempo": 1.0}]
    subtitles      [{"src": png, "start": 秒, "end": 秒}]
    target_lufs    默认 -14
    true_peak      默认 -1.5
    crf            默认 18

短版（只含 B 段）的做法：segments 只放 B 段，所有 voice/subtitle 的 start 减去同一 offset，
music/water 的 offset 填这个值 —— 这样短版就是完整版的中间那一段，逐帧对齐。
"""
import json
import os
import subprocess
import sys

W, H, FPS = 768, 1368, 24


def sh(*args):
    return subprocess.run(list(args), capture_output=True, text=True)


def probe_dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(out)


def norm(src, dst, length):
    """归一化到 768x1368 / 24fps / 精确时长 / yuv420p"""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src,
                    "-t", f"{length}",
                    "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",
                    "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
                    "-an", dst], check=True)


def build(spec, spec_dir):
    cwd = os.getcwd()

    def p(x):
        """输入路径：相对路径优先按当前工作目录解析，找不到再回落到规格文件所在目录"""
        if os.path.isabs(x):
            return x
        if os.path.exists(os.path.join(cwd, x)):
            return os.path.join(cwd, x)
        return os.path.join(spec_dir, x)

    def outp(x):
        """输出路径：相对路径一律按当前工作目录解析"""
        return x if os.path.isabs(x) else os.path.join(cwd, x)

    out = outp(spec["out"])
    master = outp(spec["master"]) if spec.get("master") else None
    work = os.path.join(os.path.dirname(out) or ".", ".assemble-work")
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    # ---- 1. 分段归一化 + concat ----
    segs = []
    for i, s in enumerate(spec["segments"]):
        dst = os.path.join(work, f"s{i}.mp4")
        norm(p(s["src"]), dst, s["len"])
        segs.append(dst)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    video = os.path.join(work, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", lst, "-c", "copy", video], check=True)
    total = probe_dur(video)

    # ---- 2. 混音 ----
    voices = spec.get("voice", [])
    beds = []
    for name in ("music", "water"):
        if spec.get(name):
            beds.append((name, spec[name]))

    inputs = []
    for _, b in beds:
        inputs += ["-i", p(b["src"])]
    for v in voices:
        inputs += ["-i", p(v["src"])]

    parts, labels = [], []
    for i, (name, b) in enumerate(beds):
        off = float(b.get("offset", 0.0))
        trim = f"atrim=start={off},asetpts=N/SR/TB," if off > 0 else ""
        parts.append(f"[{i}]{trim}volume={b.get('gain', 0.3)}[{name}]")
        labels.append(f"[{name}]")
    for j, v in enumerate(voices):
        idx = len(beds) + j
        ms = int(round(float(v["start"]) * 1000))
        at = float(v.get("atempo", 1.0))
        pre = f"atempo={at}," if abs(at - 1.0) > 1e-6 else ""
        parts.append(f"[{idx}]{pre}adelay={ms}|{ms}[v{j}]")
        labels.append(f"[v{j}]")

    n_in = len(beds) + len(voices)
    lufs = spec.get("target_lufs", -14)
    tp = spec.get("true_peak", -1.5)
    fc = (";".join(parts) + ";" +
          f"{''.join(labels)}amix=inputs={n_in}:duration=longest:normalize=0[mix];"
          f"[mix]aresample=48000,loudnorm=I={lufs}:TP={tp}:LRA=11[out]")
    mix = os.path.join(work, "mix.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", fc, "-map", "[out]",
                    "-c:a", "pcm_s16le", "-ar", "48000", mix], check=True)

    # ---- 3. 叠字幕 ----
    subs = spec.get("subtitles", [])
    vin = ["-i", video, "-i", mix]
    for s in subs:
        vin += ["-loop", "1", "-i", p(s["src"])]

    sub_ends, overlays = "", ""
    for i, s in enumerate(subs):
        sub_ends += (f"[{i+2}:v]format=rgba,"
                     f"fade=t=in:st={s['start']:.2f}:d=0.25:alpha=1,"
                     f"fade=t=out:st={max(s['end']-0.25, s['start']):.2f}:d=0.25:alpha=1[s{i}];")
    for i in range(len(subs)):
        src_lbl = "v0" if i == 0 else f"v{i}"
        dst_lbl = "vout" if i == len(subs) - 1 else f"v{i+1}"
        s = subs[i]
        overlays += (f"[{src_lbl}][s{i}]overlay=0:0:format=auto:"
                     f"enable='between(t,{s['start']:.2f},{s['end']:.2f})'[{dst_lbl}];")
    if not subs:
        overlays = "[0:v]null[vout];"
    fc2 = (f"[1:a]atrim=0:{total:.3f},aresample=48000,"
           f"aformat=sample_fmts=fltp:channel_layouts=stereo[aout];"
           f"{sub_ends}{overlays}[vout]format=yuv420p[v420]")

    film = master or os.path.join(work, "film.mp4")
    crf = spec.get("crf", 18)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *vin,
                    "-filter_complex", fc2, "-map", "[v420]", "-map", "[aout]",
                    "-t", f"{total:.3f}", "-shortest",
                    "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
                    "-pix_fmt", "yuv420p", "-crf", str(crf), "-preset", "veryfast",
                    "-threads", "6", "-c:a", "aac", "-profile:a", "aac_low",
                    "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", film], check=True)

    if master:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", film,
                        "-vf", "scale=1080:1920:flags=lanczos,format=yuv420p",
                        "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
                        "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "veryfast",
                        "-threads", "6", "-c:a", "copy", "-movflags", "+faststart",
                        out], check=True)
        print(f"[ok] {out}  {total:.2f}s")
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", film,
                        "-vf", "scale=1080:1920:flags=lanczos,format=yuv420p",
                        "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
                        "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "veryfast",
                        "-threads", "6", "-c:a", "copy", "-movflags", "+faststart",
                        out], check=True)
        print(f"[ok] {out}  {total:.2f}s")

    for s in subs:
        print(f"     字幕 {s['start']:6.2f} → {s['end']:6.2f}")
    for v in voices:
        print(f"     旁白 {v['start']:6.2f}s  {v['src']}")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    spec_path = os.path.abspath(sys.argv[1])
    with open(spec_path) as f:
        spec = json.load(f)
    build(spec, os.path.dirname(spec_path))


if __name__ == "__main__":
    main()
