---
name: email-campaign
description: >
  全链路营销与产品动态邮件发送运维技能：覆盖目标受众清洗（高危中小学学生域名与假号拦截、Private Relay 与测试域过滤）、
  每日配额与事务缓冲精算、Seed 白名单预发验收、滚动批次投递、Resend 瞬态网络重试、退信与压制根因诊断，以及退信邮箱自动治理。
  当用户提到“发送营销邮件”、“发邮件活动”、“邮件营销”、“邮件分批”、“email campaign”、“newsletter campaign”、“活动邮件”、“检查退信”、“邮件拒收”时触发。
---

# Email Campaign Skill

本技能固化了从受众清洗、白名单验证、分批发送到退信诊断治理的**全链路营销邮件工程实践**。
核心目标是：**在严守发信服务商配额与反垃圾信誉的前提下，安全、稳健地完成大规模邮件投递，坚决杜绝因高危邮箱导致域名进入黑名单**。

---

## 核心准则与安全红线（Prerequisites & Hard Rules）

1. **域名信誉高于一切**：
   - 近 15 天退信率（Bounce Rate）严格红线为 **3.5% ~ 4.0%**。一旦当前退信率或本批保守估算越线，必须**立刻熔断停止发送**。
2. **严守每日配额精算**：
   - 每日计划消耗必须留足缓冲：
     $$\text{当日已发} + \text{日常业务/事务邮件预留} + \text{当前批次人数} + \text{安全缓冲(20)} \le \text{发信商每日限额}$$
   - 例如 Resend 免费额度每日 100 封，扣除已用 19、每日一签 19 与安全缓冲 20，单批最多允许 40 封。
3. **严禁直接发真实用户（Seed 预发闭环）**：
   - 第 0 批必须由团队核心白名单邮箱进行真实收信验收。
   - 真实用户批次一旦启动，严禁再次复用滚动投递 Segment 重试 Seed。
4. **异常邮箱即刻治理（零容忍）**：
   - 任何发生退信（Hard Bounce / Transient 550）或被服务商压制（Suppressed）的邮箱，必须**立刻在发信平台打标退订（`unsubscribed: true`）**并从后续批次剔除，防止重复消耗配额与累积投诉。

---

## 阶段一：受众清洗与风险特征阻断（Audience Hygiene）

### 1. 基础合规过滤
- 剔除邮箱未验证用户（`emailConfirmedAt` 为空）。
- 剔除已注销账户（`deletedAt` 存在）或封禁中用户（`bannedUntil > now`）。
- 剔除活动截止时间之后注册的用户（防止动态受众干扰批次规划）。
- 排除苹果匿名中继邮箱（`privaterelay.appleid.com`、`private.icloud.com`，防退信且打开率极低）。
- 排除保留测试域名（`example.com`、`*.test` 等）。

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

## 阶段二：分批规划与网络鲁棒性（Batch Planning）

1. **梯形批次规模**：
   - 第 0 批（Seed）：仅白名单测试邮箱（通常 2~5 人）；
   - 第 1 批（首批真实用户）：小批量试水，建议 **20 ~ 40 人**；
   - 第 2 批起：若第 1 批投递健康（退信率正常），可平稳提高到 **50 人/批**；
   - 第 4 批及退信风险升高时：自动降级回 **20 人/批** 并执行 DNS 质量复检。
2. **长循环 API 网络重试（防止超时崩溃）**：
   - 同步几百位联系人属性时，单个 HTTP 请求可能偶发超时（如 Resend `Unable to fetch data`）；
   - 必须实现指数退避重试（重试 3 次，间隔 1s, 2s, 3s）；
   - 打印进度日志（如 `[count/total]`），避免无响应假死。
3. **单一滚动 Segment 机制**：
   - 发信平台（如 Resend）通常限制自定义 Segment 数量；
   - 统一使用一个 `delivery-segment`，每次发送前全量覆盖该 Segment 的成员，严禁按批次创建无数垃圾 Segment。

---

## 阶段三：Seed 白名单预发验收（Seed Pre-flight）

执行第 0 批发送前，检查清单：
- [ ] 邮件主题与正文变量替换正常，无 raw template 泄漏；
- [ ] HTML 在桌面端（Gmail / Outlook / Apple Mail）与手机端排版自适应无崩坏；
- [ ] 退订链接（Unsubscribe）与偏好设置可正常跳转；
- [ ] 发信域名通过 SPF、DKIM、DMARC 验证；
- [ ] 验收完成后，原 Seed Broadcast 状态确认标记为 `sent`。

---

## 阶段四：批次投递与动态名单核对（Execution）

每次执行特定批次（如 `--batch 1`）时：
1. **二次确认门禁**：必须传入匹配的 `--confirm <campaign>/<batch>` 字符串，防止手滑误发。
2. **发送前动态核对（Dynamic Reconciliation）**：
   - 重新拉取最新受众，核对该批次成员中是否有人在最近退订、被标记不健康或命中风险黑名单；
   - 自动过滤不合格成员，保证进入滚动 Segment 的都是健康合格的联系人。
3. **退信率熔断校验**：
   - 调用发信 API 检查近 15 天健康数据，计算：
     $$\text{保守估算退信率} = \frac{\text{历史退信数} + \min(\text{本批人数}, 2)}{\text{历史总发信数} + \text{本批人数}}$$
   - 若估算越过 4%，直接抛错终止发送。

---

## 阶段五：退信根因诊断与即刻治理（Diagnosis & Remediation SOP）

发送完成后，若发信平台出现拒收，按以下 SOP 排查处理：

### 1. 抓取邮件详情与错误事件
调用邮件列表 API 抓取 `last_event` 为异常的记录，分类诊断：
- **`bounced` (Permanent / Hard Bounce)**：
  - 典型日志：`550 NoSuchUser` / `The email account does not exist`；
  - 处置：收件人已销号，**必须永久退订**。
- **`bounced` (Transient / ContentRejected)**：
  - 典型日志：`550-5.7.1 Rejected by school` / `Policy Rejection`；
  - 处置：受众域名的安全策略拒绝外信，**必须永久退订**。
- **`suppressed` (平台压制拦截)**：
  - 典型日志：邮件直接被服务商拦截，未实际外发；
  - 原因：该邮箱在全局黑名单中（历史退信/投诉过），白白消耗额度；
  - 处置：**必须立即退订**。

### 2. 即刻治理脚本流程
执行治理逻辑（建议自动化脚本实现）：
```ts
// 1. 设置联系人为退订状态
await resend.contacts.update({
  id: contactId,
  unsubscribed: true,
  properties: { [campaignBatchProperty]: '' },
});
// 2. 从当前滚动投递 Segment 移除
await resend.contacts.segments.remove({
  contactId,
  segmentId: deliverySegmentId,
});
```

### 3. 特征沉淀
将引发退信的域名或模式扩充到 `isBlockedRiskyEmail` 过滤规则中，确保后续活动从源头彻底切断该类邮箱。

---

## 常用运维命令对照表

| 操作 | 典型命令 |
| :--- | :--- |
| **受众审计** | `pnpm email:audience:audit` |
| **批次规划与属性同步** | `pnpm email:campaign:prepare --campaign <key>` |
| **第 0 批 Seed 发送** | `pnpm email:campaign:send -- --campaign <key> --batch 0 --confirm <key>/0` |
| **Seed 失败轮换重试** | `pnpm email:campaign:send -- --campaign <key> --batch 0 --retry 1 --confirm <key>/0/retry-1` |
| **正式批次发送** | `pnpm email:campaign:send -- --campaign <key> --batch 1 --confirm <key>` |
| **高风险质量重排** | `pnpm email:campaign:replan --campaign <key> --after-batch 3` |
