# 音频诊断

把"用户说底噪很大"翻译成"在哪个频段、什么幅度、稳态还是动态"。

## 核心思路

**先量再调。**用户的口头诊断常常错。今天遇到的真实例子：用户说"低频嗡嗡"，结果频段分析后噪声功率最大的是 200-4000 Hz（人声频段），最后定位是笔记本风扇当主麦。

诊断三件套：

1. **说话 vs 静音对比**——确认底噪绝对值和动态范围
2. **频段分布**——决定用 highpass / 普通 FFT 降噪 / AI 降噪
3. **逐秒扫描**——区分稳态噪声 / 瞬态尖峰 / AGC 爬升

## 命令模板

### 说话段 vs 静音段

挑 3 个说话段（确认是连续说话）+ 3 个静音段（间隔 ≥ 10 秒）：

```bash
for window in "说话_1:1200:15" "说话_2:2040:15" "静音_1:1514:16" "静音_2:3323:17"; do
  label=$(echo $window | cut -d: -f1)
  start=$(echo $window | cut -d: -f2)
  dur=$(echo $window | cut -d: -f3)
  echo "【$label】 start=${start}s, dur=${dur}s"
  ffmpeg -hide_banner -nostats -ss $start -t $dur -i "原片.mp4" \
    -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
done
```

健康基线（家用录音）：

| 指标 | 健康 | 这次 | 含义 |
|---|---|---|---|
| 说话 mean | -16 to -20 dB | -16 dB | OK |
| 静音 mean | -50 dB 以下 | -32 dB | 底噪偏大 |
| 说话 max | -3 to -1 dB | 0 dB | 削顶（增益太大） |
| 静音 max | -40 dB 以下 | 0 dB | 有瞬态事件 |

### 频段分布

把音频切成低频 / 人声 / 高频三段，分别测响度：

```bash
SILENCE_START=3325
SILENCE_DUR=5

# 20-200 Hz：电源嗡、桌面震动、风噪
ffmpeg -hide_banner -nostats -ss $SILENCE_START -t $SILENCE_DUR -i 原片.mp4 \
  -af "highpass=f=20,lowpass=f=200,volumedetect" -f null - 2>&1 | grep mean_volume

# 200-4000 Hz：人声 + 大多数风扇/AC
ffmpeg -hide_banner -nostats -ss $SILENCE_START -t $SILENCE_DUR -i 原片.mp4 \
  -af "highpass=f=200,lowpass=f=4000,volumedetect" -f null - 2>&1 | grep mean_volume

# >4000 Hz：嘶嘶声、磁带噪、键盘高频
ffmpeg -hide_banner -nostats -ss $SILENCE_START -t $SILENCE_DUR -i 原片.mp4 \
  -af "highpass=f=4000,volumedetect" -f null - 2>&1 | grep mean_volume
```

判断逻辑：

| 主频段 | 噪声来源（高概率） | 推荐方法 |
|---|---|---|
| 20-200 Hz 最响 | 电源 50/60 Hz、桌面震动、空调机箱低频 | `highpass=f=120` 直接秒了 |
| 200-4000 Hz 最响 | 笔记本风扇、AC、马路车流、人声底噪 | afftdn 激进 + agate；严重时上 Adobe Podcast |
| >4000 Hz 最响 | 麦克风电气底噪、廉价电容麦自噪声 | afftdn + 轻 lowpass=f=10000，或换麦 |
| 三段都差不多 | 宽频房间噪 / 信号链 SNR 整体差 | 只能上 AI 降噪 |

### 逐秒扫描（找尖峰、判断稳态/动态）

在一段已知"无人说话"的区间里，逐秒采样：

```bash
START=3323; DUR=17
for s in $(seq 0 $((DUR-1))); do
  t=$((START+s))
  result=$(ffmpeg -hide_banner -nostats -ss $t -t 1 -i 原片.mp4 \
    -af volumedetect -f null - 2>&1)
  mean=$(echo "$result" | grep mean_volume | awk '{print $5}')
  max=$(echo "$result" | grep max_volume | awk '{print $5}')
  printf "  第%2d秒: mean=%-7s max=%-7s\n" $s "$mean" "$max"
done
```

要看的几件事：

- **mean 是否爬升**：从 -30 一路涨到 -10 = AGC 在拉增益。这种用 ffmpeg 治不了，只能让用户去关掉麦的 AGC
- **max 出现 0 dB 尖峰**：是瞬态事件（键盘/转椅/呼吸），afftdn 治不了，要用 declick 或手动剪
- **mean 全程 -32 dB ± 2 dB**：稳态噪声，afftdn / 噪声门 / sox noisered 都能搞定

## 听觉掩蔽现象（重要！）

用户经常主诉："说话时底噪轻，不说话时底噪重"。

99% 是**听觉掩蔽**，不是 AGC。

底噪本身一直在 -30 dB（恒定），说话时人声 -16 dB 比底噪高 14 dB，把底噪盖住了；
不说话时没人声盖，底噪就"冒"出来。底噪没变，是听觉感知在切换。

判断方法：看长沉默逐秒扫描，mean 是稳定的 → 掩蔽；mean 在爬升 → AGC。

要消除这个现象，本质是降低底噪绝对值（让说话/静音差距 > 30 dB），不是去做什么"动态平衡"。
