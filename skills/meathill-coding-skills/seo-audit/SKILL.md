---
name: seo-audit
description: >
  对一个或多个公开网站做基于 GSC、Bing Webmaster、GA4、PageSpeed/Chrome、Ahrefs 与 Google Trends 的只读 SEO 审计；
  结合本地源码和线上 HTML 形成证据矩阵，分别汇总 GSC/Bing 关键词与内容机会，并在用户明确授权后更新或创建对应 GitHub issues。
  当用户要求全站 SEO 调研、关键词机会、搜索趋势研究、跨站 SEO 报告或把发现同步到 issue 时触发。
---

# SEO Audit

把一次分散在多个后台、浏览器会话和代码仓库里的 SEO 检查，整理成可复查、可执行、不会混淆指标口径的证据链。

本 skill 适合多站点、跨仓库、需要同时看搜索数据和实现细节的审计。它默认只读：不改源码、不部署、不提交或删除 sitemap、不请求索引、不改 GSC/Bing/GA/Ahrefs 配置、不创建 Ahrefs 项目或启动爬虫。只有用户明确要求“更新/创建 GitHub issue”时，才执行对应的 GitHub 写入；不要把 issue 授权扩大成代码或外部 SEO 设置授权。

如果需求只是仓库内的用户文案或 meta 检查，优先用 `product-content-audit`；如果需求是运行网站的人工业务验收，优先用 `website-operator-qa`；如果只关注加载性能，优先用 `web-perf`。本 skill 可以在完整审计中引用这些边界，但不要把它们的职责混在一起。

## 工作模式

先判断用户要哪一种模式：

- **完整审计**：网站清单、五类工具、Google Trends、线上页面、源码、报告和 CSV。
- **关键词研究**：重点收集 GSC/Bing query、Google Trends 主题、query-to-page 映射和内容优先级，可跳过不影响关键词判断的深度实现检查。
- **Issue 同步**：先读取既有 issue 和评论，再把新证据追加到正确 issue；只有发现独立工作包才创建新 issue。

用户说“所有网站/全站”时，默认运行完整审计；用户只要求“总结关键词”时，至少运行 GSC、Bing 和 Google Trends，并明确其他工具没有参与或数据不可用。

## 0. 建立范围和网站—账号—源码对应表

在任何工具写入或结论前，先完成范围表。优先读取：

- 用户最新的排除清单；最新指令覆盖旧清单。
- `products.json`、产品目录、部署配置和本地 `~/Documents/GitHub` 下的仓库。
- 每个正式域名的真实线上地址、重定向关系和是否为生产入口。
- GSC property、Bing Webmaster site、GA4 property、Ahrefs project 的可见性。

对每个网站记录：

```text
site → production URL → repository → GSC property → Bing site → GA property → Ahrefs project
```

并标记：正式网站、API、CMS、后台、资源域名、预览域名、重定向/退役域名、静态/客户端壳。共享仓库要去重审计，但保留受影响网站矩阵；共享 SEO bug 只开一个仓库级 issue，正文列出所有受影响站点和回归 URL。

如果源码或账号不可用，写成“源码不可用/属性未发现/数据未稳定读取”，不能写成“没有关键词/没有流量”。用户后来提供的仓库 URL 优先级最高；无法确认 repo 时，不要猜仓库，也不要把 issue 开到相似项目。

### 本项目组合的默认排除边界

对于这次 Meathill 网站组合，如果用户没有重新指定范围，默认排除：

- 永久排除：`abalone.ai`、`battleship-game.org`、`myworld.org`、`stockcalculator.io`、`hackquest.io`。
- 本轮追加排除：`ai3dmodel.app`、`55.muistory.com`、`xiaoniaoshuo.com`、`mywordle.org`。

最新用户清单可以新增、移除或替换上述列表。被排除的网站不得进入关键词优先级、跨站结论、issue 更新或新 issue；如果历史原始记录中仍有它们，明确标注“历史采集、当前范围外”，不要用它们支撑当前建议。

## 1. 证据和时间窗口规则

每条数据至少保存：网站、URL/property、工具、指标定义、观察窗口、读取时间、筛选条件、原始证据位置和证据状态。

默认窗口是：

- GSC：最近 28 个完整自然日、前一个 28 天、最近 90 天趋势；记录 GSC 实际可用的最后日期，不自行补齐数据延迟。
- Bing：以界面实际显示的窗口为准；本流程常见的是 `3 M`，必须记录页面显示的起止日期。
- GA4：最近 28 天、前一周期和 90 天趋势；同时记录归因模型、维度和 property 名称。
- Google Trends：通常过去 12 个月；记录国家/地区、Web/News/Image 等搜索类型、比较词和实际日期。
- PageSpeed/Chrome：记录设备、视口、网络、CPU、冷/热状态和测试时间；单次 trace 不是字段数据，也不是 PSI 官方分数。
- Ahrefs：记录页面显示的快照日期；不把 Ahrefs 的数据库关键词/流量与 GSC/Bing 点击展现相加。

统一用 `已验证`、`推断`、`待复核`、`数据不可用` 标注证据边界。指标时间范围或定义不同，就并列展示，不做伪造的合计或横向排名。

## 2. 收集五类工具证据

优先使用已连接的 MCP；MCP 不可用或缺少某个操作时，使用现有已登录 Chrome/浏览器会话或官方 UI。先发现可用工具和 property，再读取数据；不要索要、保存或输出凭据、Token、Cookie。

### GSC

对可访问 property 读取：

- Search Analytics 的 query、page、country、device、search appearance。
- 快速机会/高展现低点击页面，以及高位但 CTR 偏低的 query。
- Sitemaps 的提交、抓取、发现 URL 和最后读取时间。
- 重点 URL 的 URL Inspection：robots 是否允许、索引状态、Google 选择的 canonical、移动适配/增强结果（如果可读）。

保留 GSC 的 clicks、impressions、CTR、average position 原始口径。一个 property 未开放，不代表站点无搜索流量。

### Bing Webmaster

至少读取 Search Performance 的 Keywords；有权限时再读取 pages、countries、devices、SEO Reports、Index Explorer、sitemaps 和 crawl 相关状态。

- 单独导出/记录关键词表，不用 GSC 表替代 Bing 表。
- 保存页面显示的总 clicks、impressions、CTR，以及按展现排序的代表性前若干 query。
- UI 显示“数据准备中/请 48 小时后再来”时标记为“数据不可用”，不是 0。
- 记录 sitemap 成功、pending、旧 URL 仍被发现等状态；工具层的 API 退役提示不要直接写成网站 SEO 问题。

### GA4

按 property 和实际报告维度读取自然搜索入口页、sessions/active users、engagement rate、关键事件/转化；必要时补充首次用户、`google / organic` 等来源维度。

记录 GA4 的归因和数据范围，不把 session、user、event、key event 与 GSC clicks 混算。property 名字可见但指标切换不稳定时，标为“属性可见、指标未稳定读取”。如果 key events 为 0，区分“真实没有转化”和“关键事件没有配置/无法验证”。

### PageSpeed / Chrome Performance

每个纳入网站检查规范首页，最多再选两个重点入口页；每页尽量跑移动和桌面。记录字段数据（CrUX）与实验室数据、LCP/INP/CLS/FCP/TBT/TTFB 等实际可读指标。

如果 PSI API 返回 429、配额为 0 或不可用，可以用 Chrome DevTools Performance trace 作为补充实验室证据，但报告必须写明它不是 PSI 评分、不是 CrUX 字段数据，且单次样本不能代表全体用户。优先用复测验证异常波动，不要把一次慢 trace 直接升级成确定根因。

### Ahrefs

只读取已有 project：Site Audit、Organic keywords、Top pages、Broken links、Backlinks、Referring domains 和 overview。不得新建 project、启动 crawl、改 crawl 设置或修改项目配置。

记录 DR/UR、关键词、自然流量、反链和引荐域的 Ahrefs 快照口径。Ahrefs 显示 0 keywords 不等于 GSC/Bing 没有 query；如果 Site Audit 最新报告不可读，不能用旧 Health Score 当作当前失败结论。

### Google Trends

使用 Google Trends Explorer（优先现有 Chrome 会话）做小规模、有解释的比较：

1. 以 GSC/Bing 已出现的 query 组为起点，补充产品类别词、同义词和用户任务词。
2. 记录时间范围、地区、搜索类型、比较词、平均/最近/峰值相对热度。
3. 读取 related queries 和 rising queries，但将低量、突发或相关性弱的词标成探索信号。
4. 把 Trends 指数解释为归一化相对热度，不是绝对搜索量、点击预测或市场规模。

Google Trends 只负责扩展选题假设；是否排期以 GSC/Bing 的真实展现、点击、排名、页面承接和 GA 转化为准。

## 3. 线上页面和源码检查

源码与线上页面要分开记录，不能用源码“应该如此”替代生产验证。对首页和重点 URL 检查：

- HTTP 响应码、响应头、跳转链、最终 URL、缓存/压缩信号。
- raw HTML 和渲染 DOM 中的 `title`、`meta description`、`robots`、canonical、Open Graph/Twitter、`lang`、hreflang。
- `robots.txt`、sitemap 内容、URL 数、lastmod、是否混入 HTTP/旧主机/私有路由。
- H1 和标题层级、正文首屏意图、FAQ/HowTo/Article/Product/Breadcrumb 等结构化数据。
- 内链可达性、孤儿页面、图片 alt、分页/筛选/参数 URL、登录/后台/下载结果页是否误暴露。
- SSR/CSR 差异：raw HTML 缺少 canonical 或正文时，注明“原始 HTML 未检测到”，不要绝对断言渲染后也没有。

源码问题要附绝对路径和行号（如果可定位），并指出共享实现与受影响网站矩阵。对没有本地源码的网站只记录线上证据和“源码不可用”。

## 4. 选择重点 URL

每个网站必查规范首页。其余 URL按以下顺序选择：

1. GSC 点击量或展现量最高的两个公开 URL。
2. 没有 GSC 时，使用 Bing 的高展现/高点击页面。
3. 再没有 Bing 时，使用 GA 的自然搜索入口页。
4. 完全没有流量数据时，从 sitemap 选择产品主页面、内容/工具页面，以及必要的多语言或模板页面。

确认 URL 是公开页；登录、后台、API、下载结果等仅用于检查是否误被收录。PageSpeed 只跑代表性页面，不为每个 URL 机械测速。

## 5. 归纳问题、关键词和内容机会

问题类别至少包括：抓取与索引、搜索结果 CTR、元信息、内容质量、内链、结构化数据、多语言、性能、分析归因、外链与权威度。

每条问题必须有唯一 ID，并包含：严重度、网站/URL、证据来源、观察时间、源码位置、业务影响、建议、置信度和证据状态。严重度使用：

- **P0**：无法访问、无法收录、全站错误等阻断问题。
- **P1**：已有大量展现/高价值入口却明显损失点击，或严重影响增长/转化的问题。
- **P2**：较重要的质量、排名、内链、结构化数据、归因或维护问题。
- **P3**：低优先级优化、数据缺口或需长期观察的项目。

高优先级问题至少有一个直接证据；如果根因只来自一个来源，写清“单一来源”，能用两个独立来源交叉验证时优先交叉验证。不要把工具缺口、历史记录或低量趋势猜测包装成已验证问题。

### 关键词总结的最低标准

GSC、Bing、GA 和 Ahrefs 的关键词/入口数据分别成表，绝不合并指标。GSC/Bing 至少保留：

```text
site, source, query, clicks, impressions, ctr, average_position, window,
intent, landing_page, action, evidence_status
```

关键词归为用户任务/意图，而不是只按字符串相似度分组，例如“下载工具”“格式/设备”“API key”“模型信息”“成本/资格”“互动小说制作”。对每个集群给出唯一主页面、辅助页面、当前证据和建议动作。

优先识别三种机会：

- 展现高、排名约在可见区间但 CTR 低：摘要/title/首屏意图匹配机会。
- CTR 已经不错但平均位置在 11–20：内容完整度、内链和页面权威度提升机会。
- GSC/Bing 已有真实 query，且 Trends/第二来源支持同一用户任务：新页面或内容集群机会。

只有 Trends 或只有极少量 query 的主题，标为实验性选题；不要为同义词批量生成薄页面或互相竞争的 canonical。

## 6. 生成报告和可交付物

完整报告至少包含：范围与排除、结论摘要、跨站优先级、工具和实际窗口、GSC 关键词总结、Bing 关键词总结、Google Trends 研究、GA/性能/Ahrefs 证据、网站—账号覆盖矩阵、逐站总结、源码/线上检查、详细问题、访问缺口、方法与证据边界、只读验收。

默认在当前工作目录的 `outputs/` 生成：

- `seo-audit-YYYY-MM-DD.md`
- `seo-audit-YYYY-MM-DD.csv`
- `seo-keyword-summary-YYYY-MM-DD.csv`
- `seo-bing-keyword-summary-YYYY-MM-DD.csv`
- `seo-google-trends-research-YYYY-MM-DD.csv`

报告模板和字段建议见 [references/report-template.md](references/report-template.md)。如果某工具没有数据，矩阵中仍保留该列并写明原因。

## 7. GitHub Issue 闭环（仅在用户明确要求时）

Issue 是外部写入，必须先确认用户明确要求更新/创建；审计本身不自动开单。

1. 先用 GitHub MCP/connector 搜索和读取目标仓库的既有 issue、正文、评论、状态和标签；不要只按标题判断重复。
2. 对用户提供的仓库 URL 使用其精确 `owner/name`；否则从产品清单、源码和部署映射中确认，确认不了就记录缺口。
3. 已有 issue 覆盖同一工作包时，优先追加带日期的证据评论，保留原历史；只有需要改变范围/验收标准时才替换正文，并先读取完整正文。
4. 只有当发现独立、可执行、现有 issue 没覆盖的工作包时才创建新 issue。共享代码问题只创建一个 issue，并附受影响站点矩阵。
5. Issue 内容使用 [references/issue-template.md](references/issue-template.md)，至少包含背景、范围、证据和窗口、影响、工作包、验收标准、非目标、证据状态和源码位置。
6. GitHub MCP 无法访问私有仓库或返回权限/资源错误时，才用已登录 `gh api` 作为明确记录的 fallback；不要因一次搜索为空就重复创建。
7. 写入后重新读取 issue/评论，确认 URL、编号、正文/评论和排除范围。不要输出凭据。

不要仅因为“Bing/GSC/Ahrefs 没有属性”就创建空泛 issue；只有缺口本身有明确的归属和可执行的接入/验证工作时才开单。

## 8. 完成前检查

- 每个纳入网站都有源码、线上、GSC、Bing、GA、PageSpeed/trace、Ahrefs 的状态，缺失单独记录。
- 每个 P0/P1 有直接证据，或至少两个独立来源交叉验证；推断和低量样本已标注。
- GSC、Bing、GA、PageSpeed、Ahrefs、Trends 的窗口、定义和延迟没有混淆。
- GSC 和 Bing 关键词都已统计；Trends 的相对指数没有被写成搜索量。
- 重点 query 都有 landing page 判断和可执行内容/技术动作；不重复堆叠同义词页。
- 最新排除清单已应用，排除网站不出现在当前结论或 issue。
- 若用户要求同步 issue，所有更新/新建均已回读验证；没有重复开单。
- 没有修改源码、部署、sitemap、robots、索引设置、工具项目或爬虫配置，除非用户另行明确授权。
