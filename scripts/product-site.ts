import { copyFile, mkdir, rm, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import {
  PRODUCTS_PATH,
  ROOT_DIR,
  assertCondition,
  loadInventory,
  type Inventory,
  type Repository,
  type Site,
} from './products.ts';

const DIST_DIR = resolve(ROOT_DIR, 'dist');
const STYLE_PATH = resolve(ROOT_DIR, 'pages/styles.css');
const HERO_IMAGE_PATH = resolve(ROOT_DIR, 'assets/profile-hero.png');

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function escapeXml(value: string): string {
  return escapeHtml(value);
}

function getRepositoryMap(inventory: Inventory): Map<string, Repository> {
  return new Map(inventory.repositories.map((repository) => [repository.slug, repository]));
}

function sortSites(sites: Site[], repositories: Map<string, Repository>): Site[] {
  return [...sites].sort((first, second) => {
    const priorityDifference = second.footer.priority - first.footer.priority;
    if (priorityDifference !== 0) {
      return priorityDifference;
    }
    const firstActivity = repositories.get(first.repository)?.lastActivityOn ?? '';
    const secondActivity = repositories.get(second.repository)?.lastActivityOn ?? '';
    return secondActivity.localeCompare(firstActivity) || first.name.localeCompare(second.name);
  });
}

function renderSiteList(sites: Site[], repositories: Map<string, Repository>): string {
  return sites
    .map((site, index) => {
      const repository = repositories.get(site.repository);
      assertCondition(repository !== undefined, `${site.id} 的仓库不存在`);
      const sourceLink =
        repository.visibility === 'public'
          ? `<a href="https://github.com/${escapeHtml(repository.slug)}" rel="external">查看源码</a>`
          : '';
      const health =
        site.health.status === 'error'
          ? '<span class="site-status" role="status">主站连接异常</span>'
          : '';
      return `
        <li class="product-row">
          <span class="product-index" aria-hidden="true">${String(index + 1).padStart(2, '0')}</span>
          <div class="product-copy">
            <h3><a href="${escapeHtml(site.url)}" rel="external">${escapeHtml(site.name)}</a></h3>
            <p>${escapeHtml(site.summary)}</p>
            <span class="product-domain">${escapeHtml(new URL(site.url).hostname)}</span>
          </div>
          <div class="product-actions">
            ${health}
            <a class="primary-link" href="${escapeHtml(site.url)}" rel="external">打开网站</a>
            ${sourceLink}
          </div>
        </li>`;
    })
    .join('');
}

function renderStructuredData(inventory: Inventory, visibleSites: Site[]): string {
  const directory = inventory.directory;
  const structuredData = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Person',
        '@id': `${directory.url}#person`,
        name: 'Meathill',
        alternateName: '肉山',
        url: 'https://meathill.com',
        sameAs: ['https://github.com/meathill', 'https://youtube.com/@meathill', 'https://x.com/meathill1'],
      },
      {
        '@type': 'WebSite',
        '@id': `${directory.url}#website`,
        url: directory.url,
        name: directory.siteName,
        description: directory.description,
        inLanguage: directory.language,
        author: { '@id': `${directory.url}#person` },
      },
      {
        '@type': 'CollectionPage',
        '@id': `${directory.url}#collection`,
        url: directory.url,
        name: directory.title,
        description: directory.description,
        isPartOf: { '@id': `${directory.url}#website` },
        mainEntity: {
          '@type': 'ItemList',
          numberOfItems: visibleSites.length,
          itemListElement: visibleSites.map((site, index) => ({
            '@type': 'ListItem',
            position: index + 1,
            item: {
              '@type': 'WebSite',
              name: site.name,
              url: site.url,
              description: site.summary,
            },
          })),
        },
      },
    ],
  };
  return JSON.stringify(structuredData).replaceAll('<', '\\u003c');
}

function renderIndex(inventory: Inventory): string {
  const repositories = getRepositoryMap(inventory);
  const ownedSites = sortSites(
    inventory.sites.filter((site) => site.ownership === 'owned' && site.footer.status !== 'excluded'),
    repositories,
  );
  const partnerSites = sortSites(
    inventory.sites.filter((site) => site.ownership === 'partner'),
    repositories,
  );
  const serviceSites = sortSites(
    inventory.sites.filter((site) => site.footer.status === 'excluded'),
    repositories,
  );
  const visibleSites = [...ownedSites, ...partnerSites, ...serviceSites];
  const directory = inventory.directory;

  return `<!doctype html>
<html lang="${escapeHtml(directory.language)}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${escapeHtml(directory.title)}</title>
    <meta name="description" content="${escapeHtml(directory.description)}">
    <meta name="author" content="Meathill">
    <meta name="robots" content="index, follow, max-image-preview:large">
    <meta name="theme-color" content="#f0f2ed">
    <link rel="canonical" href="${escapeHtml(directory.url)}">
    <link rel="icon" type="image/png" href="./assets/profile-hero.png">
    <link rel="alternate" type="application/json" href="./products.json" title="Product inventory">
    <link rel="stylesheet" href="./styles.css">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="${escapeHtml(directory.siteName)}">
    <meta property="og:locale" content="${escapeHtml(directory.locale)}">
    <meta property="og:title" content="${escapeHtml(directory.title)}">
    <meta property="og:description" content="${escapeHtml(directory.description)}">
    <meta property="og:url" content="${escapeHtml(directory.url)}">
    <meta property="og:image" content="${escapeHtml(directory.imageUrl)}">
    <meta property="og:image:width" content="1536">
    <meta property="og:image:height" content="512">
    <meta property="og:image:alt" content="${escapeHtml(directory.imageAlt)}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:creator" content="@meathill1">
    <meta name="twitter:title" content="${escapeHtml(directory.title)}">
    <meta name="twitter:description" content="${escapeHtml(directory.description)}">
    <meta name="twitter:image" content="${escapeHtml(directory.imageUrl)}">
    <meta name="twitter:image:alt" content="${escapeHtml(directory.imageAlt)}">
    <script type="application/ld+json">${renderStructuredData(inventory, visibleSites)}</script>
  </head>
  <body>
    <header class="site-header">
      <a class="brand" href="${escapeHtml(directory.url)}">MEATHILL</a>
      <nav aria-label="主要导航">
        <a href="https://meathill.com">个人网站</a>
        <a href="https://github.com/meathill">GitHub</a>
        <a href="./products.json">JSON</a>
      </nav>
    </header>
    <main>
      <section class="intro" aria-labelledby="page-title">
        <p class="eyebrow">Product directory · 更新于 ${escapeHtml(inventory.updatedOn)}</p>
        <h1 id="page-title">我开发和维护的产品，都在这里。</h1>
        <p class="lede">从 AI 工具、创作产品到独立站服务。这份目录提供每个产品的当前入口，也作为主站不可用时的备用索引。</p>
        <div class="intro-actions">
          <a class="button" href="https://meathill.com">访问个人网站</a>
          <a href="https://github.com/meathill">查看公开源码</a>
        </div>
      </section>
      <figure class="hero-figure">
        <img src="./assets/profile-hero.png" width="1536" height="512" alt="${escapeHtml(directory.imageAlt)}">
      </figure>
      <section class="directory-section" aria-labelledby="owned-products">
        <div class="section-heading">
          <p>Independent products</p>
          <h2 id="owned-products">自有产品</h2>
          <span>${ownedSites.length} 个持续开发中的网站</span>
        </div>
        <ol class="product-list">${renderSiteList(ownedSites, repositories)}</ol>
      </section>
      <section class="directory-section partner-section" aria-labelledby="partner-products">
        <div class="section-heading">
          <p>Collaborations</p>
          <h2 id="partner-products">合作产品</h2>
          <span>与伙伴共同完成或持续维护</span>
        </div>
        <ol class="product-list">${renderSiteList(partnerSites, repositories)}</ol>
      </section>
      <section class="directory-section service-section" aria-labelledby="services">
        <div class="section-heading">
          <p>Infrastructure</p>
          <h2 id="services">公共服务</h2>
          <span>为其他产品提供能力的在线服务</span>
        </div>
        <ol class="product-list">${renderSiteList(serviceSites, repositories)}</ol>
      </section>
    </main>
    <footer class="site-footer">
      <p>由 Meathill 持续维护。不加载统计脚本，不设置追踪 Cookie。</p>
      <div><a href="mailto:meathill@gmail.com">联系我</a><a href="./products.json">机器可读清单</a></div>
    </footer>
  </body>
</html>`;
}

function renderNotFound(inventory: Inventory): string {
  return `<!doctype html>
<html lang="${escapeHtml(inventory.directory.language)}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>页面不存在 | ${escapeHtml(inventory.directory.siteName)}</title>
    <meta name="description" content="这个页面不存在，请返回 Meathill 产品目录继续浏览。">
    <meta name="robots" content="noindex, follow">
    <link rel="icon" type="image/png" href="./assets/profile-hero.png">
    <link rel="stylesheet" href="./styles.css">
  </head>
  <body class="not-found-page">
    <main class="not-found">
      <p class="eyebrow">Page not found</p>
      <h1>这里没有你要找的页面。</h1>
      <p>链接可能已经变化，也可能只是多输入了一个字符。</p>
      <a class="button" href="./">返回产品目录</a>
    </main>
  </body>
</html>`;
}

function renderRobots(inventory: Inventory): string {
  return `User-agent: *\nAllow: /\n\nSitemap: ${inventory.directory.url}sitemap.xml\n`;
}

function renderSitemap(inventory: Inventory): string {
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>${escapeXml(inventory.directory.url)}</loc>
    <lastmod>${inventory.updatedOn}</lastmod>
  </url>
</urlset>
`;
}

function validateOutput(inventory: Inventory, indexHtml: string, notFoundHtml: string): void {
  const requiredSeo = [
    '<meta name="description"',
    '<link rel="canonical"',
    '<meta property="og:title"',
    '<meta property="og:description"',
    '<meta property="og:image"',
    '<meta name="twitter:card"',
    '<script type="application/ld+json">',
  ];
  for (const fragment of requiredSeo) {
    assertCondition(indexHtml.includes(fragment), `首页缺少 SEO 信息: ${fragment}`);
  }
  for (const site of inventory.sites) {
    assertCondition(indexHtml.includes(`href="${escapeHtml(site.url)}"`), `首页缺少站点入口: ${site.id}`);
    assertCondition(indexHtml.includes(escapeHtml(site.summary)), `首页缺少站点说明: ${site.id}`);
  }
  assertCondition(!/(TODO|FIXME|Lorem|placeholder|coming soon)/i.test(indexHtml), '首页包含占位文案');
  assertCondition(notFoundHtml.includes('noindex, follow'), '404 页面必须 noindex');
  assertCondition(notFoundHtml.includes('返回产品目录'), '404 页面缺少返回入口');
}

async function buildSite(inventory: Inventory): Promise<void> {
  const indexHtml = renderIndex(inventory);
  const notFoundHtml = renderNotFound(inventory);
  validateOutput(inventory, indexHtml, notFoundHtml);

  await rm(DIST_DIR, { recursive: true, force: true });
  await mkdir(resolve(DIST_DIR, 'assets'), { recursive: true });
  await Promise.all([
    writeFile(resolve(DIST_DIR, 'index.html'), indexHtml, 'utf8'),
    writeFile(resolve(DIST_DIR, '404.html'), notFoundHtml, 'utf8'),
    writeFile(resolve(DIST_DIR, 'robots.txt'), renderRobots(inventory), 'utf8'),
    writeFile(resolve(DIST_DIR, 'sitemap.xml'), renderSitemap(inventory), 'utf8'),
    writeFile(resolve(DIST_DIR, '.nojekyll'), '', 'utf8'),
    copyFile(STYLE_PATH, resolve(DIST_DIR, 'styles.css')),
    copyFile(HERO_IMAGE_PATH, resolve(DIST_DIR, 'assets/profile-hero.png')),
    copyFile(PRODUCTS_PATH, resolve(DIST_DIR, 'products.json')),
  ]);
}

async function main(): Promise<void> {
  const command = process.argv[2] ?? 'check';
  assertCondition(command === 'check' || command === 'build', `未知命令: ${command}`);
  const inventory = await loadInventory();
  const indexHtml = renderIndex(inventory);
  const notFoundHtml = renderNotFound(inventory);
  validateOutput(inventory, indexHtml, notFoundHtml);

  if (command === 'build') {
    await buildSite(inventory);
    console.log(`GitHub Pages 站点已生成：${DIST_DIR}`);
    return;
  }
  console.log(`SEO 与页面内容校验通过：${inventory.sites.length} 个站点`);
}

await main();
