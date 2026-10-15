---
name: email-campaign
description: >
  全链路营销与产品动态邮件发送运维技能：覆盖目标受众清洗（高危中小学学生域名与假号拦截、Private Relay 与测试域过滤）、
  Resend Contacts / Audience 订阅中心同步与权威退订状态治理、每日配额与事务缓冲精算、Seed 白名单预发验收、
  滚动批次投递、Resend 瞬态网络重试、退信与压制根因诊断，以及退信邮箱自动治理。
  当用户提到“发送营销邮件”、“发邮件活动”、“邮件营销”、“邮件分批”、“email campaign”、“newsletter campaign”、“活动邮件”、“检查退信”、“邮件拒收”、“退订”时触发。
---

# Email Campaign Skill

本技能固化了从受众清洗、订阅中心集成、白名单验证、分批发送到退信诊断治理的**全链路营销邮件工程实践**。
核心目标是：**在严守发信服务商配额与反垃圾信誉的前提下，安全、稳健地完成大规模邮件投递，坚决杜绝因高危邮箱导致域名进入黑名单，并以发信服务商官方订阅体系（如 Resend Contacts / Audience）为权威闭环处理受众与退订**。

---

## 核心准则与安全红线（Prerequisites & Hard Rules）

1. **域名信誉高于一切**：
   - 近 15 天退信率（Bounce Rate）严格红线为 **3.5% ~ 4.0%**。一旦当前退信率或本批保守估算越线，必须**立刻熔断停止发送**。
2. **严守每日配额精算**：
   - 每日计划消耗必须留足缓冲：
     $$\text{当日已发} + \text{日常业务/事务邮件预留} + \text{当前批次人数} + \text{安全缓冲(20)} \le \text{发信商每日限额}$$
   - 例如 Resend 免费额度每日 100 封，扣除已用与业务预留后，单批最多允许 40 封。
3. **以发信平台订阅中心（Resend Contacts）作为权威状态源**：
   - 受众必须同步至发信平台（Resend Contacts / Audience），方便运营在官方后台直观查看受众状态；
   - 任何批次发信前，**必须全量拉取发信平台的 `unsubscribed: true` 联系人**，以服务商后台退订记录为绝对权威，坚决不给已退订用户发信。
4. **严禁直接发真实用户（Seed 预发闭环）**：
   - 第 0 批必须由团队核心白名单邮箱进行真实收信验收，排版与多语言无误后方可推进。
5. **异常邮箱即刻治理（零容忍）**：
   - 任何发生退信（Hard Bounce / Transient 550）或被服务商压制（Suppressed）的邮箱，必须**立刻在发信平台打标退订（`unsubscribed: true`）**并从后续批次剔除，防止重复消耗配额与累积投诉。

---

## 阶段一：受众清洗与风险特征阻断（Audience Hygiene）

### 1. 基础合规过滤
- 剔除已注销账户（`deletedAt` 存在）或封禁中用户。
- 排除苹果匿名中继邮箱（`privaterelay.appleid.com`、`private.icloud.com`，防退信且打开率极低）。
- 排除保留测试域名（`example.com`、`*.test` 等）。
- 严格去重与空邮箱过滤。

### 2. 高危中小学/学生邮箱识别与拦截（实战踩坑重点！）
> [!CAUTION]
> **中小学与国际学校学生邮箱是营销邮件最大的退信炸弹！**
> 1. **网关严苛拦截**：中小学机构通常配置 Google Workspace for Education / Microsoft 365 严格白名单，任何外部营销邮件直接返回 `550-5.7.1 Rejected by school`；
> 2. **账号批量销号**：学生升学、转学或毕业后，学校邮箱账号会被批量删除注销，立刻导致 `550 NoSuchUser` 永久硬退信。

**拦截策略规范（`isBlockedRiskyEmail`）**：
- **已知拒收学校域名**：`kcpupils.org`、`moe-dl.edu.my`、`hkstudent.ycis.com` 等。
- **学生子域特征正则**：
  ```ts
  /(?:^|\.)(?:pupils?|students?|smail|elearn)\./i
  ```
  涵盖香港、台湾、马来西亚等中小学分配的教育系统域名（如 `apps.ntpc.edu.tw`、`stu.mail.*`、`smail.*`）。
- **保护正常高校**：普通综合性大学（如 `nyu.edu`、`*.edu.cn` 等）不应误伤。
- **虚假/废弃短数字 QQ 邮箱**：纯数字且长度 $\le 7$ 位的 QQ 号（多为早期废弃死号或乱填）。

---

## 阶段二：Resend 订阅中心集成与退订闭环（Audience & Unsubscribe）

### 1. 受众全量同步至 Resend Contacts
为便于在 Resend 官方控制台（Audiences / Contacts）直观管理用户生命周期，业务库中的合格受众应定期批量同步入库：
- **API 接口**：`POST https://api.resend.com/contacts`
- **参数规范**：`{ email, first_name, unsubscribed: false }`
- **流控策略**：每个请求间隔 100~120ms，避免触发 API 频控；已存在的联系人容错跳过（409/422）。

### 2. 基于游标（Cursor）的全量分页退订拉取
> [!IMPORTANT]
> **Resend Contacts API 默认每页仅返回 20 条记录**！  
> 若联系人总数超过 20，仅拉取首页会导致历史退订联系人被漏掉，造成违规发信！

**全量分页拉取实现模式**：
```ts
let url = 'https://api.resend.com/contacts?limit=100';
while (url) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${apiKey}` } });
  const { data } = await res.json();
  for (const contact of data || []) {
    if (contact.unsubscribed && contact.email) {
      suppressedSet.add(contact.email.trim().toLowerCase());
    }
  }
  // 若不足 100 条说明已到末尾；否则取最后一条 ID 作为 after 游标
  if (!data || data.length < 100) break;
  const lastId = data[data.length - 1]?.id;
  url = lastId ? `https://api.resend.com/contacts?limit=100&after=${lastId}` : null;
}
```

### 3. 双保险退订持久化
退订采用「**发信平台状态 + 本地受控文件**」双保险：
1. **Resend Contacts 状态**：调用 `PATCH /contacts/{email}` 将 `unsubscribed` 设为 `true`；
2. **Git 受控持久化文件**：在仓库中维护 `data/email-campaign-unsubscribed.txt`，无论本地缓存或 `.tmp` 目录如何清理，退订黑名单永久有效。

### 4. RFC 8058 标准一键退订与 Web 端点闭环（重要规范！）
> [!IMPORTANT]
> **API 发信（`POST /emails`）不会自动插入退订链接！必须全链路自建退订入口**：
> 1. **严禁硬编码“回复邮件退订”**：所有语言的模板页脚必须通过专属函数渲染超链接 `<a href="${unsubscribeUrl}">`，纯文本同步提供链接；
> 2. **发信必须注入 RFC 8058 Header**：
>    ```ts
>    headers: {
>      'List-Unsubscribe': `<${unsubscribeUrl}>`,
>      'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
>    }
>    ```
>    使 Gmail、Apple Mail、QQ 邮箱等在邮件顶部原生展示【退订】按钮；
> 3. **安全防篡改 Token**：`unsubscribeUrl` 参数必须附带基于 Web Crypto / HMAC-SHA256 的防篡改签名 token（`verifyUnsubscribeToken`），杜绝恶意批量退订他人；
> 4. **Web 路由自动联动 Resend**：服务端端点（如 `/api/email/unsubscribe`）处理 GET 请求（展示友好确认页）与 POST 请求（客户端一键静默退订），接收到后立刻调用 `PATCH /contacts/{email}` 将 Resend Contacts 的 `unsubscribed` 置为 `true`，完成订阅中心权威闭环。

---

## 阶段三：分批规划与网络鲁棒性（Batch Planning）

1. **基于全局合格受众固定划分批次**：
   - 严禁对剩余待发名单动态 `slice`（会导致发完上一批后批次序号偏移跳发漏人）；
   - 批次序号基于初始合格受众（如总数 440 人按 40 人/批划分为 11 批）固定不变，每批独立校验内部已发状态。
2. **长循环 API 网络重试（防止超时崩溃）**：
   - 单封邮件发送支持指数退避重试（重试 3 次，间隔 1s, 2s, 3s）；
   - 打印进度日志（如 `[count/total] ... OK (id)`），避免无响应假死。

---

## 阶段四：Seed 白名单预发验收（Seed Pre-flight）

执行批量发送前，通过 `--test <email>` 进行真实客户端验证：
- [ ] 邮件主题与正文变量替换正常，无 raw template 泄漏；
- [ ] 多语言探测（中、英、日、西、葡、法、泰）准确匹配，无法确定时优雅兜底英文；
- [ ] HTML 在桌面端（Gmail / Outlook / Apple Mail）与手机端排版自适应无崩坏；
- [ ] 包含明显的退订提示与联系方式。

---

## 阶段五：批次投递与防退信熔断（Execution & Circuit Breaker）

每次执行特定批次时：
1. **二次确认门禁**：必须传入匹配的 `--confirm <campaign>/<batch>` 字符串，防止手滑误发。
2. **实时连续失败熔断**：若连续失败达到 **3 次**，立即中止。
3. **批次累计失败率熔断**：本批次失败率若超过 **5%**（基准人数 $\ge 2$），触发熔断紧急停止发信，保护域名信誉。
4. **断点自动记录**：发送成功即刻保存 sentAt 状态，重跑幂等不重复投递。

---

## 常用运维命令对照表

| 操作 | 典型命令 |
| :--- | :--- |
| **受众审计与批次规划** | `pnpm email:campaign --dry-run` |
| **同步受众到 Resend 订阅中心** | `pnpm email:campaign --sync-contacts` |
| **一键退订指定邮箱** | `pnpm email:campaign --unsubscribe 'user@example.com'` |
| **单邮箱 Seed 测试发信** | `pnpm email:campaign --test 'meathill@gmail.com' --locale zh-CN` |
| **执行指定批次发送** | `pnpm email:campaign --batch 1 --confirm 'art-qr/1'` |
| **强制重新从数据库拉取受众** | `pnpm email:campaign --refresh-users --dry-run` |
