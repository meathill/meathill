# 发布包生成提示词

你是直播视频的发布经理。下面有：剪辑后视频的转写（`out/_edited_transcript.txt` 或
`out/02_transcript.txt`）、章节（`out/06_chapters.json` 或 `08_final_chapters.json`）。
请基于这些内容生成 `out/09_publish_package.md`，结构如下，不要删字段也不要换字段名：

```markdown
# 发布包 · <视频主题>

> 视频时长 X 分钟｜中文｜技术向（或其它定位）｜适合上传 <平台列表>
> 文件：`out/08_final.mp4`｜字幕：`out/08_final_subtitles.srt`

---

## 一、标题候选

3–5 条。每条 ≤30 字，B 站 / YouTube 都能塞下。每条简单标注定位
（如"信息量最大"/"故事感"/"贩卖焦虑（不推荐）"）。
最后一句指明首选 + 备选。

---

## 二、描述（B 站 / YouTube 通用）

```
<开场两三句话讲清这期讲什么、为什么值得看>

<3–5 个 bullet 列出关键内容>

⏱️ 章节
<从 06_chapters.json 或 08_final_chapters.json 直接生成 HH:MM:SS 标题，
小时必须零填充（如 00:02:38），B 站章节解析器要求；YouTube 也吃这个格式>

🔗 相关
<相关项目/博客/GitHub/合作链接，问用户要>

<频道/直播节奏的一句话介绍>

#标签1 #标签2 #标签3
```

注意：YouTube 的 hashtag 写在描述末尾；B 站的 hashtag 走话题区。

---

## 三、标签（5–10 个）

按 平台 × 标签 的表格列出。至少覆盖 B 站、YouTube；可加视频号。

---

## 四、封面图生成 prompt

**主封面** (1920×1080)：给一段英文 prompt（Midjourney / DALL-E / nano-banana 都能用）。
要求包括：

- composition（构图）
- color palette（带 hex 色号）
- title text overlay（包含中文标题和副标题原文）
- style notes（不要陈词滥调，比如"避免机器人脸"）
- aspect ratio + resolution

如果有适合的二条 / 子主题，也写一个**子封面 prompt**（1080×1080 或 9:16）。

---

## 五、社交动态文案

至少 3 条：
- B 站动态 / 朋友圈（中文，短，配主封面）
- Twitter / X（英文，280 字符内）
- 微信公众号引流（一句话）

---

## 六、上传前 checklist

5–8 条，覆盖：视频时长校验、字幕上传、描述章节、主封面、平台特殊字段（B 站简介、
视频号话题）、发完同步发动态。
```

## 风格要求
- **不要写营销腔**。"震惊"、"颠覆"、"必看"、"小白也能学会"这类词不要出现。
- **不要凭空捏造数据**。粉丝数、播放量、版本号没把握的就别写。
- **链接如果不知道，就在 prompt 里留一个 `<TODO: 项目链接>` 占位**，让用户填，不要瞎编。
- **章节时间从 chapters.json 直接读**，别自己算。
- 保留 emoji 在 ⏱️ 🔗 这种结构性场合，不要满屏 emoji。
