# meathill-coding-skills

Agent skills for **Claude Code**, **Gemini CLI**, and other Markdown-based AI
agents — covering everyday software-engineering chores that Meathill keeps
running into across projects.

## What's inside

| Skill | Triggers when you say… |
|---|---|
| **code-maintenance** | "maintain", "clean up", "refactor", "tidy up", "DRY up", "address TODOs/FIXMEs", "tech debt markers" |
| **pr-review** | "PR review", "review 意见", "处理 review 留言", "review comments" |
| **product-content-audit** | "改文案", "把开发者语言改成人话", "页面跟最近功能不同步", "缺下载/升级链接", "做一次产品内容审查", "SEO/meta 检查" |
| **project-quote** | "报价", "估价", "工时评估", "给客户报价", "竞品分析报价" |
| **website-operator-qa** | "网站测试用例", "运营/客户视角验收", "manual QA", "操作录像缺陷" |

Every skill ships as a single `SKILL.md` containing the trigger description in
its frontmatter and the playbook in its body — no JS, no runtime.

## Install

### Claude Code

Skills live in `~/.claude/skills/<name>/SKILL.md`. After `npm install`, link
each skill folder you want into that directory:

```bash
npm install meathill-coding-skills
mkdir -p ~/.claude/skills

# Link all four
for s in code-maintenance pr-review project-quote website-operator-qa; do
  ln -sf "$(pwd)/node_modules/meathill-coding-skills/$s" ~/.claude/skills/$s
done
```

Or copy them in if you'd rather not symlink:

```bash
cp -r node_modules/meathill-coding-skills/code-maintenance ~/.claude/skills/
```

Restart Claude Code (or run `/skills`) so it picks up the new entries.

### Gemini CLI

Same shape — drop the skill folders under `~/.gemini/skills/` (or wherever
your Gemini setup expects them) and the `SKILL.md` frontmatter handles the
rest.

### Other agents

Any agent that loads Markdown skills via folder + `SKILL.md` should work.
The skill bodies are framework-agnostic playbooks; the frontmatter
description is what the host agent uses for routing.

## Update

```bash
npm update meathill-coding-skills
```

If you symlinked the folders, the linked skills update in place. If you
copied them, copy again after updating.

## What's new

- **1.3.2** — Keeps customer-facing quotations focused on the final project scope and commercial terms, excluding internal planning rationale, prior-draft commentary, and revision-process language.
- **1.3.1** — Makes **project-quote** product-first: plan roles, end-to-end workflows, states, and shared domain objects before deriving modules and work packages; count shared capabilities once; quote only the single service tier explicitly selected by the user.
- **1.3.0** — Reworks **project-quote** for current AI-assisted delivery: coding baselines use 10% of traditional experience time; auxiliary work is quoted at 20% / 45% / 80%; every quote includes itemized work, non-separately-priced delivery baselines, customer-paid costs, payment/handoff/acceptance/maintenance terms, and budget-aware technology options. The inventory now records proven multi-Worker + Queue + Web architecture experience.
- **1.2.0** — Adds **product-content-audit**: a two-stage skill (audit report
  first, then apply) for reviewing user-facing copy in the repo from a
  non-technical user's perspective. Targets the common case where AI-assisted
  coding moves faster than the page copy can keep up. i18n-aware; never
  auto-translates.
- **1.1.0** — `code-maintenance` adds **Task 7: Resolve TODO/FIXME Comments**.
  After every maintenance round, the skill now sweeps for `TODO`, `FIXME`,
  `HACK`, `XXX`, `BUG` markers and triages each (resolve / convert to issue /
  delete) so tech debt notes don't pile up between rounds.
- **1.0.0** — Initial release with `code-maintenance`, `pr-review`,
  `project-quote`, `website-operator-qa`.

## License

[MIT](../../LICENSE) © Meathill Zhai &lt;meathill@gmail.com&gt;
