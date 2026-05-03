#!/usr/bin/env python3
"""Generate a starter `09_publish_package.md` with chapter timestamps and the
section skeleton already filled in. The LLM then reads the transcript +
this starter and replaces every `<TODO: ...>` with real content based on
`prompts/publish_package_prompt.md`.

Reads:
  out/08_final_chapters.json  (preferred)  OR  out/06_chapters.json
  out/08_final.mp4            (for duration)  OR  out/04_edited.mp4
Writes:
  out/09_publish_package.md   (starter; LLM fills the TODOs)
"""
import argparse, json, subprocess, sys
from pathlib import Path

def fmt_ts(s: float) -> str:
    s = int(s); m = s // 60; sec = s % 60; h = m // 60; m = m % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

def get_duration(p: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0", str(p)],
        text=True,
    )
    return float(out.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="Path to the source video (used to locate out/)")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing 09_publish_package.md (default: refuse)")
    args = ap.parse_args()
    out = Path(args.video).resolve().parent / "out"
    target = out / "09_publish_package.md"
    if target.exists() and not args.force:
        print(f"[skip] {target} already exists. Use --force to overwrite.",
              file=sys.stderr)
        sys.exit(0)

    # Prefer the post-slate-insertion artifacts; fall back to pre-slate.
    chapters_path = out / "08_final_chapters.json"
    if not chapters_path.exists():
        chapters_path = out / "06_chapters.json"
    video_path = out / "08_final.mp4"
    if not video_path.exists():
        video_path = out / "04_edited.mp4"
    if not chapters_path.exists() or not video_path.exists():
        print(f"[err] need chapters json + video mp4 in {out}", file=sys.stderr)
        sys.exit(2)

    chapters = json.loads(chapters_path.read_text(encoding="utf-8"))
    duration = get_duration(video_path)
    minutes = int(round(duration / 60))

    chapter_lines = "\n".join(f"{fmt_ts(c['start'])} {c['title']}" for c in chapters)

    md = f"""# 发布包 · <TODO: 视频主题（一句话点题）>

> 视频时长 {minutes} 分钟｜中文｜<TODO: 定位，例如 技术向 / 教学向 / 故事向>｜适合上传 <TODO: 平台列表>
> 文件：`out/{video_path.name}`｜字幕：`out/08_final_subtitles.srt`

---

## 一、标题候选

<TODO: 3–5 条标题，每条 ≤30 字。每条后面括号里标注定位
（如「信息量最大」/「故事感」/「贩卖焦虑 - 不推荐」）。
最后一句指明首选 + 备选。>

---

## 二、描述（B 站 / YouTube 通用）

```
<TODO: 开场两三句话，讲清楚这期讲什么、为什么值得看>

<TODO: 3–5 个 bullet 列出关键内容>

⏱️ 章节
{chapter_lines}

🔗 相关
<TODO: 项目链接 / 博客 / GitHub / 合作链接 — 不知道就留 TODO>

<TODO: 频道 / 直播节奏的一句话介绍>

<TODO: 3–5 个 #标签>
```

---

## 三、标签（5–10 个）

| 平台 | 标签 |
|------|------|
| B 站 | <TODO> |
| YouTube | <TODO> |
| 视频号 | <TODO> |

---

## 四、封面图生成 prompt

**主封面** (1920×1080)：

```
<TODO: 一段英文 prompt（Midjourney / DALL-E / nano-banana 通用），包含：
- composition（构图）
- color palette（带 hex 色号）
- title text overlay（中文标题 + 副标题原文）
- style notes（不要陈词滥调，比如「避免机器人脸」）
- aspect ratio + resolution>
```

**子封面**（如有需要，1080×1080 或 9:16）：

```
<TODO: optional 子主题封面 prompt>
```

---

## 五、社交动态文案

**B 站动态 / 朋友圈**：

```
<TODO: 中文，短，配主封面图>
```

**Twitter / X**（英文，280 字符内）：

```
<TODO: english version, link at the end>
```

**微信公众号引流**（一句话）：

```
<TODO: one sentence>
```

---

## 六、上传前 checklist

- [ ] 检查 `{video_path.name}` 时长 ≈ {minutes} 分钟
- [ ] 上传字幕 `08_final_subtitles.srt`
- [ ] 描述区粘贴章节列表，YouTube 会自动识别成 chapters
- [ ] 主封面用上面 prompt 生成；如平台压缩字号，手动加文字图层
- [ ] B 站补「视频简介」字段（复用第二节描述前两段）
- [ ] 视频号选话题（<TODO: 主题>）
- [ ] 发完同步发布动态文案
"""
    target.write_text(md, encoding="utf-8")
    print(f"[ok] wrote starter {target} ({len(chapters)} chapters, {minutes}min video)")
    print(f"[next] 打开它，按 prompts/publish_package_prompt.md 把所有 <TODO: …> 填掉")

if __name__ == "__main__":
    main()
