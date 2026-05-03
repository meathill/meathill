---
name: live-replay-video-pipeline
description: |
  把直播录像处理成可发布的视频包：保留 transcription、根据 transcription 自动剪掉冗余、
  为剪辑后视频生成 SRT 字幕、生成章节（标题 + 起止时间）、为每个章节生成截图加标题封面，
  并把封面插入最终视频。当用户提供 .mp4/.mov/.mkv 直播录像并要求剪辑/转写/出字幕/出
  章节/出封面/做章节卡时触发。
---

# Live Replay Video Pipeline

把一段直播录像处理成"成片包"：剪掉开场寒暄 / whisper 幻觉 / 长停顿，给剪辑后视频
出 SRT、章节、章节封面，并把封面作为 3 秒标题卡插到每章前面。产出物全部留在视频
所在目录的 `out/`：

```
<视频所在目录>/
├── run_transcribe.command          # 给 Mac 用户双击跑 whisper-cpp 的入口
└── out/
    ├── 02_transcript.json          # 带时间戳的原始转写（source of truth）
    ├── 02_transcript.txt           # 人读版 [mm:ss] 句子
    ├── 03_cut_list.json            # 保留段列表（LLM 生成 → 03b 再细化）
    ├── 04_edited.mp4               # 剪辑后视频（仅 cut，不带封面）
    ├── 05_subtitles.srt            # 对齐到 04_edited.mp4 的 SRT
    ├── 06_chapters.json            # 章节（04_edited 时间轴）
    ├── 06_chapters.txt             # YouTube/B 站可贴的章节文本
    ├── covers/                     # 章节封面 PNG（07 出，08 用）
    ├── 08_final.mp4                # 最终视频：每章前面插 3 秒封面卡
    ├── 08_final_subtitles.srt      # 时间轴已加上 slate 偏移的 SRT
    ├── 08_final_chapters.json
    ├── 08_final_chapters.txt       # 章节时间已对齐到 08_final.mp4
    └── 09_publish_package.md       # 标题/描述/标签/封面 prompt/动态文案
```

中间产物（01_audio.wav、_whispercpp.json、_edited_transcript.txt、_insert_work/、
_edit_work/）跑完都可以删掉；transcription 与各个步骤产物按需保留。

## 与 livestream-to-podcast 的区别

姊妹 skill `livestream-to-podcast` 专注于**音频清洗 + 上传素材**（去底噪、响度
标准化、片头片尾裁剪、生成简介/标签/封面 prompt）。本 skill 专注于**视频剪辑 +
章节化结构**（按 transcription 剪冗余、出对齐字幕、生成可视化章节封面并插到视频
里）。两者可以串：先 podcast 那一套清音频、再用本 skill 出章节化的视频版。

## 主流程（9 步）

### 1. 抽音频（01）

```
python3 scripts/01_extract_audio.py <video>
```
ffmpeg 出 16kHz/mono PCM。80 分钟视频 ~20 秒搞定。

### 2. 转写（02 + 02b）

`huggingface.co` 在 Cowork 沙箱代理里被拒（403），faster-whisper / openai-whisper
都下不了模型。所以转写在**用户 Mac 本地**用 whisper-cpp 跑：

1. 把 `assets/run_transcribe.command` 复制到视频所在目录
2. 用户 Finder 双击 `run_transcribe.command`（Terminal 自动打开并跑）
3. 脚本自动找 `whisper-cli` / `whisper-cpp` / `main`，自动找
   `~/whisper.cpp/models/ggml-*.bin`、`/opt/homebrew/share/whisper-cpp/models/`、
   MacWhisper 模型路径等
4. 跑完调 `scripts/02b_adapt_whispercpp.py` 把 whisper.cpp 的 JSON 转成
   pipeline 标准格式 `02_transcript.json` + `02_transcript.txt`

LLM（你）用 computer-use 自动化：Finder 浏览到文件 → 双击。**注意：**`.command`
的双击会在 Mac 主屏（不一定是当前 Cowork 显示器）的 Terminal 里打开，必要时
`switch_display` 看进度。

### 3. 生成 cut list（LLM 步）

调用方（LLM）读 `out/02_transcript.txt`，按 `prompts/cut_list_prompt.md` 决定
保留哪些段，输出 `out/03_cut_list.json`。重点是把开场寒暄、whisper 在静音段产生
的重复 hallucination（常见模式：同一句话重复 30 次）、长停顿剪掉。

### 3b. 自动剪掉内部静音（推荐）

```
python3 scripts/03b_carve_silences.py <video> --min-gap 15
```
扫 `02_transcript.json`，在每个保留段内找连续 segment 之间 / 段首段尾的 dead air
（**overlap-aware**：跨越大段边界的 segment 视为有内容，不会误判半句话为静音），
超过阈值的从 cut list 里剜掉。原 cut list 备份到 `03_cut_list.bak.json`。
建议阈值 10–15 秒。跑完必须重跑 04 / 05 / 06。

### 4. 剪辑（04）

```
python3 scripts/04_edit_video.py <video>
```
优先 `-c copy` 直接拷贝流不重新编码——80 分钟视频 ~30 秒切完，画质零损失。

注意点：
- `-c copy` 切片从最近的关键帧开始，可能比指定的 start 早 0~2 秒，无伤大雅。
- 拼接时**不要加 `-movflags +faststart`**——faststart 要在结尾把整个文件重写
  一遍，在受 45s 超时的沙箱里很容易被打断、出 moov 缺失。要 faststart 可以
  上传前单独再 remux。
- 如果某段 stream-copy 出来太短或失败，自动 fallback 到 ultrafast 重编码。

### 5. SRT（05）

```
python3 scripts/05_make_srt.py <video>
```
把原 transcript 投影到剪辑后时间轴。落在保留段内的句子：时间 = 段起点 + 偏移；
落在被剪掉部分的整条丢弃。

### 6. 章节（LLM 步）

```
python3 scripts/_make_edited_transcript.py <video>
```
生成对齐到剪辑后时间轴的 `_edited_transcript.txt`，调用方按
`prompts/chapters_prompt.md` 划 4–10 个章节，写入 `out/06_chapters.json`。

```
python3 scripts/06b_chapters_to_txt.py <video>
```
把 `06_chapters.json` 转成 `06_chapters.txt`，**严格 `HH:MM:SS 标题` 格式**——
B 站章节解析器要求小时也零填充（`00:02:38` 而不是 `02:38` 或 `2:38`），YouTube
也吃这个格式。脚本支持 `--source 08_final_chapters.json` 用同一逻辑生成
slate-aware 版本。

### 7. 章节封面（07）

```
python3 scripts/07_make_covers.py <video>
```
对每个章节，在 `start + 0.4*(end-start)` 处用 ffmpeg 截一帧（来源优先剪辑后
视频），用 PIL 在底部叠半透明黑条 + 章节标题 + 序号徽章。

**中英混排字体**：脚本用 CJK + Latin 两套字体，逐字符选择。CJK 优先 PingFang
（mac）、Noto CJK、WQY、Droid Fallback；Latin 优先 SF / DejaVu / Lato。
**不要只用 DroidSansFallbackFull**——它没有 Latin glyph，英文字符会变方块。

### 8. 封面插入视频（08）

```
python3 scripts/08_insert_covers.py <video>
```
把 `covers/` 里的 8 张 PNG 各做成 3 秒静音 mp4（强制 `-video_track_timescale
90000` 跟 `04_edited.mp4` 时间基对齐，否则 concat `-c copy` 时长会乱跑），
切 `04_edited.mp4` 成 8 个 chapter 片段，交叉 concat 出 `08_final.mp4`。
同时按章节序号给 SRT 时间戳加 `3*i` 秒，按各 slate / chap 实测时长重写
`08_final_chapters.txt/.json`。

### 9. 发布包（LLM 步 + 09 starter 脚本）

```
python3 scripts/09_make_publish_starter.py <video>
```
脚本读 `08_final_chapters.json` 与 `08_final.mp4`（或 fallback 到 06/04），
生成 `out/09_publish_package.md` **starter**：章节时间和文件名都已填好，标题/
描述/标签/封面 prompt/动态文案处都是 `<TODO: …>` 占位。

调用方（LLM）然后读 `02_transcript.txt`（或 `_edited_transcript.txt`）+ starter，
按 `prompts/publish_package_prompt.md` 把所有 TODO 填掉。

发布包结构：
- 一、3–5 条标题候选（≤30 字，带定位标注）
- 二、描述（B 站 / YouTube 通用，含章节、链接、hashtag）
- 三、标签（B 站 / YouTube / 视频号 三平台）
- 四、封面图生成 prompt（主封面 1920×1080 + 可选子封面）
- 五、社交动态文案（B 站动态 / Twitter / 微信公众号引流）
- 六、上传前 checklist

## 一次性跑通的命令清单

```bash
SKILL=/path/to/video-skills/live-replay-video-pipeline
VIDEO=/path/to/your/<video>.mp4

# 1. 抽音频
python3 "$SKILL/scripts/01_extract_audio.py" "$VIDEO"

# 2. 转写（Mac 本地，用 whisper-cpp）
cp "$SKILL/assets/run_transcribe.command" "$(dirname "$VIDEO")/"
chmod +x "$(dirname "$VIDEO")/run_transcribe.command"
# 双击它（或 bash 跑）；跑完会落 02_transcript.json/.txt

# 3. cut list（你来读 02_transcript.txt → 写 03_cut_list.json）

# 3b. 自动剪静音
python3 "$SKILL/scripts/03b_carve_silences.py" "$VIDEO" --min-gap 15

# 4. 剪辑视频
python3 "$SKILL/scripts/04_edit_video.py" "$VIDEO"

# 5. SRT
python3 "$SKILL/scripts/05_make_srt.py" "$VIDEO"

# 6. 章节（你来读 _edited_transcript.txt → 写 06_chapters.json）
python3 "$SKILL/scripts/_make_edited_transcript.py" "$VIDEO"
python3 "$SKILL/scripts/06b_chapters_to_txt.py"     "$VIDEO"

# 7. 封面
python3 "$SKILL/scripts/07_make_covers.py" "$VIDEO"

# 8. 插封面到视频
python3 "$SKILL/scripts/08_insert_covers.py" "$VIDEO"

# 9. 发布包 starter（你来读 starter 里的 TODO，按 prompt 填掉）
python3 "$SKILL/scripts/09_make_publish_starter.py" "$VIDEO"
```

## 提示词在哪里

`prompts/cut_list_prompt.md`、`prompts/chapters_prompt.md`、
`prompts/publish_package_prompt.md`，调用方按需修改。
