export type BrandSiteType = 'public-product' | 'experiment' | 'service' | 'resource' | 'legacy';
export type BrandVisibility = 'public' | 'unlisted' | 'internal';
export type BrandMode = 'full' | 'hybrid' | 'compact' | 'none';
export type NavigationGroup = 'studio' | 'products' | 'experiments' | 'none';

export interface BrandOrganization {
  id: string;
  name: string;
  legalName: string;
  url: string;
}

export interface BrandSite {
  id: string;
  host: string;
  name: string;
  url: string;
  summary: string;
  type: BrandSiteType;
  visibility: BrandVisibility;
  brandMode: BrandMode;
  defaultLocale: string;
  navigationGroup: NavigationGroup;
  priority: number;
}

export interface BrandCatalog {
  version: number;
  updatedOn: string;
  directoryUrl: string;
  fallbackDirectoryUrl: string;
  organization: BrandOrganization;
  maxDirectLinks: number;
  sites: BrandSite[];
}

export interface BrandBreadcrumbItem {
  label: string;
  href?: string;
}

export interface OrganizationJsonLd extends Record<string, unknown> {
  '@context': 'https://schema.org';
  '@type': 'Organization';
  '@id': string;
  name: string;
  legalName: string;
  url: string;
}
