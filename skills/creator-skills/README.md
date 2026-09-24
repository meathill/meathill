# creator-skills

Agent skills for **Claude Code**, **Gemini CLI**, and other Markdown-based AI agents — covering full-chain content creation, tech article writing, multilingual localization, and social media publishing by Meathill.

## What's inside

| Skill | Triggers when you say… | Description |
|---|---|---|
| **article-writing** | "写文章", "撰写教程", "发布博文", "整理发帖内容", "撰写封面文章", "article writing", "content creation", "publish article" | 全链路文章撰写与多平台分发技能：从事实核查、深度立意、读者视角行文、用户审校门禁，到 6 语母语级本地化、16:9 信息图封面、小红书 3:4 大字图文即粘即发及 CMS 自动化发布。 |

Every skill ships as a single `SKILL.md` containing the trigger description in its frontmatter and the playbook in its body — no JS, no runtime.

## Install

### Claude Code

Skills live in `~/.claude/skills/<name>/SKILL.md`. After `npm install`, link the skill folder into that directory:

```bash
npm install creator-skills
mkdir -p ~/.claude/skills

ln -sf "$(pwd)/node_modules/creator-skills/article-writing" ~/.claude/skills/article-writing
```

Restart Claude Code (or run `/skills`) so it picks up the new entries.

### Gemini CLI / Antigravity

Drop the skill folder under `~/.gemini/skills/` (or your workspace `.agents/skills/`) and the `SKILL.md` frontmatter handles the rest.
