---
name: live-replay-video-pipeline
description: >
  把直播录像或长视频回放处理成可发布的视频包：转写原始音频、基于 transcription
  规划剪辑、剪掉冗余和长停顿、生成 SRT 字幕、章节、章节封面、最终视频和发布文案。
  当用户提供 .mp4/.mov/.mkv 直播录像、OBS 录屏、webinar 或课程回放，并要求剪辑、
  转写、出字幕、出章节、做封面/章节卡、准备 B 站或 YouTube 发布素材时触发。
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

中间产物（01_audio.wav、_edited_transcript.txt、_insert_work/、_edit_work/ 等）
跑完可删，但**不要自动删**——用 `scripts/99_cleanup.py`（手动，建议上传后再跑，
见第 10 步）。

## 跨步骤原则：第一人称视角

LLM 创意步骤（Step 3 / 6 / 9）写出来的文字——cut list reason、章节标题、标题候选、
描述、动态文案、粉丝动态、封面 prompt 副标题——**都是作者自己在跟观众沟通的话**，
不是 LLM 代替作者描述作者。所以：

- 不要写 "程序员的自我介绍" / "20 年程序员的 Codex 起手式" / "a 20-yr dev uses Codex"
  这种把作者当第三人称对象的句式。
- 改成 "自我介绍" / "我的 Codex 起手式" / "I'm using Codex"。
- 引用作者的资历时要么"我"包裹（"我做了 20 年开发"），要么直接省略。

下游 prompt（`prompts/chapters_prompt.md`、`prompts/publish_package_prompt.md`）里
也复述了这条规则；这里是 cross-cutting reminder，章节标题 + 整个发布包都按这条来。

## 主流程（9 步）

### 1. 抽音频（01）

```
python3 scripts/01_extract_audio.py <video>
```
ffmpeg 出 16kHz/mono PCM。80 分钟视频 ~20 秒搞定。

### 2. 转写（A：API 优先；B：本地 whisper-cpp 兜底）

两条路结果都落成标准 `02_transcript.json`（`segments:[{start,end,text}]`）+
`02_transcript.txt`，下游一致。

**A. API 转写（推荐，尤其中英混说 + 技术术语）** — `scripts/02d_transcribe_api.py`

whisper（本地 medium 尤甚）对中英 code-switching + 技术词很弱；而本 pipeline **依赖
逐句时间戳**。已查证：OpenAI `gpt-4o-transcribe` 不返回时间戳（仅 `whisper-1` 返回，
25MB/文件）；`MiMo-V2.5-ASR` 文本最准但**不返回时间戳**。所以：

- 默认 `--engine mimo`：用 MiMo（中英混说 + 技术内容最准）。它无时间戳，脚本用 ffmpeg
  `silencedetect` 在停顿处把音频切 ~100s 块（块边界=真实时间戳），并发送 MiMo 取文本，
  再按标点分句、按字数分配块内时间。MiMo 单次能吃 ≥300s。
- `--engine whisper1`：`whisper-1`（verbose_json 段级时间戳）+ GPT-4o 按术语词表逐句纠错。
- `--probe-mimo`：对 15s 切片打印原始响应，确认 token / 时间戳能力。
- 凭据放 `~/.config/live-replay/secrets.env`（`MIMO_API_KEY` / `MIMO_BASE_URL` /
  `OPENAI_API_KEY`），脚本用 curl `-K` stdin 传，**不进 argv / 日志**。

**A+. 清口癖（可选）** — `scripts/02e_clean_filler.py`

用 MiMo 对话模型（默认 `mimo-v2.5`）把转写文本里的口癖（呃/嗯/啊/哈、重复、口吃）清掉，
**只改 text、保留时间戳**，原文备份到 `02_transcript.raw.json`。SRT 字幕和章节/发布文案
因此读着干净，**视频原声不动**（适合"口癖只清字幕、不动视频"的需求）。

**B. 本地 whisper-cpp（离线兜底）** — `assets/run_transcribe.command` + `02b`

无网络 / 不想花 API 时：把 `assets/run_transcribe.command` 复制到视频目录双击跑（自动找
`whisper-cli`/`whisper-cpp`/`main` + `ggml-*.bin`），跑完用 `scripts/02b_adapt_whispercpp.py`
转成标准格式。中英混说质量最弱。

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

**局部变速 / 8x 时间流逝**：cut list 段可带可选字段 `"speed"`（float，默认 1.0）。一旦有
任何段 `speed != 1.0`，04 自动切到**变速路径**：所有段（含 1x）统一重编码到同一 profile
（libx264 30fps + `-video_track_timescale 90000`）再 `concat -c copy`；`speed>1` 的段
`setpts=PTS/N` 提速并**静音**（anullsrc 占位）。无任何 speed 字段时行为与旧版逐字节一致。
05 / `_make_edited_transcript` 的投影同样 speed-aware（`(t-s)/speed`），落在 speed>1 段内的
字幕整条丢弃（时间流逝段无可懂语音），`_edited_transcript.txt` 里折叠成一行 ⏩ 标记。共享
`scripts/_cuts.py`（`load_segments` / `build_cum` / `any_speed`）保证三处算法不漂移。
用法：给"等待 / 空档"段加 `"speed": 8.0`。

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
**章节标题硬限制 ≤16 字**（汉字/英文/标点都各算 1 字）——B 站章节解析器的硬约束，
超过会被截断或不识别。

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
把 `covers/` 里的 PNG 各做成 3 秒静音 mp4（**探测 `04_edited.mp4` 的 fps + timescale
并据此渲染 slate**，让 30fps 变速成片 / 60fps 普通成片都能干净 concat），
切 `04_edited.mp4` 成 chapter 片段，交叉 concat 出 `08_final.mp4`。
注意：chapter 用 `-c copy` 切有关键帧漂移，多章累计可达几秒，`08_final` 章节时间是**近似**；
要帧准确就上传 `04_edited.mp4` + 用 `06_chapters.txt` 当章节元数据。
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
- 五、社交动态文案（视频发布**后**手动转发：独立动态 / Twitter / 公众号）
- 六、**B 站粉丝动态**（≤233 字，投稿表单里独立字段，随视频自动推到粉丝 feed）
- 七、上传前 checklist

### 10. 清理中间产物（手动，**上传后**）

```
python3 scripts/99_cleanup.py <video>                            # dry-run，只列出将删什么
python3 scripts/99_cleanup.py <video> --yes                      # safe：删 scratch，留所有成片+转写
python3 scripts/99_cleanup.py <video> --minimal --keep 08 --yes  # 上传 08_final 后：只留它+发布包
```
**不被流程自动调用**——必须手动跑，避免上传前误删成片。`--keep {both,04,08}` 指定保留哪一版
（删另一版的视频/字幕/章节）；`--minimal` 连转写 / cut list / covers(章节卡) 一起删，只剩上传
需要的。永不删除：被保留版本的视频/字幕/章节、`09_publish_package.md`、`cover*.png`(主封面)。
safe 档（不加 --minimal）只删 scratch，保留转写 + cut list（可复跑 05/06/...）。

## 一次性跑通的命令清单

```bash
SKILL=/path/to/video-skills/live-replay-video-pipeline
VIDEO=/path/to/your/<video>.mp4

# 1. 抽音频
python3 "$SKILL/scripts/01_extract_audio.py" "$VIDEO"

# 2. 转写（API 优先；凭据放 ~/.config/live-replay/secrets.env）
python3 "$SKILL/scripts/02d_transcribe_api.py" "$VIDEO"          # 默认 MiMo（中英混说最准）
python3 "$SKILL/scripts/02e_clean_filler.py"   "$VIDEO"          # 可选：清字幕口癖（不动视频）
# 离线兜底：cp assets/run_transcribe.command 到视频目录双击 → 再跑 02b

# 3. cut list（你来读 02_transcript.txt → 写 03_cut_list.json；等待段可加 "speed":8.0）

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

# 10. 清理中间产物（手动，**上传之后**再跑）
python3 "$SKILL/scripts/99_cleanup.py" "$VIDEO" --minimal --yes
```

## 提示词在哪里

`prompts/cut_list_prompt.md`、`prompts/chapters_prompt.md`、
`prompts/publish_package_prompt.md`，调用方按需修改。
