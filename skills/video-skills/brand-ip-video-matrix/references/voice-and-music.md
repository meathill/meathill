# 声线、音乐床与字幕

## 一、TTS 声线

### 为什么必须"母版 + 复刻"两步

小米 MiMo-V2.5-TTS 的 `voicedesign` 模式**不接受参考音频**——
它每次请求都会重新设计一条嗓子。四条台词分四次调用，声音必然各不相同。

正确流程：

```
第 1 步  voicedesign  → 一条母版音频（角色 / 场景 / 表演指导）
第 2 步  voiceclone   → 把母版复刻到每一条台词
```

`voiceclone` 的 `audio.voice` 必须是 **data URL**，不是裸 base64：

```
data:audio/mpeg;base64,<base64>
```

（mp3/m4a 用 `audio/mpeg`，wav 用 `audio/wav`）

### 母版提示词写法（导演模式）

用「角色 + 场景 + 表演指导」三段式，把母版设计成一条**信息量足、音素覆盖广**的自我介绍，
这样复刻到短句时音色才稳。示例：

```
角色：young adult female voice, warm and friendly, clean and bright, like fresh filtered water
场景：speaking directly to the viewer in a bright modern bathroom
表演指导：confident and upbeat, like she genuinely loves what she does
```

### 复刻的指导词必须短

实测：一句 3.36s 的台词，带冗长角色/情绪描述后变成 6.88s——**语速慢了将近一倍**。
换成简短指导只增加约 0.6 秒。

| 位置 | 内容 | 长度 |
|---|---|---|
| 风格标签 | 拼在台词最前面，括号包裹 | `(Sweet Excited)` |
| 指导词 | 单独的 user 消息 | 一行，≤ 10 词 |

```
(Sweet Excited) Filterbaby removes up to 99.9% of chlorine. Softer, shinier hair.
```
指导：`Thrilled and proud, but keep it quick.`

`keep it quick` 这类短词能有效压住语速。

### 其它实测

- MiMo 原生输出 **24 kHz 单声道**（带宽上限约 12 kHz），比 MiniMax 的 32 kHz 窄；
  最终成片统一转 48 kHz 立体声。
- 接口有**限流**：429 和 5xx 退避重试（指数退避，20s 起），4xx 参数错误立即失败。
- 参考音频文件放 `.tmp/` 并设 600 权限，key 走环境变量或文件，**不进聊天记录**。
  项目若进版本库，把 `.tmp/` 加进 `.gitignore`。

### 通用 TTS 的退化路径

没有 MiMo 时，普通的 `synthesize_speech` + 预设音色 ID 也能做，
但音色会明显更"机器"。若最终交付要给人评审，优先把时间花在拿到一条好母版上。

---

## 二、音乐床

批量生成 2–3 版风格不同的（卡通 / 活泼 / 氛围），让用户试听选定——这一步值得让用户拍板，
因为音乐床直接决定整片的情绪，和角色定位要配。

技术要点：

- 长度按最长成片准备（33s 版按 33s 生成）
- 归一化到 **RMS -18 dB** 再进混音，避免几条片子音乐响度不一致
- 音乐在混音里通常压到 **0.30**，环境音 0.34，旁白保持主导

---

## 三、字幕

### 为什么用 PIL 而不是 ffmpeg

本机 ffmpeg 编译**没带 libfreetype / libass**，`drawtext` 和 `subtitles` 滤镜都不可用。
文字全部由 PIL 渲染成带 alpha 的 PNG，再用 `overlay` 贴上去。

`scripts/make_subtitle.py` 已封装：

```bash
python3 scripts/make_subtitle.py --text "第一行\n第二行" --out build/sub.png
```

样式（已验证）：深色半透明圆角底条 `rgba(18,18,18,168)` + 白色圆体粗字 38px，
文字区最大宽 600px 自动折行，底条中心 y=1055。

### 安全区

竖版平台的底部 UI 会压掉画面下沿约 200px。字幕中心放在 **y≈1055**（768×1368 基准）
既不被 UI 压住，又不挡住角色的脸（角色通常在画面中上部）。

角色如果在画面下部，字幕要么下移要么把角色构图放在上方。

### 文案

- 字幕与旁白**同文**，不另写一套——两套文案长期会走偏。
- 英文长句折行控制在两行内，每行 ≤ 6 词。
- 字幕窗口按旁白**实际时长**自动延长，不要写死。

---

## 四、旁白与字幕的时间轴

```
旁白起点 = 画面段落起点 + 0.5 ~ 0.8s   （给画面一个起手）
字幕起点 = 旁白起点 - 0.05s
字幕终点 = max(预设终点, 旁白起点 + 旁白时长 + 0.06s)
```

排布时检查三件事：

1. 相邻两段旁白的间隔 > 0.05s，否则听起来是抢话
2. 字幕窗不越出整片时长
3. 短版（只含 B 段）的旁白起点 = 完整版起点 − offset，
   **音乐和环境音按同一个 offset 裁切**，这样短版就是完整版的中间那一段，两版能逐帧对齐比较
