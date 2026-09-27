---
name: seo-audit
description: >
  对一个或多个公开网站做只读 SEO 健康审计：公开页面脚本检查（PageSpeed/CrUX、robots/sitemap、结构化数据、响应头、AI 爬虫与 agent-readiness），
  加上 GSC、Bing Webmaster、Yandex Webmaster、GA4、Ahrefs、Cloudflare 等后台和 Google Trends；先复核控制台报错再出结论，
  输出去重后的 P0–P3 报告与关键词/内容机会，并在用户明确授权后更新或创建对应 GitHub issues。
  当用户要求全站 SEO 审计/体检、关键词机会、搜索趋势研究、跨站 SEO 报告、复查上一轮审计或把发现同步到 issue 时触发。
---

# SEO Audit

把一次分散在多个后台、浏览器会话和代码仓库里的 SEO 检查，整理成可复查、可执行、不会混淆指标口径的证据链；每轮结束只把运行状态写回本地配置（运行历史、已确认的陈旧报告和有意设置），通用经验另写进报告的“建议的 skill 改进”，下一轮更快、误报更少。

本 skill 适合多站点、跨仓库、需要同时看搜索数据和实现细节的审计。它默认只读：不改源码、不部署、不提交或删除 sitemap、不请求索引、不改 GSC/Bing/Yandex/GA/Ahrefs/Cloudflare 配置、不创建 Ahrefs 项目或启动爬虫。只有用户明确要求“更新/创建 GitHub issue”时，才执行对应的 GitHub 写入；不要把 issue 授权扩大成代码或外部 SEO 设置授权。

如果需求只是仓库内的用户文案或 meta 检查，优先用 `product-content-audit`；如果需求是运行网站的人工业务验收，优先用 `website-operator-qa`；如果只关注加载性能，优先用 `web-perf`。本 skill 可以在完整审计中引用这些边界，但不要把它们的职责混在一起。

## 工作模式

先判断用户要哪一种模式：

- **完整审计**：配置里的全部网站、公开检查、所有已登录后台、Google Trends、线上页面、源码、报告和 CSV。
- **关键词研究**：重点收集 GSC/Bing query、Google Trends 主题、query-to-page 映射和内容优先级，可跳过不影响关键词判断的深度实现检查。
- **Issue 同步**：先读取既有 issue 和评论，再把新证据追加到正确 issue；只有发现独立工作包才创建新 issue。

用户说“所有网站/全站”时，默认运行完整审计；用户只要求“总结关键词”时，至少运行 GSC、Bing 和 Google Trends，并明确其他工具没有参与或数据不可用。开始前把范围和检查项简要告诉用户，只问是否要增减检查项，不要逐项确认。

## 0. 审计配置、范围和网站—账号—源码对应表

### 审计配置文件

站点清单等私有信息不写进本 skill，而是放在一个**本地、不公开**的审计配置文件里（位置由用户或宿主 agent 约定）。每轮开始先读它，结束时更新它。结构见 [references/config-template.md](references/config-template.md)，至少包含：

- 网站清单和 `site → repository` 对应表（共享仓库注明子应用/目录）。
- 排除清单；用户最新指令覆盖配置里的旧清单。
- 各后台的登录/访问说明（只写“在哪登录、用哪个账号”，不写凭据；API key 只写环境变量名）。
- **已知有意设置**：看起来像问题、但是用户有意为之的配置（例如某站在 CDN 里屏蔽 AI 训练爬虫、但允许搜索和 agent）。命中时不要当 bug 上报。
- **已知陈旧的控制台报告**：历史上反复出现但复测多为误报的项目（如 GSC 5xx、sitemap “无法获取”、Yandex DNS 错误）。仍需复测，但默认怀疑。
- 运行历史：日期、各优先级数量、报告位置，用于“与上轮相比”。

没有配置文件时，从下列来源建立一份，并在报告末尾建议用户保存：

- `products.json`、产品目录、部署配置和本地仓库。
- 每个正式域名的真实线上地址、重定向关系和是否为生产入口。
- GSC property、Bing site、Yandex site、GA4 property、Ahrefs project、Cloudflare zone 的可见性。

### 对应表

对每个网站记录：

```text
site → production URL → repository → GSC property → Bing site → Yandex site → GA property → Ahrefs project → CDN zone
```

并标记：正式网站、API、CMS、后台、资源域名、预览域名、重定向/退役域名、静态/客户端壳。共享仓库要去重审计，但保留受影响网站矩阵；共享 SEO bug 只开一个仓库级 issue，正文列出所有受影响站点和回归 URL。

如果源码或账号不可用，写成“源码不可用/属性未发现/数据未稳定读取”，不能写成“没有关键词/没有流量”。用户后来提供的仓库 URL 优先级最高；无法确认 repo 时，不要猜仓库，也不要把 issue 开到相似项目。

被排除的网站不得进入关键词优先级、跨站结论、issue 更新或新 issue；如果历史原始记录中仍有它们，明确标注“历史采集、当前范围外”，不要用它们支撑当前建议。

### 工作目录

每轮新建独立工作目录（如 `seo-audit-YYYYMMDD/`），按来源分 `raw/` 子目录（`raw/psi/`、`raw/gsc/`、`raw/bing/`、`raw/verify/` …），原始数据落盘后再汇总，方便复查和下轮对比。

工作目录必须放在本地私有位置，不能在任何 git 仓库内（尤其是公开仓库或本 skill 所在仓库），也不要同步到公开网盘。原始数据含搜索词、流量、控制台问题和 CDN 配置，只留在本地。对外（issue、PR、分享给他人）只给必要的、脱敏后的报告片段，不附原始导出文件。

## 1. 证据和时间窗口规则

每条数据至少保存：网站、URL/property、工具、指标定义、观察窗口、读取时间、筛选条件、原始证据位置和证据状态。

默认窗口是：

- GSC：最近 28 个完整自然日、前一个 28 天、最近 90 天趋势；记录 GSC 实际可用的最后日期，不自行补齐数据延迟。
- Bing：以界面实际显示的窗口为准；常见是 `3 M`，必须记录页面显示的起止日期。
- GA4：最近 28 天、前一周期和 90 天趋势；同时记录归因模型、维度和 property 名称。
- Google Trends：通常过去 12 个月；记录国家/地区、Web/News/Image 等搜索类型、比较词和实际日期。
- PageSpeed/CrUX：CrUX 是 28 天滚动字段数据，注意是否回退到 origin 级；实验室数据记录设备、网络、测试时间。单次 trace 不是字段数据，也不是 PSI 官方分数。
- Ahrefs：记录页面显示的快照日期；不把 Ahrefs 的数据库关键词/流量与 GSC/Bing 点击展现相加。
- Cloudflare：记录统计窗口（如 24h 缓存命中率）。

统一用 `已验证`、`推断`、`待复核`、`数据不可用` 标注证据边界；复测过的控制台报错另标 `已复现` / `线上正常·控制台待处理` / `陈旧`（定义见第 4 节）。指标时间范围或定义不同，就并列展示，不做伪造的合计或横向排名。

## 2. 公开检查（无需登录，脚本化，可后台运行）

先跑这部分，它不占用浏览器会话，可以和后台检查并行准备。

- **PageSpeed Insights API**：移动 + 桌面，读取 CrUX 字段数据（LCP/INP/CLS/FCP/TTFB p75）和实验室数据。匿名调用很容易 429（共享日配额），用用户提供的 API key，通过环境变量读取，绝不打印或写入报告。不要在本机并行跑 headless Chromium/Lighthouse，容易把机器拖垮；本地 Lighthouse 只作兜底并注明不可与 PSI 直接比较。
- **robots.txt / sitemap**：读取 sitemap（含 sitemap index），统计 URL 总数，再**有界、限速**地请求其中的 URL，记录非 200、重定向、HTTP/旧主机/私有路由、lastmod 异常。
  - sitemap 文档本身也有上限：每站最多读取 50 个 sitemap 文件，单个响应体不超过 10MB（如 `curl --max-filesize`），sitemap 阶段每站总耗时不超过 2 分钟，同样遵守下面的并发和间隔。超限时按子 sitemap 抽样读取，URL 总数标为“估算”（已读文件的平均 URL 数乘以子 sitemap 数）或“不可用”，不要写成精确值。
  - 请求目标限制（防 SSRF）：只接受 `http`/`https` URL；只请求配置里该站的生产域名和明确登记的别名；sitemap 里指向其他主机、`localhost`、私有/链路本地/保留 IP（RFC1918、`169.254.0.0/16`、`127.0.0.0/8`、`::1`、`fc00::/7` 等）的 URL 一律不请求，只在报告里记为“sitemap 含站外/私有 URL”。请求前先解析 DNS，解析到私有或保留地址也拒绝；不自动跟随跨主机跳转，只记录 `Location`，同主机跳转最多跟 5 次。
  - 默认上限：每站最多请求 500 个 URL（可在配置里按站点调整）。超过上限时按子 sitemap 均匀抽样，并保证重点 URL 和每种模板/语言至少各一个。
  - 默认节奏：同一主机并发不超过 2，请求间隔不少于 250ms，单请求超时 10 秒；优先用 HEAD，不支持时再 GET。遇到 429 或连续 5xx 时遵守 `Retry-After` 并降速，仍失败就停止该站并记录“扫描中断”。
  - 超过上限的全量扫描必须由用户明确要求或在配置里显式开启。报告里写明“已请求 N / 共 M 个 URL，抽样方式”。
- **llms.txt / llms-full.txt 与 agent-readiness**：可用 isitagentready.com 之类工具评估等级；robots.txt 缺 `Content-Signal` 通常是 Level 2 的缺口。
- **结构化数据**：解析 JSON-LD，标记无效 JSON、`@context` 非 schema.org、缺 logo/image/rating 等必填/推荐字段、Schema.org 真正弃用（superseded）的类型或属性。另外单独标注“类型仍有效、但搜索引擎已不再展示富结果”的情况（如 Google 已取消 `HowTo` 富结果，FAQ 富结果只对少数权威站点展示）：这类只记为 P2 提示（富结果收益为零，可保留或精简），不算结构化数据错误。
- **响应头和页面基础**：cache-control、`cf-cache-status`（HTML 是否被边缘缓存）、跳转链、canonical、hreflang 一致性（语言路径是否真的返回对应语言）、H1 是否存在。
- **AI 爬虫 UA 测试**：用 GPTBot、ClaudeBot 等 UA 请求首页，记录 403；再对照配置里的“已知有意设置”判断是否为 bug。
- **外链下限**：没有更好数据源时，用 Common Crawl 网页图谱（域名级）估计引用域下限，并注明覆盖面远小于商业工具、子域名归到父域。

## 3. 已登录后台（只读，一次只开一个浏览器会话）

优先使用已连接的 MCP；MCP 不可用或缺少某个操作时，使用现有已登录浏览器会话或官方 UI。一次只跑一个浏览器子任务，避免会话互相干扰。先发现可用工具和 property，再读取数据；不要索要、保存或输出凭据、Token、Cookie。Google 登录要求 2FA 时，把桌面交给用户处理，不要尝试绕过。

### GSC

- 人工操作（manual actions）、安全问题。
- 网页索引编制：各未编入原因及数量、样例 URL。
- Sitemaps 的提交、抓取、发现 URL 和最后读取时间。
- Core Web Vitals 报告、增强功能（结构化数据）报告。
- Search Analytics 的 query、page、country、device、search appearance；快速机会/高展现低点击页面，以及高位但 CTR 偏低的 query。
- 重点 URL 的 URL Inspection：robots 是否允许、索引状态、Google 选择的 canonical。

保留 GSC 的 clicks、impressions、CTR、average position 原始口径。一个 property 未开放，不代表站点无搜索流量。

### Bing Webmaster

- Search Performance 的 Keywords（单独成表，不用 GSC 表替代）；有权限时再读 pages、countries、devices。
- Site Scan / SEO Reports（重复 title、缺 description 等）、首页 URL Inspection、IndexNow 状态、Crawl 设置/抓取量、sitemaps。
- 保存页面显示的总 clicks、impressions、CTR，以及按展现排序的代表性 query。
- UI 显示“数据准备中/请 48 小时后再来”时标记为“数据不可用”，不是 0；工具层的 API 退役提示不要写成网站 SEO 问题。

### Yandex Webmaster

读取站点问题（critical / possible）和低价值页面。站点刚添加时数据很薄，要注明；Yandex 的 DNS 错误常在线上已恢复，但仍需复测并按第 4 节区分线上结果和控制台状态。

### GA4

- 按渠道的 sessions、engagement；自然搜索入口页、关键事件/转化。
- 识别类似机器人的 Direct 流量（极低互动、集中来源地/时间）。
- 核对每个站点页面上的 tag ID 是否对应真实 property 和正确的数据流 URL。

记录 GA4 的归因和数据范围，不把 session、user、event、key event 与 GSC clicks 混算。property 可见但指标切换不稳定时，标为“属性可见、指标未稳定读取”。key events 为 0 时，区分“真实没有转化”和“关键事件没有配置/无法验证”。

### Ahrefs（Webmaster Tools）

只读取已有 project：Health Score 及变化、已抓取/损坏/重定向/被阻止数量、DR、引荐域及 30 天变化、Organic keywords、Top pages；对分数最低的项目再看 top issues。不得新建 project、启动 crawl、改 crawl 设置或点升级/试用。

引荐域上涨但 DR 不动，通常是垃圾外链，记为 P2 观察项。Ahrefs 显示 0 keywords 不等于 GSC/Bing 没有 query；最新 Site Audit 不可读时，不能用旧 Health Score 当作当前结论。

### Cloudflare / CDN

按 zone 读取：Bot Fight Mode、AI Crawl Control（搜索 / agent / 训练三类分别是否允许）、托管 robots.txt、缓存规则（有没有规则缓存 HTML？有没有规则把含登录态的动态页面也缓存了？）、24h 缓存命中率。缓存规则的发现要用 `cf-cache-status` 实测几张 HTML 页面交叉验证。慢 TTFB + HTML 未缓存通常是同一个问题。

### Google Trends

1. 以 GSC/Bing 已出现的 query 组为起点，补充产品类别词、同义词和用户任务词。
2. 记录时间范围、地区、搜索类型、比较词、平均/最近/峰值相对热度。
3. 读取 related / rising queries，将低量、突发或相关性弱的词标成探索信号。
4. 把 Trends 指数解释为归一化相对热度，不是绝对搜索量、点击预测或市场规模。

Google Trends 只负责扩展选题假设；是否排期以 GSC/Bing 的真实展现、点击、排名、页面承接和 GA 转化为准。

## 4. 上报前复核

控制台报错常常滞后于线上状态，不复核不能进 P0/P1。复核要把**线上复测结果**和**控制台状态**分开记录：

- 对控制台报告的错误样例 URL（5xx、sitemap “无法获取”、DNS 错误、软 404 等）重新 curl：普通浏览器 UA 和 Googlebot UA 各请求 2 次，记录状态码和时间，存到 `raw/verify/`。每类报告最多取 10 个样例，沿用第 2 节的限速规则。
- 伪装 UA 只能说明“当前 Web 端点对这个 UA 字符串的响应”，不能证明报告时刻的状态、搜索引擎真实出口 IP 的可达性、robots 解析或后台 sitemap 处理已经恢复。能用时，再用控制台自带的实时检测（如 GSC URL Inspection 的“测试实际网址”、Bing URL Inspection）确认。
- 按三种状态标记：
  - `已复现`：线上复测仍失败。可以按影响定为 P0/P1；仅在用户明确授权更新/创建 issue 时，才开代码/部署 issue，否则只列入报告中的建议 issue。
  - `线上正常·控制台待处理`：线上复测正常，但控制台仍在报。不开代码 issue，也不进 P0/P1；放进“控制台动作清单”（验证修复、重新提交 sitemap、请求重新抓取），并在下一轮确认结果。若控制台实时检测也失败，改判为 `已复现`。
  - `陈旧`：只有在控制台已重新处理且报告消失（验证通过、重新读取 sitemap 成功、错误样例的最近抓取时间晚于修复且状态正常）之后才能这样标。
- 上报前对照配置里的“已知有意设置”和“已知陈旧报告”。

## 5. 线上页面和源码检查

源码与线上页面要分开记录，不能用源码“应该如此”替代生产验证。对首页和重点 URL 检查：

- HTTP 响应码、响应头、跳转链、最终 URL、缓存/压缩信号。
- raw HTML 和渲染 DOM 中的 `title`、`meta description`、`robots`、canonical、Open Graph/Twitter、`lang`、hreflang。
- H1 和标题层级、正文首屏意图、结构化数据。
- 内链可达性、孤儿页面、图片 alt、分页/筛选/参数 URL、登录/后台/下载结果页是否误暴露。
- SSR/CSR 差异：raw HTML 缺少 canonical 或正文时，注明“原始 HTML 未检测到”，不要绝对断言渲染后也没有。

源码问题要附路径和行号（如果可定位），并指出共享实现与受影响网站矩阵。对没有本地源码的网站只记录线上证据和“源码不可用”。

### 选择重点 URL

每个网站必查规范首页。其余 URL 按以下顺序选择：

1. GSC 点击量或展现量最高的两个公开 URL。
2. 没有 GSC 时，使用 Bing 的高展现/高点击页面。
3. 再没有 Bing 时，使用 GA 的自然搜索入口页。
4. 完全没有流量数据时，从 sitemap 选择产品主页面、内容/工具页面，以及必要的多语言或模板页面。

PageSpeed 只跑代表性页面，不为每个 URL 机械测速。

## 6. 归纳问题、关键词和内容机会

**跨来源去重**：只有根因已经验证时，才把多个来源的症状合并成一条，并在证据里列出所有来源（例如已确认 HTML 因 `s-maxage=1` 未被边缘缓存、回源才慢，这时 Yandex 报服务器慢、CrUX TTFB 差、Ahrefs 慢页面可以合并）。根因没验证时（HTML 不缓存可能是有意策略，TTFB 慢也可能来自 origin 或数据库），保留为独立问题并互相引用，写明“疑似同一根因，待验证”。

问题类别至少包括：抓取与索引、搜索结果 CTR、元信息、内容质量、内链、结构化数据、多语言、性能、CDN/缓存、AI 爬虫与 agent-readiness、分析归因、外链与权威度。

每条问题必须有唯一 ID，并包含：严重度、网站/URL、证据来源、观察时间、源码位置、业务影响、建议、置信度和证据状态。严重度使用：

- **P0**：有真实展现的页面正在丢失索引/流量，或全站级故障（无法访问、无法收录、全站错误）。
- **P1**：修复方式明确且影响可观，如已有大量展现却明显损失点击、CWV 字段数据未通过、严重影响增长/转化。
- **P2**：卫生类问题：质量、排名、内链、结构化数据、归因、垃圾外链观察等。
- **P3**：低优先级优化、数据缺口或需长期观察的项目。

高优先级问题至少有一个直接证据；如果根因只来自一个来源，写清“单一来源”，能用两个独立来源交叉验证时优先交叉验证。不要把工具缺口、历史记录、陈旧控制台报告或低量趋势猜测包装成已验证问题。

### 关键词总结的最低标准

GSC、Bing、GA 和 Ahrefs 的关键词/入口数据分别成表，绝不合并指标。GSC/Bing 至少保留：

```text
site, source, query, clicks, impressions, ctr, average_position, window,
intent, landing_page, action, evidence_status
```

关键词归为用户任务/意图，而不是只按字符串相似度分组。对每个集群给出唯一主页面、辅助页面、当前证据和建议动作。优先识别三种机会：

- 展现高、排名约在可见区间但 CTR 低：摘要/title/首屏意图匹配机会。
- CTR 已经不错但平均位置在 11–20：内容完整度、内链和页面权威度提升机会。
- GSC/Bing 已有真实 query，且 Trends/第二来源支持同一用户任务：新页面或内容集群机会。

只有 Trends 或只有极少量 query 的主题，标为实验性选题；不要为同义词批量生成薄页面或互相竞争的 canonical。

## 7. 生成报告和可交付物

报告用用户的语言，至少包含：简短结论、范围与排除、优先级总表（网站、来源、证据数字、修复建议、仓库、是否已复核）、工具和实际窗口、GSC/Bing 关键词总结、Google Trends 研究、GA/性能/Ahrefs 证据、CDN 汇总、网站—账号覆盖矩阵、逐站总结、详细问题、**按仓库分组的建议 issue**、**仅需在控制台处理的动作清单**、**与上一轮相比的变化**（新增/已修复/仍存在）、访问缺口与证据边界、只读验收。

默认在工作目录生成：

- `FINAL-REPORT.md`（或 `seo-audit-YYYY-MM-DD.md`）
- `seo-audit-YYYY-MM-DD.csv`
- `seo-keyword-summary-YYYY-MM-DD.csv`
- `seo-bing-keyword-summary-YYYY-MM-DD.csv`
- `seo-google-trends-research-YYYY-MM-DD.csv`

报告模板和字段建议见 [references/report-template.md](references/report-template.md)。如果某工具没有数据，矩阵中仍保留该列并写明原因。交付时发送摘要和报告文件，并询问用户要把哪些优先级开成 issue。

## 8. GitHub Issue 闭环（仅在用户明确要求时）

Issue 是外部写入，必须先确认用户明确要求更新/创建；审计本身不自动开单。

1. 逐个确认目标仓库：用户提供的精确 `owner/name` 优先；否则从配置、产品清单、源码和部署配置（如 wrangler 配置里的域名）确认，确认不了就在正文注明“仓库未确认”或记录缺口。
2. 搜索并读取目标仓库的**打开和近期关闭**的 issue、正文、评论、状态和标签；不要只按标题判断重复。已有 issue 覆盖同一工作包时，追加带日期的证据评论，保留原历史；只有需要改变范围/验收标准时才替换正文，并先读取完整正文。近期关闭但问题复现的，评论说明复现证据。
3. 只有当发现独立、可执行、现有 issue 没覆盖的工作包时才创建新 issue。共享代码问题只创建一个 issue，并附受影响站点矩阵。
4. Issue 内容使用 [references/issue-template.md](references/issue-template.md)，至少包含问题、带日期的证据和窗口、受影响 URL、影响、修复建议、验收标准、非目标、证据状态和源码位置。
5. 优先用 GitHub MCP/connector；无法访问私有仓库或返回权限错误时，才用已登录 `gh` 作为明确记录的 fallback；不要因一次搜索为空就重复创建。
6. 不关闭 issue，不开/不合并 PR。写入后重新读取 issue/评论，确认 URL、编号、正文/评论和排除范围，并把每个 issue 链接回报给用户。

不要仅因为“Bing/GSC/Ahrefs 没有属性”就创建空泛 issue；只有缺口本身有明确的归属和可执行的接入/验证工作时才开单。

## 9. 闭环：更新本地配置

默认闭环只写本地私有配置，不修改本 skill 或任何发布包：

- 在审计配置的运行历史里追加本轮：日期、各优先级数量、issue 数量、报告位置。
- 更新“已知陈旧报告”和“已知有意设置”列表（控制台已确认消失、判定为 `陈旧` 的模式加入；用户确认为有意的加入；已不再出现的移除）。
- 本轮踩到的通用经验（新的误报模式、工具配额、界面变化）写进报告的“建议的 skill 改进”一节，不直接改 skill。
- 只有用户单独明确授权后，才把这些建议作为一次独立变更（例如单独的 PR）提交，并经过审查；提交前去掉所有站点私有信息、路径和凭据。

## 10. 完成前检查

- 每个纳入网站都有源码、线上、GSC、Bing、Yandex、GA、PageSpeed/CrUX、Ahrefs、CDN 的状态，缺失单独记录。
- 每个 P0/P1 有直接证据或两个独立来源交叉验证；控制台报错已复测，线上结果和控制台状态分开标注（已复现 / 线上正常·控制台待处理 / 陈旧）；sitemap 扫描有上限并写明抽样范围；推断和低量样本已标注。
- 已对照“已知有意设置”，没有把有意配置报成 bug。
- 各工具的窗口、定义和延迟没有混淆；Trends 的相对指数没有被写成搜索量；跨来源同根因已合并。
- 重点 query 都有 landing page 判断和可执行内容/技术动作；不重复堆叠同义词页。
- 最新排除清单已应用，排除网站不出现在当前结论或 issue。
- 若用户要求同步 issue，所有更新/新建均已回读验证；没有重复开单。
- 报告包含“与上一轮相比”和“建议的 skill 改进”，配置的运行历史已更新；未经单独授权没有修改本 skill。
- 没有修改源码、部署、sitemap、robots、索引设置、CDN、工具项目或爬虫配置，除非用户另行明确授权；没有输出任何凭据。
