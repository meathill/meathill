# ffmpeg 配方

把所有今天验证过有效的滤镜组合和编码参数集中在这里。

## 试制阶段

### 切样本

挑一段同时包含说话和静音的区间（30-60 秒），转成 WAV 方便对比：

```bash
TEST_DIR="/Users/meathill/Movies/直播/降噪测试"
mkdir -p "$TEST_DIR"

ffmpeg -y -hide_banner -loglevel error \
  -ss 3300 -t 50 -i "原片.mp4" \
  -vn -ac 2 -ar 48000 -c:a pcm_s16le "$TEST_DIR/0_原始.wav"
```

### 并行试 4-6 个方案

每个方案输出独立 WAV，最后批量量化对比。

```bash
TEST="$TEST_DIR"

# 方案 A: 通用 afftdn + 噪声追踪
ffmpeg -y -hide_banner -loglevel error -i "$TEST/0_原始.wav" \
  -af "afftdn=nr=40:nf=-30:tn=1" "$TEST/A_afftdn激进.wav"

# 方案 B: 非局部均值降噪
ffmpeg -y -hide_banner -loglevel error -i "$TEST/0_原始.wav" \
  -af "anlmdn=s=0.0001:p=0.005:r=0.01" "$TEST/B_anlmdn.wav"

# 方案 C: 多滤镜串联
ffmpeg -y -hide_banner -loglevel error -i "$TEST/0_原始.wav" \
  -af "highpass=f=80,afftdn=nr=30:tn=1,anlmdn=s=0.0001,agate=threshold=0.02:ratio=4:attack=10:release=200" \
  "$TEST/C_组合.wav"

# 方案 D: 仅噪声门
ffmpeg -y -hide_banner -loglevel error -i "$TEST/0_原始.wav" \
  -af "agate=threshold=0.04:ratio=10:attack=5:release=400:knee=2" \
  "$TEST/D_噪声门.wav"

# 方案 E: 极致 afftdn + 软门  ← 今天的获胜方案
ffmpeg -y -hide_banner -loglevel error -i "$TEST/0_原始.wav" \
  -af "highpass=f=80,afftdn=nr=80:nf=-30:tn=1,agate=threshold=0.05:ratio=4:attack=10:release=300:knee=4" \
  "$TEST/E_极致.wav"

# 方案 F: 收紧门限
ffmpeg -y -hide_banner -loglevel error -i "$TEST/0_原始.wav" \
  -af "agate=threshold=0.08:ratio=8:attack=5:release=400:knee=4" \
  "$TEST/F_硬门.wav"
```

### 批量量化对比

```bash
SILENCE_START=26  # 样本里纯静音段的起点（避开边缘）
SILENCE_DUR=12
SPEECH_START=0
SPEECH_DUR=15

for f in 0_原始 A_afftdn激进 B_anlmdn C_组合 D_噪声门 E_极致 F_硬门; do
  silence=$(ffmpeg -hide_banner -nostats -ss $SILENCE_START -t $SILENCE_DUR -i "$TEST/${f}.wav" \
    -af volumedetect -f null - 2>&1 | grep mean_volume | awk '{print $5}')
  speech=$(ffmpeg -hide_banner -nostats -ss $SPEECH_START -t $SPEECH_DUR -i "$TEST/${f}.wav" \
    -af volumedetect -f null - 2>&1 | grep mean_volume | awk '{print $5}')
  printf "  %-15s 说话=%-8s 静音=%-8s\n" "$f" "${speech}dB" "${silence}dB"
done
```

判断标准：

- **静音值越低越好**——意味着底噪被压下去了
- **说话值不能掉**——掉了说明降噪伤了人声
- **说话/静音差距越大越好**——意味着信噪比改善

把前 3 名转 MP3 给用户试听：

```bash
for f in 0_原始 E_极致 F_硬门; do
  ffmpeg -y -hide_banner -loglevel error -i "$TEST/${f}.wav" \
    -c:a libmp3lame -b:a 128k "$TEST/${f}.mp3"
done
```

然后给 `computer://` 链接让用户听完决定。

## 成片阶段

### 完整命令模板

写到 `_process.command`，让用户 Finder 双击触发（VideoToolbox 是 macOS 独有的硬件编码器）：

```bash
#!/bin/bash
set -u
cd "/Users/meathill/Movies/直播" || exit 1
mkdir -p 播客

INPUT="原片.mp4"
OUTPUT="播客/成片.mp4"

# 关键参数（按需改）
SEG1_START=622    # 片头开始（秒）
SEG1_END=4592     # 中间尴尬段开始（秒）
SEG2_START=4718   # 中间尴尬段结束（秒）
SEG2_END=4745     # 片尾结束（秒）

ffmpeg -y -hide_banner \
  -ss $SEG1_START -to $SEG1_END -i "$INPUT" \
  -ss $SEG2_START -to $SEG2_END -i "$INPUT" \
  -filter_complex "\
[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a];\
[a]highpass=f=80,\
   afftdn=nr=80:nf=-30:tn=1,\
   agate=threshold=0.05:ratio=4:attack=10:release=300:knee=4,\
   silenceremove=start_periods=0:stop_periods=-1:stop_duration=2.0:stop_threshold=-50dB:detection=peak,\
   loudnorm=I=-16:TP=-1.5:LRA=11[ao]" \
  -map "[v]" -map "[ao]" \
  -c:v h264_videotoolbox -b:v 3M -tag:v avc1 \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  -movflags +faststart \
  "$OUTPUT"
```

### 滤镜链解释

按顺序：

1. **`highpass=f=80`** ——砍 80 Hz 以下的次声/电源嗡。这一段对人声基本无影响，但能干掉低频垃圾。
2. **`afftdn=nr=80:nf=-30:tn=1`**——FFT 频域降噪，nr=80（最大 97）够狠，`tn=1` 让它动态追踪噪声。**对稳态宽频噪有效**（比如风扇）。
3. **`agate=threshold=0.05:ratio=4:attack=10:release=300:knee=4`**——软噪声门，0.05 ≈ -26 dB。说话时门开（让信号通过），停顿时门关（把残余底噪压住）。`knee=4` 让开关更平滑，避免"啪嗒"的人为感。
4. **`silenceremove=stop_duration=2.0:stop_threshold=-50dB`**——去 2 秒以上的长静音。注意阈值要在前面降噪之后能达到的水平上设置。
5. **`loudnorm=I=-16:TP=-1.5:LRA=11`**——EBU R128 响度标准化到 -16 LUFS，真峰值 -1.5 dB，动态范围 11 LU。**这是 Apple Podcasts 推荐值**，B 站/YouTube 也兼容。

### 参数微调指南

| 噪声情况 | 改这里 |
|---|---|
| 风扇声还在 | afftdn 加 nr=90，或后面再加 `anlmdn=s=0.0001` |
| 人声变模糊/失真 | afftdn 减 nr 到 50-60，关 `tn=1` |
| 噪声门"啪嗒"感明显 | knee 加到 6，release 加到 500 |
| 中间还有几秒沉默没去 | stop_threshold 改 -45 dB（更敏感）；或先用 `agate` 把底噪压到 -50 dB 以下 |
| 输出整体偏轻 | loudnorm I 改 -14（响度上一档） |
| 输出文件太大 | `-b:v 2M` 改成 2 Mbps；或用 libx264 软编 + crf 23 |

### VideoToolbox vs libx264

VideoToolbox 在 M 系列上**比软编快 10x+**（实测今天 80 分钟 1080p 五六分钟编完，速度 12.2x 实时）。

但 VideoToolbox 出的码率比 libx264 同质量略大（比特率效率低 20% 左右）。如果用户特别在意文件大小，再换 libx264：

```
-c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p
```

软编 80 分钟 1080p 在 4 核 ARM 上大概要 1-2 小时，所以**只在用户明确要求小文件时才用**。

## 浏览速度优化（可选）

加 `-movflags +faststart` 让 MP4 的 moov atom 移到文件开头，B 站/YouTube 上传后预览能立即播放。

## 输出验证

ffmpeg 跑完一定再用 ffprobe 量一遍，确认时长、码率符合预期：

```bash
ffprobe -v error -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_type,codec_name,width,height,sample_rate,channels \
  -of default=nw=1 "$OUTPUT"
```

预期：

- duration = (SEG1_END - SEG1_START) + (SEG2_END - SEG2_START) = 你切的两段总长（除非 silenceremove 触发）
- 视频 codec_name = h264, width=1920, height=1080
- 音频 codec_name = aac, sample_rate=44100, channels=2

时长不对 = 裁剪参数错了；分辨率掉了 = filter_complex 写错；音频参数不对 = encoder 配置错了。

## 用 silenceremove 的注意事项

`silenceremove` 在用户的录音里**经常不触发**，因为：

- 默认 `stop_threshold=-50dB` 比实际底噪（-30 dB）严格 20 dB
- `detection=peak` 看的是峰值，瞬态尖峰（键盘咔嗒）会让它判定为非静音

排查时先量一下输出时长是不是等于裁剪段加和。如果完全相等，silenceremove 一段都没去掉。

修法：

1. **前面先加 `agate` 把底噪压下去**，让噪声门后的"静音"真的安静（< -50 dB），silenceremove 自然就触发了
2. **改用 `detection=rms`**——看均值不看峰值，对瞬态尖峰不敏感
3. **放宽阈值**——`stop_threshold=-30dB`，但可能误伤说话时的弱辅音
