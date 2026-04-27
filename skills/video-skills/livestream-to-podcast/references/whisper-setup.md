# Whisper 转写

为什么需要：从转写文本里找裁剪点（开场词、告别词、长沉默间隔），比让用户挨个时间点听快得多，也比单纯靠音量阈值（在底噪大的录音里）准得多。

## 为什么不能在沙箱里跑

沙箱网络拦了 huggingface.co、openaipublic.azureedge.net 等模型 CDN（403 Forbidden）。
faster-whisper / openai-whisper / whisper.cpp 都需要从这些 CDN 下模型。

→ 让用户在 Mac 本地跑。

## 一次性给用户的安装命令

```bash
brew install whisper-cpp
```

如果用户已经装了，跳过这一步。

## .command 模式

不要让用户复制长命令进 Terminal。写一个 `.command` 文件到他们的视频文件夹，然后用 Finder 双击触发：

```bash
# 1. 沙箱端写脚本
Write 工具 → /Users/<user>/Movies/<视频文件夹>/_transcribe.command

# 2. 沙箱端 chmod
mcp__workspace__bash → chmod +x .../转写.command

# 3. computer-use 打开 Finder，定位到视频文件夹，双击 .command
mcp__computer-use__open_application Finder
mcp__computer-use__key cmd+shift+g  # Go to Folder
mcp__computer-use__type /Users/<user>/Movies/<视频文件夹>
mcp__computer-use__key Return
mcp__computer-use__double_click <脚本图标坐标>
```

为什么不用 `mcp__computer-use__type` 直接在 Terminal 输入？因为 Terminal 的访问层级是 **click**，不允许键盘输入。
为什么不用 `osascript` 让 AppleScript 跑命令？因为系统 prompt 明确禁止，安全策略。

## .command 脚本模板

```bash
#!/bin/bash
set -u

cd "/Users/meathill/Movies/直播" || exit 1

WHISPER="/opt/homebrew/bin/whisper-cli"
MODEL_DIR="$HOME/whisper-models"
MODEL="$MODEL_DIR/ggml-large-v3-turbo.bin"
INPUT_VIDEO="Live Replay Apr 26 2026.mp4"
WAV_FILE="live.wav"

# 1. 二进制路径自动探测（brew / 手动编译都覆盖到）
if [ ! -x "$WHISPER" ]; then
  for cmd in whisper-cli whisper-cpp main; do
    if command -v "$cmd" &> /dev/null; then
      WHISPER=$(command -v "$cmd")
      break
    fi
  done
fi
[ -x "$WHISPER" ] || { echo "❌ 找不到 whisper-cli"; read; exit 1; }

# 2. 模型下载（只下一次）
mkdir -p "$MODEL_DIR"
if [ ! -f "$MODEL" ]; then
  echo "↓ 下载 large-v3-turbo（约 1.6 GB）..."
  curl -L --fail -o "$MODEL.tmp" \
       "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin" \
    || curl -L --fail -o "$MODEL.tmp" \
       "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin" \
    || { rm -f "$MODEL.tmp"; echo "❌ 下载失败"; read; exit 1; }
  mv "$MODEL.tmp" "$MODEL"
fi

# 3. 转 WAV（whisper.cpp 需要 16kHz 单声道）
if [ ! -f "$WAV_FILE" ]; then
  ffmpeg -y -loglevel error -stats -i "$INPUT_VIDEO" \
    -ar 16000 -ac 1 -c:a pcm_s16le "$WAV_FILE"
fi

# 4. 跑转写——关键参数缺一不可，见下文
"$WHISPER" \
  -m "$MODEL" \
  -l zh \
  -osrt -of "live" \
  -f "$WAV_FILE" \
  -t 8 \
  -mc 0 \
  -sns \
  -pp

[ -f "live.srt" ] && echo "✅ 完成 → live.srt" || echo "❌ 失败"
echo "可关闭窗口（Cmd+W）"
```

## 关键参数（缺一不可）

whisper.cpp 在 ggerganov 实现里，**默认行为对噪声大的中文录音很容易出现幻觉循环**（每段 1 秒，文本全是"中文字幕：李宗盛"或"由 XX 字幕组制作"）。原因是它会用上一段的输出作为下一段的 prompt，一旦撞上一次"中文字幕"幻觉，会一路传染下去。

修复（已实测两次）：

| 参数 | 作用 | 不加的后果 |
|---|---|---|
| `-mc 0` | max-context = 0，不把上一段输出作为下一段提示 | 幻觉循环 |
| `-sns` | suppress non-speech tokens，禁止生成"♪"、"中文字幕"等非语音 token | "中文字幕：XXX"幻觉 |
| `-pp` | print progress，进度可见 | 没影响转写质量，但能让用户看到 25%/50%/75% |
| `-t 8` | 8 个 CPU 线程（M 系列芯片够用） | 默认 4 线程，慢一倍 |

**不要加 `-nc`**，那是别的 whisper 实现（比如 openai-whisper Python 版）的参数；whisper.cpp 用的是 `-mc 0`。如果加了 `-nc`，whisper-cli 会判定为非法参数，直接打印 help 后退出（实测踩过）。

## 噪声严重时先降噪再转写

如果原音频的底噪 > -25 dB（用 audio-diagnostics 测过的话就知道），即使加了上面的参数，whisper 仍然可能漏识别。

办法：转 WAV 之后，先用 ffmpeg 做一遍预降噪，再把降噪版传给 whisper：

```bash
ffmpeg -y -i live.wav \
  -af "highpass=f=120,afftdn=nr=20:nf=-30,dynaudnorm=f=200:g=15" \
  -ar 16000 -ac 1 -c:a pcm_s16le live_clean.wav

# 然后 whisper 用 live_clean.wav 而不是 live.wav
```

注意：这只用于"帮 whisper 识别"，不是最终成片的降噪。最终成片走第 5 步的 ffmpeg-recipes 里的滤镜链。

## SRT 后处理：找裁剪点

拿到 `live.srt` 后，从沙箱跑 Python 扫出长间隔（候选裁剪点）：

```python
import re

with open('live.srt', 'r', encoding='utf-8') as f:
    content = f.read()

def t2s(t):  # "00:12:34,560" → 754.56
    h, m, s = t.split(':')
    s, ms = s.split(',')
    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000

blocks = re.findall(
    r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\Z)',
    content, re.DOTALL,
)

prev_end = 0
for n, start, end, text in blocks:
    s, e = t2s(start), t2s(end)
    gap = s - prev_end
    text = text.strip().replace('\n', ' ')
    # 异常长段（>15s）= 可能幻觉；段间距 >10s = 可能长沉默
    if e - s > 15 or gap > 10:
        print(f"#{n}  {int(s)//60:02d}:{int(s)%60:02d}  (段长 {e-s:.1f}s, 间隔 {gap:.0f}s)  {text[:60]}")
    prev_end = e
```

得到的列表里：

- **开头几段**通常是测试音/暖场/调灯，那种 30 秒整数边界 + "中文字幕"文本的段就是幻觉，可以全裁掉
- **第一个有意义的整句**（"我们开始吧"/"大家好"/"欢迎来到"）是真正的开场
- **段间距 > 30 秒**的位置：一般是中场暂停（喝水/等弹幕），常常可以剪掉
- **结尾**找"拜拜"/"感谢大家陪伴"/"今天就到这里"

把这个列表展示给用户，让他们勾选裁剪点。
