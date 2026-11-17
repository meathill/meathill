# video-skills

Agent skills for **Claude Code**, **Gemini CLI**, and other Markdown-based AI
agents — covering livestream post-processing and brand IP video production by
Meathill.

## What's inside

| Skill | Triggers when you say… | Description |
|---|---|---|
| **live-replay-video-pipeline** | "处理直播录像", "转写", "剪掉停顿", "出字幕", "做章节", "章节封面", "直播回放", "webinar 回放" | 把直播录像或长视频回放处理成可发布的视频包：转写、基于 transcription 规划剪辑、剪掉冗余和长停顿、生成 SRT 字幕、章节、章节封面、最终视频和发布文案。 |
| **brand-ip-video-matrix** | "做 IP 形象", "虚拟代言人", "品牌吉祥物视频", "卖点矩阵", "一批投放素材", "TikTok / Reels / Shorts 短视频", "批量做成短视频" | 从官网抓可对外的功效口径 → 定位并设计 IP 形象 → 图生视频生成角色镜头 → 定制克隆声线与音乐床 → 装配 9:16 成片矩阵与评审包。 |

每个 skill 以一个 `SKILL.md` 承载触发描述与执行手册，细节按需拆进
`references/`，确定性动作收进 `scripts/`。

## Install

### Claude Code

Skills live in `~/.claude/skills/<name>/SKILL.md`. After `npm install`, link
each skill folder you want into that directory:

```bash
npm install video-skills
mkdir -p ~/.claude/skills

for s in brand-ip-video-matrix live-replay-video-pipeline; do
  ln -sf "$(pwd)/node_modules/video-skills/$s" ~/.claude/skills/$s
done
```

Or copy them in if you'd rather not symlink:

```bash
cp -r node_modules/video-skills/brand-ip-video-matrix ~/.claude/skills/
```

Restart Claude Code (or run `/skills`) so it picks up the new entries.

### Gemini CLI

Same shape — drop the skill folders under `~/.gemini/skills/` (or wherever
your Gemini setup expects them) and the `SKILL.md` frontmatter handles the
rest.

## Dependencies

`brand-ip-video-matrix` 需要本机有 `ffmpeg` 与 `Pillow`（渲染字幕层）。
`live-replay-video-pipeline` 另需 whisper 运行时。两者都不引入 npm 依赖。

## What's new

- **1.2.0** — 新增 **brand-ip-video-matrix**：把 Filterbaby × Phoebe 项目的实战经验固化成端到端
  流程。覆盖官网口径溯源纪律、IP 形象设定与造型硬约束写法、图生视频的首帧继承机制
  （首帧必须含角色，否则模型会自己捏一个并长出手臂）、MiMo「母版 + 复刻」两段式声线、
  PIL 字幕层、ffmpeg 装配配方与 8 条已踩坑位，附带 `assemble.py`（JSON 规格驱动的装配流水线）、
  `make_subtitle.py`、`qc_video.sh` 三个脚本。
- **1.1.0** — 初始版本，收录 **live-replay-video-pipeline**。

## License

[MIT](../../LICENSE) © Meathill Zhai <meathill@gmail.com>
