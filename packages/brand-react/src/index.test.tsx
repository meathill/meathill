import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { BrandBreadcrumb, BrandFooter, BrandHeader, BrandSiteSwitcher } from './index.js';

describe('品牌 React 组件', () => {
  it('Header 同时提供母品牌、产品和站点切换', () => {
    const html = renderToStaticMarkup(
      <BrandHeader currentSiteId="evertools" productName="EverTools" productUrl="https://tools.meathill.com" />,
    );
    expect(html).toContain('Meathill Studio');
    expect(html).toContain('EverTools');
    expect(html).toContain('<details');
  });

  it('站点切换器标记当前站且不包含服务端点', () => {
    const html = renderToStaticMarkup(<BrandSiteSwitcher currentSiteId="evertools" />);
    expect(html).toContain('aria-current="page"');
    expect(html).not.toContain('Mui Search API');
  });

  it('Footer 保留法律主体和全部产品入口', () => {
    const html = renderToStaticMarkup(<BrandFooter currentSiteId="meathill" />);
    expect(html).toContain('href="https://meathill.com/app"');
    expect(html).toContain('Meathill LLC');
  });

  it('Breadcrumb 生成可见的品牌层级', () => {
    const html = renderToStaticMarkup(
      <BrandBreadcrumb currentSiteId="evertools" items={[{ label: 'PDF 编辑' }]} />,
    );
    expect(html).toContain('Meathill Studio');
    expect(html).toContain('EverTools');
    expect(html).toContain('aria-current="page"');
  });
});
