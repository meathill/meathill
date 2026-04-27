---
name: livestream-to-podcast
description: >
  把直播录像（或任意未经剪辑的长视频）剪成可直接上传的播客/视频版成片。触发条件：
  当用户提到"直播录像"、"直播回放"、"播客版"、"剪辑视频"、"上传 B 站/YouTube/小宇宙"、
  "去底噪"、"去静音"、"裁掉片头片尾"、"转成播客"，或上传一个 mp4 并希望对它做剪辑/降噪/响度处理时，
  应该使用本 skill。也适用于："Live Replay" / "OBS 录像"、"webinar 录像剪精华"、
  "去掉直播开场暖场"、"音频底噪太大"、"风扇声"、"长视频里有大段沉默"等场景。
  涵盖完整流程：需求澄清 → 音频诊断 → Whisper 转写定位裁剪点 → ffmpeg 管线试制（多方案 A/B）→
  全片硬件编码 → 输出上传材料（标题/标签/简介/粉丝动态/封面 prompt）。
---

# 直播录像 → 播客成片

把一段 60-120 分钟、含底噪和大量闲聊的原始直播录像，处理成可以直接上传到 B 站、YouTube、小宇宙、Apple Podcasts 的成品。

全程中文交互。脚本的最终运行环境是用户的 macOS（M 系列芯片，有 ffmpeg + whisper.cpp + Homebrew）。

## 沙箱与本机的分工

沙箱里能做：ffmpeg 滤镜分析、转码、生成 .command 脚本写到挂载目录。
本机才能做：

- 跑 whisper.cpp（沙箱网络拦了 Hugging Face，下不了模型）
- 用 h264_videotoolbox 硬件编码（比沙箱软编快 10 倍以上）
- 跑 Adobe Podcast Enhance 等浏览器/桌面应用

模式：**沙箱写 `.command` 脚本到用户的视频文件夹 → Finder 双击 → Terminal 自动跑**。
不要让用户复制粘贴长命令到终端，他们就是为了不想干这个才找你。

## 主流程

按顺序走六步。每一步都有可能让用户做选择，**不要替用户决定**关键裁剪点和音色取舍。

### 1. 需求澄清（必做）

用 `AskUserQuestion` 工具一次性问 3-4 个问题，覆盖：

- **目标格式**：纯音频（MP3/M4A）还是视频播客（MP4）
- **剪辑动作**：裁片头/裁片尾/去长静音/中间剪片段/响度标准化/降噪（多选）
- **噪声类型（如选了降噪）**：低频嗡嗡 / 稳态嘶嘶 / 环境杂音 / 不确定
- **片头片尾时间点**：让用户给秒数；如果他们说"用转写定位"就走第 3 步

不要凭"看起来很简单"省略这一步。直播录像看似就是切个头尾，实际可能藏着「中间 2 分钟尴尬段」「最后一段嘉宾连不上线」「想保留某个高光片段」之类需求。

### 2. 音频诊断

读 `references/audio-diagnostics.md`。
取至少 3 个说话段 + 3 个静音段做 `volumedetect`，对比 mean/max。再做频段功率分布（低/人声/高），定位噪声主频。

诊断要回答的问题：

- 底噪是稳态还是动态（AGC 还是真噪声）？看长静音里逐秒扫描会不会爬升
- 噪声主要在哪个频段？决定用 highpass + afftdn 还是只能上 AI 降噪
- 静音段里有没有 0 dB 尖峰？决定 silenceremove 用 peak 还是 rms 检测

**陷阱：用户的口头诊断常常错。**今天碰到过的真实案例：用户说"低频嗡嗡声"，频段分析后发现噪声集中在 200-4000 Hz（人声范围），后来才确认是笔记本风扇当主麦的结果。**先测，再选滤镜。**

### 3. Whisper 转写定位裁剪点

读 `references/whisper-setup.md`。
通过 `.command` 脚本在用户 Mac 跑 whisper.cpp。**关键参数 `-mc 0 -sns -pp`，缺一不可**，否则 whisper 会陷入"中文字幕：李宗盛"这类幻觉循环（实测过两次教训）。

模型用 `ggml-large-v3-turbo.bin`（约 1.6 GB），M 系列芯片上 80 分钟音频 5-10 分钟出 SRT。

拿到 SRT 后，从沙箱里跑一段 Python，扫出：
- 第一个出现"那我们开始吧"/"大家好"/"欢迎"等开场词的时间 → 片头候选
- 最后出现"拜拜"/"感谢大家"/"今天就到这里"的时间 → 片尾候选
- 段落间间隔 > 30 秒的位置 → 长沉默/尴尬段候选

把候选位置 + 上下文文本展示给用户，让他们选裁剪点。

### 4. 管线试制（小样 A/B）

**不要直接对全片应用滤镜**——降噪参数错了，1.5 GB 的成片也得重做。

从原始视频里切一段 30-60 秒的样本（最好同时包含说话和静音），并行试 4-6 个滤镜组合，用 `volumedetect` 量化对比说话段 vs 静音段的差距。

把 3 个最好的方案转成 MP3，给用户 `computer://` 链接试听，让用户选。

读 `references/ffmpeg-recipes.md` 里的"试制阶段"章节。

### 5. 全片处理

读 `references/ffmpeg-recipes.md` 里的"成片阶段"章节。

写 `_process.command` 到 `/Users/<user>/Movies/<视频文件夹>/`，用 Finder 双击触发。

ffmpeg 命令的核心结构：

```
-ss <开头> -to <裁剪点1> -i 原片 -ss <裁剪点2> -to <结尾> -i 原片
-filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a];[a]<音频滤镜链>[ao]"
-map "[v]" -map "[ao]"
-c:v h264_videotoolbox -b:v 3M -tag:v avc1
-c:a aac -b:a 128k -ar 44100 -ac 2
-movflags +faststart
```

VideoToolbox 给出的 12x 实时速度，80 分钟原片 5-6 分钟编完。

### 6. 上传材料（如果用户要求）

读 `references/upload-package.md`。
基于 SRT 里的实际内容，生成：

- 标题（3 个备选，覆盖叙事/干货/互动三种调性）
- 标签（10 个以内，关键词在前）
- 简介（带时间戳章节）
- 粉丝动态（A/B/C 三种语气）
- 封面 AI prompt（极客风/人物风两个版本，明确告诉 AI **不要画文字**）

**时间戳要换算**：SRT 里的时间是原片时间，要减去裁掉的片头长度。比如裁了 622 秒（10:22），原片 22:54 在成片里就是 22:54 - 10:22 = 12:32。

## 工程纪律

- **过程文件最后清掉**。WAV / SRT / 试听 MP3 / `.command` / `whisper_help.txt` 这些，最终只留原片 + 成片。沙箱默认没有删除权限，调 `mcp__cowork__allow_cowork_file_delete` 拿权限再 `rm`。
- **现在就承认局限**。afftdn 治不了瞬态噪声（键盘咔嗒、转椅声），silenceremove 在底噪 -30 dB 时不会触发 -50 dB 阈值，VideoToolbox 出的码率比 libx264 同 CRF 略大。这些都是事实，遇到就直说，不要硬编。
- **超过 -16 LUFS 之后再担心底噪。**loudnorm 会把底噪一起拉高，所以方案对比要在加 loudnorm 之前的版本上做听感判断。
- **每次 ffmpeg 跑完都再 `ffprobe` 量一下**输出文件的时长和码率，确认裁剪点和编码器都按预期工作了。

## 经常踩的坑

| 坑 | 现象 | 解决 |
|---|---|---|
| Whisper 幻觉 | 输出全是"中文字幕 :Cinco"或"由 XX 字幕组制作" | 加 `-mc 0 -sns`，必要时先降噪再转写 |
| sandbox 下不了 HF 模型 | 沙箱跑 faster-whisper 报 ProxyError 403 | 不在沙箱里转写，写 `.command` 让用户在 Mac 跑 |
| Terminal tier=click | computer-use 无法在 Terminal 里输入命令 | 用 `.command` 脚本 + Finder 双击触发 |
| present_files 报错 | 中文路径文件提示 not accessible | 给 `computer://` 直链替代 |
| silenceremove 不生效 | 输出时长和裁剪段加和一致 | 阈值高于实际底噪；用 rms 检测，或先 agate 把噪声压下去 |
| 长沉默段噪声反而更"响" | 用户主诉：不说话时底噪很响 | 这是听觉掩蔽（masking）现象，不是 AGC。底噪本来就在，说话时被人声盖住 |
| 0 dB 尖峰穿透 | 静音段 max 一直 0 dB | 是真噪声事件（键盘/转椅），不是 fan，afftdn 治不了，得用 declick 或 AI 降噪 |

## 何时建议用户用 Adobe Podcast Enhance

如果上面的滤镜组合做完用户还是不满意（特别是录音是用笔记本麦克风录的、底噪在人声频段），告诉用户：

> [Adobe Podcast Enhance](https://podcast.adobe.com/enhance) 是最强的一档，AI 直接把人声从风扇里抽出来，比上面这些 ffmpeg 滤镜效果都好（且免费）。把成片音频抽出来传上去，下载回来再 mux 回视频。

不要嘴硬装 ffmpeg 万能。当 ffmpeg 力有不逮时坦诚说出，对用户更好。
