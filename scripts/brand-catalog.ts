import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import type { BrandCatalog } from '../packages/brand/src/types.ts';
import { assertCondition, loadInventory, ROOT_DIR } from './products.ts';

const GENERATED_CATALOG_PATH = resolve(ROOT_DIR, 'packages/brand/src/catalog.generated.ts');

async function renderCatalog(): Promise<string> {
  const inventory = await loadInventory();
  const sitesById = new Map(inventory.sites.map((site) => [site.id, site]));

  const catalog: BrandCatalog = {
    version: inventory.version,
    updatedOn: inventory.updatedOn,
    directoryUrl: inventory.directory.url,
    fallbackDirectoryUrl: inventory.directory.fallbackUrl,
    organization: inventory.brandNetwork.organization,
    maxDirectLinks:
      inventory.footerGroups.find((group) => group.id === 'meathill-products')?.maxDirectLinks ?? 6,
    sites: inventory.brandNetwork.domains.map((domain) => {
      const site = domain.siteId ? sitesById.get(domain.siteId) : undefined;
      return {
        id: domain.siteId ?? domain.host,
        host: domain.host,
        name: domain.name,
        url: `https://${domain.host}`,
        summary: site?.summary ?? '',
        type: domain.type,
        visibility: domain.visibility,
        brandMode: domain.brandMode,
        defaultLocale: domain.defaultLocale,
        navigationGroup: domain.navigationGroup,
        priority: site?.footer.priority ?? 0,
      };
    }),
  };

  return `import type { BrandCatalog } from './types.js';\n\nexport const BRAND_CATALOG = ${JSON.stringify(
    catalog,
    null,
    2,
  )} as const satisfies BrandCatalog;\n`;
}

async function main(): Promise<void> {
  const command = process.argv[2] ?? 'check';
  assertCondition(command === 'check' || command === 'generate', `未知命令: ${command}`);
  const expected = await renderCatalog();

  if (command === 'generate') {
    await writeFile(GENERATED_CATALOG_PATH, expected, 'utf8');
    console.log(`已生成 ${GENERATED_CATALOG_PATH}`);
    return;
  }

  const current = await readFile(GENERATED_CATALOG_PATH, 'utf8');
  assertCondition(current === expected, '品牌包目录与 products.json 不一致，请运行 pnpm run format');
  console.log('品牌包目录校验通过');
}

await main();
