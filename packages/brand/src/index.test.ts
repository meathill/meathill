import { describe, expect, it } from 'vitest';
import {
  brandCatalog,
  buildBrandBreadcrumbs,
  getBrandNetworkLinks,
  getOrganizationJsonLd,
  resolveBrandSite,
} from './index.js';

describe('品牌目录', () => {
  it('按主机名解析站点并忽略端口', () => {
    expect(resolveBrandSite('TOOLS.MEATHILL.COM:443')?.id).toBe('evertools');
    expect(resolveBrandSite('unknown.meathill.com')).toBeUndefined();
  });

  it('Footer 不包含当前站、服务或重复产品', () => {
    const links = getBrandNetworkLinks('everband');
    expect(links).toHaveLength(brandCatalog.maxDirectLinks);
    expect(links.some((site) => site.id === 'everband')).toBe(false);
    expect(links.every((site) => site.visibility === 'public')).toBe(true);
    expect(new Set(links.map((site) => site.id)).size).toBe(links.length);
  });

  it('为子站生成母品牌开头的面包屑', () => {
    expect(buildBrandBreadcrumbs('evertools', [{ label: 'PDF 编辑' }])).toEqual([
      { label: 'Meathill Studio', href: 'https://meathill.com' },
      { label: 'EverTools', href: 'https://tools.meathill.com' },
      { label: 'PDF 编辑' },
    ]);
  });

  it('所有站共享一个 Organization 实体', () => {
    expect(getOrganizationJsonLd()).toMatchObject({
      '@id': 'https://meathill.com/#organization',
      name: 'Meathill Studio',
      legalName: 'Meathill LLC',
    });
  });
});
