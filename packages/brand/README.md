# meathill-brand

Meathill Studio 的跨站品牌目录、设计 token、结构化数据和导航工具。目录在发布时由 [`products.json`](../../products.json) 生成，运行时不请求母站或远程配置。

```bash
pnpm add meathill-brand
```

```ts
import {
  buildBrandBreadcrumbs,
  getBrandNetworkLinks,
  getOrganizationJsonLd,
  resolveBrandSite,
} from "meathill-brand";
import "meathill-brand/tokens.css";
```

公开 API：

- `resolveBrandSite(hostname)`
- `getPublicBrandSites()`
- `getBrandNetworkLinks(currentSiteId)`
- `buildBrandBreadcrumbs(currentSiteId, localItems)`
- `getOrganizationJsonLd()`

MIT License。
