import {
  brandCatalog,
  buildBrandBreadcrumbs,
  getBrandNetworkLinks,
  getPublicBrandSites,
  type BrandBreadcrumbItem,
} from 'meathill-brand';
import type { ReactNode } from 'react';

interface BrandLabels {
  allProducts: string;
  current: string;
  navigation: string;
  network: string;
}

export interface BrandSiteSwitcherProps {
  currentSiteId: string;
  locale?: string;
}

export interface BrandHeaderProps extends BrandSiteSwitcherProps {
  productName: string;
  productUrl: string;
  mode?: 'full' | 'compact';
  actions?: ReactNode;
  className?: string;
}

export interface BrandFooterProps extends BrandSiteSwitcherProps {
  description?: string;
  className?: string;
  children?: ReactNode;
}

export interface BrandBreadcrumbProps {
  currentSiteId: string;
  items?: readonly BrandBreadcrumbItem[];
  className?: string;
}

function resolveLabels(locale = 'zh'): BrandLabels {
  if (locale.toLowerCase().startsWith('zh')) {
    return {
      allProducts: '全部产品',
      current: '当前站点',
      navigation: '面包屑导航',
      network: '产品网络',
    };
  }
  return {
    allProducts: 'All products',
    current: 'Current site',
    navigation: 'Breadcrumb',
    network: 'Product network',
  };
}

export function BrandSiteSwitcher({ currentSiteId, locale }: BrandSiteSwitcherProps) {
  const labels = resolveLabels(locale);
  const sites = getPublicBrandSites();

  return (
    <details className="meathill-brand-switcher">
      <summary>{labels.network}</summary>
      <div className="meathill-brand-switcher-panel">
        <ul>
          {sites.map((site) => (
            <li key={site.id}>
              <a aria-current={site.id === currentSiteId ? 'page' : undefined} href={site.url}>
                <span>{site.name}</span>
                {site.id === currentSiteId ? <small>{labels.current}</small> : null}
              </a>
            </li>
          ))}
        </ul>
        <a className="meathill-brand-directory-link" href={brandCatalog.directoryUrl}>
          {labels.allProducts}
        </a>
      </div>
    </details>
  );
}

export function BrandHeader({
  actions,
  className = '',
  currentSiteId,
  locale,
  mode = 'full',
  productName,
  productUrl,
}: BrandHeaderProps) {
  return (
    <header className={`meathill-brand-header meathill-brand-header-${mode} ${className}`.trim()}>
      <div className="meathill-brand-header-inner">
        <div className="meathill-brand-identity">
          <a className="meathill-brand-studio-link" href={brandCatalog.organization.url}>
            Meathill Studio
          </a>
          <span aria-hidden="true" className="meathill-brand-divider" />
          <a className="meathill-brand-product-link" href={productUrl}>
            {productName}
          </a>
        </div>
        <div className="meathill-brand-header-actions">
          <BrandSiteSwitcher currentSiteId={currentSiteId} locale={locale} />
          {actions}
        </div>
      </div>
    </header>
  );
}

export function BrandFooter({
  children,
  className = '',
  currentSiteId,
  description,
  locale,
}: BrandFooterProps) {
  const labels = resolveLabels(locale);
  const links = getBrandNetworkLinks(currentSiteId);

  return (
    <footer className={`meathill-brand-footer ${className}`.trim()}>
      <div className="meathill-brand-footer-inner">
        <div className="meathill-brand-footer-about">
          <a href={brandCatalog.organization.url}>Meathill Studio</a>
          {description ? <p>{description}</p> : null}
          {children}
          <small>
            © {new Date().getFullYear()} {brandCatalog.organization.legalName}. All rights reserved.
          </small>
        </div>
        <nav aria-label={labels.network} className="meathill-brand-footer-nav">
          {links.map((site) => (
            <a href={site.url} key={site.id}>
              {site.name}
            </a>
          ))}
          <a href={brandCatalog.directoryUrl}>{labels.allProducts}</a>
        </nav>
      </div>
    </footer>
  );
}

export function BrandBreadcrumb({ currentSiteId, items = [], className = '' }: BrandBreadcrumbProps) {
  const labels = resolveLabels();
  const breadcrumbs = buildBrandBreadcrumbs(currentSiteId, items);

  return (
    <nav aria-label={labels.navigation} className={`meathill-brand-breadcrumb ${className}`.trim()}>
      <ol>
        {breadcrumbs.map((item, index) => (
          <li key={`${item.label}-${index}`}>
            {item.href ? <a href={item.href}>{item.label}</a> : <span aria-current="page">{item.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}
