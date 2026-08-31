# meathill-brand-react

Meathill Studio 跨站 Header、Footer、站点切换器和 Breadcrumb。组件只依赖 React，并通过 peer dependency 使用 `meathill-brand` 的版本化目录。

```bash
pnpm add meathill-brand meathill-brand-react
```

```tsx
import { BrandFooter, BrandHeader } from "meathill-brand-react";
import "meathill-brand-react/styles.css";
```

站点切换器使用原生 `<details>`，无需额外客户端状态库；所有链接随包构建，不依赖运行时远程注入。

MIT License。
