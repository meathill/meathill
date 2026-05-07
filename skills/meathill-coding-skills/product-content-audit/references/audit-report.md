# Audit Report Template

第一阶段产出的报告统一用下面这个结构，让用户能够：

- 快速看出哪些是必须改的、哪些是可选的
- 在第二阶段用条目 ID 精确批准或跳过具体改动
- 知道每条建议背后的依据，而不是被一堆"看上去更好"的改写淹没

报告默认保存到 `WIP/product-content-audit-YYYY-MM-DD.md`。

---

## Required structure

ALWAYS use this exact top-level outline:

```markdown
# Product Content Audit — YYYY-MM-DD

## 0. Scope
## 1. Recent product changes
## 2. Findings
### 2.1 Jargon & plain language (J)
### 2.2 Copy out of sync with code (S)
### 2.3 Missing links / CTAs / next steps (L)
### 2.4 SEO / meta / OG (M)
### 2.5 Readability / micro-copy (R)
### 2.6 i18n gaps (I)
## 3. Open questions
## 4. Suggested order of fixes
```

每个 finding 用唯一 ID（前缀 + 序号），方便用户在第二阶段说 "应用 J1、J3、L2，跳过 S2"。

---

## 0. Scope

只列**这次审查实际看了什么**，不列你打算看但没看的。让用户知道哪些区域是被覆盖的，哪些是下次再说。

```markdown
- 主语言: zh-CN
- 其他语言: en
- 已覆盖目录: app/, components/, locales/{zh,en}.json, public/seo/
- 未覆盖（用户可决定下次是否纳入）: emails/, docs/
- 参考的最近提交: 最近 30 次（2026-04-15 ~ 2026-05-07）
```

## 1. Recent product changes

把扫到的 commit 翻译成普通用户能看懂的话，每条一句。这一节的目的是让用户**重新校准产品当前真实长什么样**，再回头看后面的 finding 才有判断力。

```markdown
- (commit a1b2c3d) 现在导出的简历 PDF 默认包含二维码；首页/帮助页可能要补一句这个能力。
- (commit 4e5f678) "Pro 模板"改名为"高级模板"；多处页面仍写着"Pro Templates"。
- (commit 7a8b9c0) 移除了第三方登录里的 GitHub 选项。
```

如果某条 commit 你没把握应该怎么用人话表达，列出来并标 `🤔` 让用户来翻译。

## 2. Findings

对每一类问题，按下面的格式写每个条目。**每条 finding 必须包含**：

- 唯一 ID（如 `J1`）
- 严重度：高 / 中 / 低
- 文件路径 + 行号 + 一段足以定位的原文
- 现在的样子（"现"）
- 建议改成什么样（"议"）—— 多语言项目里要分别给出每种语言的建议或标 🤔
- 改这个的依据是什么（"由"）—— 用业务语言解释，不要只说 "更友好"

### 模板

```markdown
- **J1 [中] components/Hero.tsx:14**
  现: "Dispatch your resume to top recruiters in one click."
  议: "Send your resume to top recruiters with one click."
  由: 普通用户不会把 dispatch 联想到"发送"。这是首页主要 CTA 上方的副标题，会直接影响用户是否继续往下读。
```

```markdown
- **L2 [高] app/dashboard/page.tsx:38**
  现: dashboard 顶部只显示用户名和"创建简历"，没有"下载桌面客户端"的入口。
  议: 在用户菜单里增加"下载桌面版"链接，指向已有的 /download 页。
  由: 客户端是产品最近主推的功能，但已经登录的用户在 dashboard 里看不到任何指向它的入口。
```

```markdown
- **I3 [中] locales/zh.json + locales/en.json**
  现: zh.json 中存在 `pricing.proPlan.tagline`，en.json 中没有同名 key。
  议: 在 en.json 中补齐对应文案。中文里写的是"全功能 + 终身免费更新"，英文版用户群更倾向于直白对比，建议由用户决定要不要保留"终身"这种营销语气。🤔
  由: 英文 locale 的定价页因为缺这个 key 会回退到 key 名本身，对用户来说像是"页面坏了"。
```

### 严重度速查（重复一遍 SKILL.md，方便用户对照）

- **高**：让真实用户**看不懂、找不到入口、放弃使用**。
- **中**：不影响能不能用，但**降低信任、影响转化或 SEO**。
- **低**：打磨级。

如果你不确定一条该归为中还是高，宁可标高，让用户来下调。

## 3. Open questions

那些**你没有信心独立判断**的问题，集中在这里，让用户回答后再进入第二阶段。

```markdown
- (Q1) 首页副标题里的 "All-in-one platform" 是个有意为之的市场用语，还是写代码时随手起的？
- (Q2) zh.json 里"恭喜"这种感叹要不要在 en.json 里同步成 "Congrats!"？英文用户的语气可能不一样。
- (Q3) 报告里 J1~J5 多处都把"endpoint"改成了"接口"，但本产品的目标用户疑似偏开发者，请确认这种风格调整方向是否正确。
```

## 4. Suggested order of fixes

按"最快减少用户损失"排序，给用户一个执行建议，但**用户有最终决定权**。

```markdown
1. **先动 L、I 类**——这些是"页面坏了"级别的问题，半小时就能改完。
2. **再动 S 类**——把 commit 提到的功能改名/下线信息，同步到产品页面。
3. **最后动 J、R 类**——需要更细的语气考量，可以先让用户决定整体调性后批量改。
4. M 类（SEO）改完后建议跑一遍 sitemap 重新提交。
```

---

## Anti-patterns（写报告时要避开）

- **"全部改成英文"或"全部统一成某种风格"** —— 这是越界。除非用户明确要求，本 skill 只逐条建议、不主张全局重构。
- **报告里写代码 diff** —— 报告是给用户看的，不是给 IDE 看的。Diff 留到第二阶段做实际修改时再生成。
- **每条都是 [高]** —— 严重度失去意义。一份健康报告里高/中/低应该各占一部分。
- **"应该把所有 button 文案再过一遍"** —— 这是任务，不是 finding。具体到哪个按钮、哪行代码、哪种改动。
- **混入与文案无关的建议**（重构、性能、依赖升级等）—— 这些不是本 skill 的职责，最多在结尾"非本次范围"区域列一句。
