# 图生视频：角色一致性与提示词

## 一、核心机制：首帧继承

图生视频 = 拿一张图当第一帧，模型在这个锚点上往后演。
**角色长什么样，取决于第一帧里有没有它。**

| 首帧内容 | 模型行为 | 后果 |
|---|---|---|
| 含角色 | 沿用参考图造型 | 手臂、眼睛、面板形状都保得住 |
| 不含角色 | 自己捏一个 | 长出手臂、丢五官、把面板改成圆形 |

实测：首帧里没有角色时，连续三轮生成都长出了小圆手，改用标准造型帧做首帧后一次通过。
**这不是提示词能救的问题，是锚点问题。**

推论：所有需要出现角色的镜头，首帧都要能拿到角色。
首帧素材不够时，从已有成片里抽帧（用 `ffmpeg -ss <t> -i <video> -frames:v 1`），
抽帧时挑**中景**而不是特写。

---

## 二、提示词结构

四块，顺序固定：

```
[角色描述块]  ← 从模型表复制，每次原样粘贴
[动作块]      ← 镜头怎么走、物件怎么动
[风格块]      ← 渲染风格、灯光、色调
[禁止项]      ← no on-screen text, no lettering, no logo
```

### 动作块的写法

- 用**描述式**，不要用祈使式。`The camera slowly pushes in toward…` 比 `Push in toward…` 稳。
- 一段只写 2–3 个动作。动作太多模型会把它们压成一团，产出"爆炸图"。
- 避免让角色**互动**的动词：patting / holding / tapping / leaning over / picking up。
  这些词会显著提高模型给角色补手臂的概率。
- 物件要运动时，写"**自行**滑落 / 自己移动"，不要写"角色把它推下去"。

### 禁肢的有效表述

无效：
```
The character is small, no arms, no hands.
```

有效：
```
The cube has NO arms and NO hands; the sides of the cube are smooth and plain with
nothing attached to them, and the only parts below are two tiny square feet.
```

写 "small / tiny" 也没有效果——模型仍会把角色放大。
**唯一有效的是描述侧面的形态，以及让首帧里有正确的角色。**

### 锁朝向

角色转身背对镜头是续接段的高发问题。写：
```
It keeps facing the camera the entire shot, so its face is always visible.
The camera holds its framing with only a very slow slight push-in and never travels
around, past, or behind the character.
```

### 收尾要求

每条视频的**最后几秒要是中景或全景**。
接续段的首帧如果取自特写末帧，模型会丢失整体轮廓，转而臆造解剖结构（补手臂、变形）。

---

## 三、续接段

一条卖点通常需要两段画面（如 10s + 6s）。第二段：

1. 首帧 = **第一段同一条视频**的末帧，用 `ffmpeg -sseof -0.1 -i <video> -frames:v 1` 抽
2. 提示词用 "Continuing the same …" 开头，保持场景、光线、角色描述块完全一致
3. 镜头运动要弱：只允许缓慢推近，禁止绕行、推过角色、越过角色

如果第一段末帧的角色造型不对，续接段会把这个错误继承下去——先修第一段。

---

## 四、通道与参数

### 可用性

| 通道 | 状态 |
|---|---|
| 文生视频 | **不可用**。产出"通用蓝色方块"式画面，无眼睛、无小脚、亮面、还可能横版 |
| 图生视频（first_frame） | 可用，是唯一可靠路径 |
| 图片生成 | 额度耗尽时全线 402；降级方案见下 |

### 已验证的提交参数

```json
{
  "model": "MiniMax-Hailuo-2.3",
  "prompt": "<描述式提示词，≤3000 字符>",
  "reference_type": "first_frame",
  "input_image": {"url": "<upload_temp_url 返回的 temp_url>", "mime_type": "image/jpeg"},
  "duration": 6,
  "resolution": "768P"
}
```

轮询用同一 `task_id` + `model`，25 秒一次；终态 `succeeded` / `failed`。

首帧上传拿临时 URL（**约 1 小时有效**，批量生成时边传边用，别提前全传）。

H3 / H3-Max 的 2K 输出需要先告知计费并获得明确确认；Hailuo-2.3 不需要。

### 额度受限时的降级

图片生成 402 时，首帧可以从已有素材派生：

| 来源 | 做法 |
|---|---|
| 已有角色帧局部裁切 | `ffmpeg -i <frame> -vf "crop=W:H:X:Y,scale=768:1368"` |
| 已有成片抽帧 | `ffmpeg -ss <t> -i <video> -frames:v 1 -vf "scale=768:1368"` |
| 已有视频的特定画面 | 从已质检通过的镜头里抽构图合适的帧 |

派生帧的代价是场景多样性受限（不同卖点可能撞场景），要在评审文档里如实写明。

---

## 五、质检

生成完必须抽帧看，不能只看任务状态 `succeeded`。

```bash
# 1) 8–9 帧拼 strip 看整体走向
for t in 0.3 1.5 2.8 4.0 5.2 6.5 7.6 8.6 9.6; do
  ffmpeg -y -loglevel error -ss $t -i clip.mp4 -frames:v 1 -vf scale=340:606 f_$t.jpg
done
ffmpeg -y -loglevel error -i f_0.3.jpg -i f_1.5.jpg … -filter_complex "[0][1][2]…hstack=inputs=9" strip.jpg

# 2) 放大角色的脸和侧面查手臂/五官
ffmpeg -y -loglevel error -ss 8.6 -i clip.mp4 -frames:v 1 -vf "crop=460:520:150:620,scale=690:780" zoom.jpg
```

检查项：手臂、眼睛位置、面板形状、角色朝向、有没有意外出现的第二个角色、意外的文字。
