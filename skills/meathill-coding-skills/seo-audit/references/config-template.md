# SEO 审计配置模板

把下面的结构保存为一个**本地、不提交到公开仓库**的配置文件（例如 `~/seo-audit/config.md`），每轮审计开始时读取、结束时更新。本模板只示意结构，示例域名均为虚构。

```markdown
# SEO audit config — 修改本文件即可调整范围
Updated: YYYY-MM-DD

## Sites
| Site | Production URL | Repo | GSC | Bing | Yandex | GA4 | Ahrefs | CDN | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| example.com | https://example.com/ | owner/example-web | … | … | … | … | … | … | 主站 |
| app.example.com | https://app.example.com/ | owner/example-web (apps/app) | … | … | … | … | … | … | 共享仓库/子应用 |
| blog.example.org | https://blog.example.org/ | owner/blog | … | … | … | … | … | … | |

## Exclude
退役域名、合作方站点、社交平台账号页等。用户最新指令覆盖本列表。

## Access notes
- 哪些后台已在哪个浏览器会话登录（GSC/GA4、Bing、Yandex、Ahrefs、Cloudflare…），用哪个账号。
- Google 登录可能要求 2FA → 交给用户。
- PSI API key：只写环境变量名（如 `PSI_API_KEY`），不写值，不写密钥文件路径。
- GitHub CLI/MCP 以哪个账号认证。

## Scan limits（可选；不写则用 skill 默认值）
- 默认：每站 sitemap 最多请求 500 个 URL，同主机并发 ≤ 2，间隔 ≥ 250ms，超时 10s。
- 覆盖示例：blog.example.org 上限 200。
- 全量扫描（显式开启）：example.com，理由：URL 少于 1000。

## Known intentional settings（不要当 bug 上报）
- example.com 在 CDN AI Crawl Control 中屏蔽 AI *训练* 爬虫（允许搜索和 agent）→ GPTBot/ClaudeBot 403 属预期。

## Known stale console reports（控制台曾确认消失后又反复出现的模式；仍需复测）
- GSC：app.example.com 的 5xx；blog.example.org sitemap “无法获取”。
- Yandex：example.com DNS 错误。

## Run history
- YYYY-MM-DD：第 1 轮（仅 GSC）。
- YYYY-MM-DD：第 2 轮完整审计，P0 x / P1 y / P2 z；开 n 个 issue。报告：<路径>
```

维护规则：

- 控制台确认报告已消失（判定为陈旧）的报错模式加入 “Known stale”；连续几轮不再出现的移除。
- 用户确认“这是故意的”设置加入 “Known intentional”，并写清范围（哪个站、哪类爬虫/规则）。
- 不在配置里保存任何凭据、Token、Cookie 或密钥文件内容。
