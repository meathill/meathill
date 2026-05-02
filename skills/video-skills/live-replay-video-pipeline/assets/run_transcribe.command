#!/bin/bash
# 双击这个文件就行（或 bash 这个文件）。
# 用本地 whisper-cpp 把 out/01_audio.wav 转写成 whisper.cpp 原生 JSON。
# 完成后会自动转换成 pipeline 要的 out/02_transcript.json + out/02_transcript.txt。
#
# 这个脚本要和视频文件放同一目录。第一次用前先跑：
#   python3 <skill>/scripts/01_extract_audio.py <video>
# 让 out/01_audio.wav 存在。
set -e
cd "$(dirname "$0")"
OUT="out"
AUDIO="$OUT/01_audio.wav"
WCPP_JSON_PREFIX="$OUT/_whispercpp"   # whisper.cpp 会自动加 .json 后缀

if [ ! -f "$AUDIO" ]; then
  echo "[err] 没找到 $AUDIO。先跑 01_extract_audio.py 抽音频。"
  exit 2
fi

# --- 1. 找 whisper-cpp 可执行文件 ---
BIN=""
for cand in whisper-cli whisper-cpp main; do
  if command -v "$cand" >/dev/null 2>&1; then BIN="$cand"; break; fi
done
if [ -z "$BIN" ]; then
  echo "[err] 没找到 whisper-cli / whisper-cpp / main。"
  echo "      brew install whisper-cpp，或手动设置 BIN=/path/to/whisper-cli"
  exit 2
fi
echo "[info] using BIN=$BIN ($(command -v "$BIN"))"

# --- 2. 找模型 ---
MODEL=""
if [ -n "$WHISPER_MODEL" ] && [ -f "$WHISPER_MODEL" ]; then
  MODEL="$WHISPER_MODEL"
fi
if [ -z "$MODEL" ]; then
  for cand in \
    "$HOME/whisper.cpp/models/ggml-large-v3.bin" \
    "$HOME/whisper.cpp/models/ggml-medium.bin" \
    "$HOME/whisper.cpp/models/ggml-small.bin" \
    "$HOME/whisper.cpp/models/ggml-base.bin" \
    "$HOME/whisper.cpp/models/ggml-tiny.bin" \
    "$(brew --prefix whisper-cpp 2>/dev/null)/share/whisper-cpp/models/ggml-base.en.bin" \
    "/opt/homebrew/share/whisper-cpp/models/ggml-base.en.bin" \
    "$HOME/Library/Application Support/MacWhisper/models/ggml-large-v3.bin" \
    "$HOME/Library/Application Support/com.chidiwilliams.macwhisper/models/ggml-large-v3.bin" \
    "$HOME/.cache/whisper.cpp/ggml-base.bin" ; do
    if [ -f "$cand" ]; then MODEL="$cand"; break; fi
  done
fi
if [ -z "$MODEL" ]; then
  echo "[info] 在 ~ 下搜 ggml-*.bin (深度 5)..."
  MODEL=$(find "$HOME" -maxdepth 5 -name "ggml-*.bin" -size +10M 2>/dev/null | head -1)
fi
if [ -z "$MODEL" ]; then
  echo "[err] 没找到 ggml-*.bin 模型。请用："
  echo "  WHISPER_MODEL=/path/to/ggml-xxx.bin bash $0"
  exit 2
fi
echo "[info] using MODEL=$MODEL"

# --- 3. 跑转写 ---
echo "[info] 60 分钟音频 base 模型大概 5-15 分钟，medium/large 更慢，耐心点。"
echo "[run] $BIN -m \"$MODEL\" -f \"$AUDIO\" -l zh -oj -of \"$WCPP_JSON_PREFIX\" -pp"
"$BIN" -m "$MODEL" -f "$AUDIO" -l zh -oj -of "$WCPP_JSON_PREFIX" -pp

if [ ! -f "${WCPP_JSON_PREFIX}.json" ]; then
  echo "[err] whisper.cpp 没生成 ${WCPP_JSON_PREFIX}.json"
  exit 2
fi
echo "[ok] whisper.cpp 已生成 ${WCPP_JSON_PREFIX}.json"

# --- 4. 转成 pipeline 标准格式 ---
# 找 02b_adapt_whispercpp.py：先在脚本同目录找 scripts/，再尝试常见 skill 路径
ADAPT=""
for d in "scripts/02b_adapt_whispercpp.py" \
         "../live-replay-video-pipeline/scripts/02b_adapt_whispercpp.py" \
         "$HOME/Documents/GitHub/meathill/skills/video-skills/live-replay-video-pipeline/scripts/02b_adapt_whispercpp.py" ; do
  if [ -f "$d" ]; then ADAPT="$d"; break; fi
done
if [ -z "$ADAPT" ]; then
  echo "[warn] 没找到 02b_adapt_whispercpp.py。"
  echo "       请手动跑：python3 <skill>/scripts/02b_adapt_whispercpp.py \\"
  echo "         \"${WCPP_JSON_PREFIX}.json\" \"$OUT/02_transcript.json\" \"$OUT/02_transcript.txt\""
  exit 0
fi

python3 "$ADAPT" "${WCPP_JSON_PREFIX}.json" "$OUT/02_transcript.json" "$OUT/02_transcript.txt"
echo "[ok] 全部完成。可以回到 LLM 让它继续后续步骤。"
