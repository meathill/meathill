#!/usr/bin/env bash
# 成片质检：编码 / 分辨率 / 时长 / 音轨 / 响度
# 用法: bash qc_video.sh <file.mp4> [更多文件...]
set -e

for f in "$@"; do
  echo "=== $f"
  ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,level \
    -of default=nw=1 "$f"
  ffprobe -v error -select_streams a:0 \
    -show_entries stream=codec_name,profile,sample_rate,channels,bit_rate \
    -of default=nw=1 "$f"
  ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$f"
  ffmpeg -hide_banner -nostats -i "$f" -af ebur128=peak=true -f null - 2>&1 \
    | grep -E "^\s+(I|LRA|Peak):" | tail -3
  echo
done
