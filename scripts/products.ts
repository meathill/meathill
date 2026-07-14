import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export type FooterStatus = 'planned' | 'review-required' | 'excluded';
export type Ownership = 'owned' | 'partner';
export type PagesMode = 'snapshot' | 'partial-static' | 'landing-only' | 'not-applicable';
export type PagesStatus = 'not-enabled' | 'eligibility-unverified' | 'not-planned';
export type RepositoryVisibility = 'public' | 'private';

export interface FooterGroup {
  id: string;
  name: string;
  maxDirectLinks: number;
  directoryUrl: string;
}

export interface Repository {
  slug: string;
  visibility: RepositoryVisibility;
  defaultBranch: string;
  lastActivityOn: string;
  pagesStatus: PagesStatus;
}

export interface Site {
  id: string;
  name: string;
  url: string;
  summary: string;
  repository: string;
  ownership: Ownership;
  footer: {
    status: FooterStatus;
    groups: string[];
    priority: number;
  };
  pages: {
    url: string;
    mode: PagesMode;
  };
  health: {
    checkedOn: string;
    status: 'ok' | 'error';
    httpStatus?: number;
    error?: string;
  };
}

export interface Inventory {
  version: number;
  updatedOn: string;
  directory: {
    url: string;
    title: string;
    description: string;
    siteName: string;
    language: string;
    locale: string;
    imageUrl: string;
    imageAlt: string;
  };
  recency: {
    days: number;
    since: string;
    coreRepositoryExceptions: string[];
  };
  footerGroups: FooterGroup[];
  repositories: Repository[];
  sites: Site[];
  excludedRepositories: Array<{
    repository: string;
    lastActivityOn: string;
    reason: string;
  }>;
}

export const ROOT_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const PRODUCTS_PATH = resolve(ROOT_DIR, 'products.json');
const PRODUCTS_DOCUMENT_PATH = resolve(ROOT_DIR, 'PRODUCTS.md');
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const REPOSITORY_PATTERN = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;

export function assertCondition(condition: boolean, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isHttpsUrl(value: string): boolean {
  try {
    return new URL(value).protocol === 'https:';
  } catch {
    return false;
  }
}

function assertBasicShape(value: unknown): asserts value is Inventory {
  assertCondition(isRecord(value), 'products.json 顶层必须是对象');
  assertCondition(Array.isArray(value.footerGroups), 'footerGroups 必须是数组');
  assertCondition(Array.isArray(value.repositories), 'repositories 必须是数组');
  assertCondition(Array.isArray(value.sites), 'sites 必须是数组');
  assertCondition(Array.isArray(value.excludedRepositories), 'excludedRepositories 必须是数组');
  assertCondition(isRecord(value.recency), 'recency 必须是对象');
  assertCondition(isRecord(value.directory), 'directory 必须是对象');
}

function validateInventory(inventory: Inventory): void {
  assertCondition(inventory.version === 1, '仅支持 version=1');
  assertCondition(ISO_DATE_PATTERN.test(inventory.updatedOn), 'updatedOn 必须是 YYYY-MM-DD');
  assertCondition(isHttpsUrl(inventory.directory.url), 'directory.url 必须使用 HTTPS');
  assertCondition(isHttpsUrl(inventory.directory.imageUrl), 'directory.imageUrl 必须使用 HTTPS');
  assertCondition(inventory.directory.title.length >= 20, 'directory.title 信息不足');
  assertCondition(inventory.directory.description.length >= 40, 'directory.description 信息不足');
  assertCondition(inventory.directory.siteName.length > 0, 'directory.siteName 不能为空');
  assertCondition(inventory.directory.language.length > 0, 'directory.language 不能为空');
  assertCondition(inventory.directory.locale.length > 0, 'directory.locale 不能为空');
  assertCondition(inventory.directory.imageAlt.length > 0, 'directory.imageAlt 不能为空');
  assertCondition(ISO_DATE_PATTERN.test(inventory.recency.since), 'recency.since 必须是 YYYY-MM-DD');
  assertCondition(inventory.recency.days > 0, 'recency.days 必须大于 0');

  const footerGroupIds = new Set<string>();
  for (const group of inventory.footerGroups) {
    assertCondition(ID_PATTERN.test(group.id), `footer group id 不合法: ${group.id}`);
    assertCondition(!footerGroupIds.has(group.id), `footer group id 重复: ${group.id}`);
    assertCondition(group.maxDirectLinks > 0, `${group.id} 的 maxDirectLinks 必须大于 0`);
    assertCondition(isHttpsUrl(group.directoryUrl), `${group.id} 的 directoryUrl 必须使用 HTTPS`);
    footerGroupIds.add(group.id);
  }

  const repositories = new Map<string, Repository>();
  for (const repository of inventory.repositories) {
    assertCondition(REPOSITORY_PATTERN.test(repository.slug), `repository slug 不合法: ${repository.slug}`);
    assertCondition(!repositories.has(repository.slug), `repository 重复: ${repository.slug}`);
    assertCondition(ISO_DATE_PATTERN.test(repository.lastActivityOn), `${repository.slug} 的活动日期不合法`);
    assertCondition(repository.defaultBranch.length > 0, `${repository.slug} 缺少默认分支`);
    if (repository.visibility === 'public') {
      assertCondition(
        repository.pagesStatus !== 'eligibility-unverified',
        `${repository.slug} 是公开仓库，不应标记 Pages 资格待确认`,
      );
    }
    if (repository.lastActivityOn < inventory.recency.since) {
      assertCondition(
        inventory.recency.coreRepositoryExceptions.includes(repository.slug),
        `${repository.slug} 超出近期窗口，必须列入 coreRepositoryExceptions`,
      );
    }
    repositories.set(repository.slug, repository);
  }

  const siteIds = new Set<string>();
  const siteUrls = new Set<string>();
  const pagesUrls = new Set<string>();
  for (const site of inventory.sites) {
    assertCondition(ID_PATTERN.test(site.id), `site id 不合法: ${site.id}`);
    assertCondition(!siteIds.has(site.id), `site id 重复: ${site.id}`);
    assertCondition(!siteUrls.has(site.url), `site url 重复: ${site.url}`);
    assertCondition(isHttpsUrl(site.url), `${site.id} 的主站必须使用 HTTPS`);
    assertCondition(site.summary.length >= 15 && site.summary.length <= 100, `${site.id} 的 summary 应为 15 至 100 字`);
    assertCondition(repositories.has(site.repository), `${site.id} 引用了未知仓库 ${site.repository}`);
    assertCondition(isHttpsUrl(site.pages.url), `${site.id} 的 Pages URL 必须使用 HTTPS`);
    assertCondition(!pagesUrls.has(site.pages.url), `Pages URL 重复: ${site.pages.url}`);
    assertCondition(ISO_DATE_PATTERN.test(site.health.checkedOn), `${site.id} 的健康检查日期不合法`);

    const [owner, repositoryName] = site.repository.split('/');
    const expectedPagesPrefix = `https://${owner.toLowerCase()}.github.io/${repositoryName}/`;
    assertCondition(
      site.pages.url.startsWith(expectedPagesPrefix),
      `${site.id} 的 Pages URL 应以 ${expectedPagesPrefix} 开头`,
    );

    if (site.footer.status === 'planned') {
      assertCondition(site.footer.groups.length > 0, `${site.id} 计划接入 footer，但未指定 group`);
    } else {
      assertCondition(site.footer.groups.length === 0, `${site.id} 尚未获准接入 footer，不应指定 group`);
    }
    for (const groupId of site.footer.groups) {
      assertCondition(footerGroupIds.has(groupId), `${site.id} 引用了未知 footer group ${groupId}`);
    }
    assertCondition(site.footer.priority >= 0, `${site.id} 的 footer priority 不能为负数`);

    const repository = repositories.get(site.repository);
    assertCondition(repository !== undefined, `${site.id} 的仓库不存在`);
    if (site.pages.mode === 'not-applicable') {
      assertCondition(repository.pagesStatus === 'not-planned', `${site.id} 不适合 Pages，但仓库状态不是 not-planned`);
    } else {
      assertCondition(repository.pagesStatus !== 'not-planned', `${site.id} 计划 Pages DR，但仓库状态是 not-planned`);
    }

    if (site.health.status === 'ok') {
      assertCondition(
        typeof site.health.httpStatus === 'number' && site.health.httpStatus >= 200 && site.health.httpStatus < 400,
        `${site.id} 健康检查为 ok，但缺少有效 HTTP 状态码`,
      );
    } else {
      assertCondition(typeof site.health.error === 'string' && site.health.error.length > 0, `${site.id} 缺少错误说明`);
    }

    siteIds.add(site.id);
    siteUrls.add(site.url);
    pagesUrls.add(site.pages.url);
  }

  for (const repository of inventory.excludedRepositories) {
    assertCondition(REPOSITORY_PATTERN.test(repository.repository), `排除的 repository slug 不合法: ${repository.repository}`);
    assertCondition(ISO_DATE_PATTERN.test(repository.lastActivityOn), `${repository.repository} 的活动日期不合法`);
    assertCondition(repository.reason.length > 0, `${repository.repository} 缺少排除原因`);
    assertCondition(!repositories.has(repository.repository), `${repository.repository} 不能同时被纳入和排除`);
  }
}

function formatRepository(repository: Repository): string {
  if (repository.visibility === 'public') {
    return `[${repository.slug}](https://github.com/${repository.slug})`;
  }
  return `\`${repository.slug}\`（私有）`;
}

function formatFooter(site: Site): string {
  const labels: Record<FooterStatus, string> = {
    planned: `待接入：${site.footer.groups.join('、')}`,
    'review-required': '需与合作方确认',
    excluded: '不接入',
  };
  return labels[site.footer.status];
}

function formatPages(site: Site, repository: Repository): string {
  if (repository.pagesStatus === 'not-planned') {
    return '不适用';
  }
  const status = repository.pagesStatus === 'not-enabled' ? '未启用' : '账号资格待确认';
  const modeLabels: Record<PagesMode, string> = {
    snapshot: '只读快照',
    'partial-static': '部分静态可用',
    'landing-only': '仅降级页',
    'not-applicable': '不适用',
  };
  return `${status}，${modeLabels[site.pages.mode]}<br>\`${site.pages.url}\``;
}

function formatHealth(site: Site): string {
  if (site.health.status === 'ok') {
    return `${site.health.httpStatus}（${site.health.checkedOn}）`;
  }
  return `异常：${site.health.error}（${site.health.checkedOn}）`;
}

function renderSiteTable(sites: Site[], repositories: Map<string, Repository>): string[] {
  const lines = [
    '| 产品 / 网站 | Repo | 最近开发 | Footer | GitHub Pages DR | 主站检查 |',
    '| --- | --- | --- | --- | --- | --- |',
  ];
  for (const site of sites) {
    const repository = repositories.get(site.repository);
    assertCondition(repository !== undefined, `${site.id} 的仓库不存在`);
    lines.push(
      `| [${site.name}](${site.url}) | ${formatRepository(repository)} | ${repository.lastActivityOn} | ${formatFooter(site)} | ${formatPages(site, repository)} | ${formatHealth(site)} |`,
    );
  }
  return lines;
}

function renderMarkdown(inventory: Inventory): string {
  const repositories = new Map(inventory.repositories.map((repository) => [repository.slug, repository]));
  const sortedSites = [...inventory.sites].sort((first, second) => {
    const firstActivity = repositories.get(first.repository)?.lastActivityOn ?? '';
    const secondActivity = repositories.get(second.repository)?.lastActivityOn ?? '';
    return secondActivity.localeCompare(firstActivity) || second.footer.priority - first.footer.priority;
  });
  const ownedSites = sortedSites.filter((site) => site.ownership === 'owned');
  const partnerSites = sortedSites.filter((site) => site.ownership === 'partner');

  return [
    '# 产品 Repo ↔ 网站清单',
    '',
    `更新时间：${inventory.updatedOn}。近期窗口：${inventory.recency.since} 至 ${inventory.updatedOn}（${inventory.recency.days} 天）。`,
    '',
    '`products.json` 是单一数据源；本文件由 `pnpm run format` 生成，请勿手动维护表格。',
    '',
    '## 自有产品',
    '',
    ...renderSiteTable(ownedSites, repositories),
    '',
    '## 合作产品',
    '',
    '合作方域名不自动加入 Meathill footer 互链，接入前需要确认品牌与 SEO 归属。',
    '',
    ...renderSiteTable(partnerSites, repositories),
    '',
    '## Footer 约定',
    '',
    '- 每个站最多展示所属分组中 6 个直接链接，并排除当前站。',
    '- 链接过多时按 `priority` 选取，其余统一进入产品目录，避免 footer 变成链接农场。',
    '- 同一代码库的垂直站只在品牌网络内互链，不默认进入全部 Meathill 产品站。',
    '- 合作产品必须先确认品牌、SEO 和客户授权，再决定是否互链。',
    '',
    '## GitHub Pages DR 约定',
    '',
    '- GitHub Pages 只发布静态文件。`landing-only` 仅提供状态说明、核心文案和入口；登录、API、数据库、上传、支付等动态能力不属于恢复范围。',
    '- `snapshot` 发布可浏览的只读内容快照；`partial-static` 保留浏览器端可独立运行的功能。',
    '- 默认保留 `<owner>.github.io/<repo>/` 地址，不给 Pages 配主站自定义域名，避免与生产 DNS 冲突。',
    '- 私有仓库需要先确认 GitHub 账号套餐支持 Pages；即使仓库私有，Pages 站点本身仍按公开内容处理。',
    '',
    '## 本轮未纳入',
    '',
    '| Repo | 最近开发 | 原因 |',
    '| --- | --- | --- |',
    ...inventory.excludedRepositories
      .sort((first, second) => second.lastActivityOn.localeCompare(first.lastActivityOn))
      .map((repository) => `| \`${repository.repository}\` | ${repository.lastActivityOn} | ${repository.reason} |`),
    '',
  ].join('\n');
}

export async function loadInventory(): Promise<Inventory> {
  const raw = await readFile(PRODUCTS_PATH, 'utf8');
  const parsed: unknown = JSON.parse(raw);
  assertBasicShape(parsed);
  validateInventory(parsed);
  return parsed;
}

async function checkGeneratedDocument(expected: string): Promise<void> {
  const current = await readFile(PRODUCTS_DOCUMENT_PATH, 'utf8');
  assertCondition(current === expected, 'PRODUCTS.md 与 products.json 不一致，请运行 pnpm run format');
}

async function main(): Promise<void> {
  const command = process.argv[2] ?? 'check';
  assertCondition(command === 'check' || command === 'generate', `未知命令: ${command}`);
  const inventory = await loadInventory();
  const markdown = renderMarkdown(inventory);

  if (command === 'generate') {
    await writeFile(PRODUCTS_DOCUMENT_PATH, markdown, 'utf8');
    console.log(`已生成 ${PRODUCTS_DOCUMENT_PATH}`);
    return;
  }

  await checkGeneratedDocument(markdown);
  console.log(`产品清单校验通过：${inventory.repositories.length} 个仓库，${inventory.sites.length} 个站点`);
}

const isDirectRun = process.argv[1] !== undefined && resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isDirectRun) {
  await main();
}
