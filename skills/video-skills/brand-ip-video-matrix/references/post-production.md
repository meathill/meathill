# 后期装配

## 一、流水线

```
分段素材 → 归一化(768×1368 / 24fps / 精确时长) → concat → 混音(loudnorm)
        → 叠字幕 PNG → H.264 编码 → 1080×1920 交付版
```

母版留 768×1368，交付版用 lanczos 升到 1080×1920。

### 用 assemble.py

`scripts/assemble.py` 吃一份 JSON 规格，跑完整条流水线：

```json
{
  "out": "videos/matrix/skin-1080.mp4",
  "segments": [
    {"src": "build/segA.mp4", "len": 10.0},
    {"src": "videos/sp/sp-skin-10s.mp4", "len": 10.125},
    {"src": "videos/sp/sp-skin-6s.mp4", "len": 4.875},
    {"src": "build/segC.mp4", "len": 5.0},
    {"src": "build/segD.mp4", "len": 3.0}
  ],
  "music": {"src": ".tmp/beds/bed-cute2.wav", "gain": 0.30, "offset": 0.0},
  "water": {"src": "build/water.wav", "gain": 0.34, "offset": 0.0},
  "voice": [
    {"src": "audio/voices/final-c4b/vo-A.mp3",  "start": 1.15},
    {"src": "audio/voices/sp/skin/vo-B1.mp3",  "start": 10.75},
    {"src": "audio/voices/sp/skin/vo-B2.mp3",  "start": 19.20, "atempo": 1.0}
  ],
  "subtitles": [
    {"src": "build/sub0.png", "start": 1.10, "end": 4.18},
    {"src": "build/sub1.png", "start": 10.70, "end": 14.69}
  ],
  "target_lufs": -14, "true_peak": -1.5
}
```

```bash
python3 scripts/assemble.py spec.json
```

`offset` 用在短版：短版的 B 段从 0 开始，完整版从 10 开始，
短版规格里所有 `start` 减 10，音乐/环境音的 `offset` 填 10，ffmpeg 用 `atrim` 裁到对应区间。

### 混音滤镜链

```
[0]volume=0.30[m];[1]volume=0.34[wa];
[2]adelay=1150|1150[v0];[3]adelay=10750|10750[v1];
[m][wa][v0][v1]amix=inputs=4:duration=longest:normalize=0[mix];
[mix]aresample=48000,loudnorm=I=-14:TP=-1.5:LRA=11[out]
```

三个细节：

- `adelay` 之间要有 `;`，漏了 ffmpeg 直接报 filterchain 解析失败
- `amix` 的 `normalize=0` 关掉自动归一化，否则旁白会被压掉
- `loudnorm` 前面必须有 `aresample=48000`（见下方坑位）

### 字幕叠加滤镜链

```
[2:v]format=rgba,fade=t=in:st=1.10:d=0.25:alpha=1,fade=t=out:st=3.93:d=0.25:alpha=1[s0];
[0:v][s0]overlay=0:0:format=auto:enable='between(t,1.10,4.18)'[v1];
[v1]format=yuv420p[v420]
```

字幕 PNG 的输入序号从 2 起（0 = 视频，1 = 音频）。

### 编码参数

```bash
-c:v libx264 -profile:v high -level 4.0 -pix_fmt yuv420p -crf 18 -preset veryfast \
-c:a aac -profile:a aac_low -b:a 192k -ar 48000 -ac 2 -movflags +faststart
```

---

## 二、坑位清单

这些都真实踩过，逐条对应现象：

### overlay + `-loop 1` 图片输入 = ffmpeg 永不退出

图片输入是无限流。输出侧必须加 `-t <总时长> -shortest`。

### loudnorm 让 AAC 被封装成 96 kHz → 播放器静音

`loudnorm` 内部升采样到 192 kHz，ffmpeg 遇到高于 96 kHz 的 AAC 采样率会按 96 kHz 封装，
部分播放器直接静音。滤镜链末加 `aresample=48000`，编码参数加 `-ar 48000 -ac 2`。

### 字幕 PNG 把像素格式顶成 yuv444p

`format=rgba` 的图片进 overlay 会让输出变 yuv444p，部分平台不认。
filter 链末加 `format=yuv420p`，并显式 `-profile:v high -level 4.0 -pix_fmt yuv420p`。

### 字幕 PNG 的输入序号偏移

规格里视频是 0、音频是 1，字幕从 2 开始。写成 3 会报 `Invalid file index`。

### 分段素材文件名与 slot 名不一致

`seg_src()` 把 "b1"/"b2" 映射到 "10s"/"6s" 文件名时容易漏，ffmpeg 报
`Error opening input file`。

### A 段 / C 段旁白是所有卖点共用的固定台词

只有 B1/B2 因卖点而异。找旁白文件时，A 和 C 一律去共用目录取，
按卖点目录去找会报 `No such file or directory`。

### Python 三引号字符串后面带尾逗号

```python
SPEC = ("...text...",)   # 这是单元素元组，不是字符串
```

`len()` 返回 1，字符串判断全部失灵。规格文件里所有三引号字符串后**不要带尾逗号**。

### `__pycache__` 同秒写入读到旧 pyc

校验脚本一律用 `python3 -B`；`rm -rf __pycache__` 会被安全策略拦截。

---

## 三、质检

`scripts/qc_video.sh` 跑一条：

```bash
bash scripts/qc_video.sh videos/matrix/skin-1080.mp4
```

检查编码、分辨率、时长、音轨参数、响度与真峰值。

字幕命中要抽帧人工确认（自动化容易漏）：

```bash
ffmpeg -y -loglevel error -ss 12.0 -i film.mp4 -frames:v 1 -vf scale=405:720 f.jpg
```

在字幕窗内抽一帧（有字）、窗外抽一帧（无字），两帧拼一起看。

角色质检用 `references/video-generation.md` 里的抽帧方法。

---

## 四、评审包

产出一份 Markdown 评审文档 + 一个 zip：

| zip 内 | 内容 |
|---|---|
| `<key>-1080.mp4` ×N | 完整版 |
| `<key>-sp15-1080.mp4` ×N | 卖点短版 |
| `<brand>-matrix.md` | 评审文档 |
| `<brand>-matrix-overview.jpg` | N×M 关键帧总览图 |

评审文档要含：逐条脚本表（段落 / 时间 / 旁白 / 字幕）、官网口径出处、实测规格表、
**给评审者的具体问题**、**已知限制如实写**。

"已知限制"这一节最容易被漏掉，但它决定了评审结论能不能落地。必须写清：
画面实际分辨率与是否上采样、哪些素材受额度限制、哪些镜头没达到预期、哪些表述是模型生成的而非官网原文。
