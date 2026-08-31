import { BRAND_CATALOG } from './catalog.generated.js';
import type {
  BrandBreadcrumbItem,
  BrandCatalog,
  BrandSite,
  OrganizationJsonLd,
} from './types.js';

export type {
  BrandBreadcrumbItem,
  BrandCatalog,
  BrandMode,
  BrandOrganization,
  BrandSite,
  BrandSiteType,
  BrandVisibility,
  NavigationGroup,
  OrganizationJsonLd,
} from './types.js';

export const brandCatalog: BrandCatalog = BRAND_CATALOG;

function normalizeHostname(hostname: string): string {
  return hostname.trim().toLowerCase().replace(/:\d+$/, '').replace(/^www\./, '');
}

export function resolveBrandSite(hostname: string): BrandSite | undefined {
  const normalized = normalizeHostname(hostname);
  return brandCatalog.sites.find((site) => site.host === normalized);
}

export function getPublicBrandSites(): BrandSite[] {
  const selected = new Map<string, BrandSite>();
  const candidates = brandCatalog.sites
    .filter((site) => site.visibility === 'public')
    .sort((first, second) => second.priority - first.priority || first.name.localeCompare(second.name));

  for (const site of candidates) {
    if (!selected.has(site.id)) {
      selected.set(site.id, site);
    }
  }

  return [...selected.values()];
}

export function getBrandNetworkLinks(currentSiteId: string): BrandSite[] {
  return getPublicBrandSites()
    .filter((site) => site.id !== currentSiteId)
    .slice(0, brandCatalog.maxDirectLinks);
}

export function buildBrandBreadcrumbs(
  currentSiteId: string,
  localItems: readonly BrandBreadcrumbItem[] = [],
): BrandBreadcrumbItem[] {
  const currentSite = brandCatalog.sites.find(
    (site) => site.id === currentSiteId && site.visibility === 'public',
  );
  if (!currentSite) {
    throw new Error(`未知的公开品牌站点: ${currentSiteId}`);
  }

  const items: BrandBreadcrumbItem[] = [
    { label: brandCatalog.organization.name, href: brandCatalog.organization.url },
  ];
  if (currentSite.id !== 'meathill') {
    items.push({ label: currentSite.name, href: currentSite.url });
  }
  return [...items, ...localItems];
}

export function getOrganizationJsonLd(): OrganizationJsonLd {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    '@id': brandCatalog.organization.id,
    name: brandCatalog.organization.name,
    legalName: brandCatalog.organization.legalName,
    url: brandCatalog.organization.url,
  };
}
