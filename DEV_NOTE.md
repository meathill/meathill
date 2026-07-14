# 开发笔记

## 产品站点清单

- `products.json` 是 `repo ↔ 网站` 的单一数据源，`PRODUCTS.md` 由脚本生成。
- “近期”按最近 90 天有开发活动计算；仍在公开运营的核心产品可通过 `coreRepositoryExceptions` 常驻。
- Footer 不做全量互链。每站最多展示 6 个同组产品，排除自身，其余入口汇总到产品目录；合作产品接入前单独确认。
- GitHub Pages 只承担静态 DR。动态产品默认只恢复降级页；内容站可做只读快照；浏览器本地能力可按实际情况做部分静态恢复。
- Pages 保留 `<owner>.github.io/<repo>/` 灾备地址，不绑定生产域名，避免与主站 DNS 冲突。
- 产品目录由 `scripts/product-site.ts` 从同一份清单生成到 `dist/`，GitHub Actions 只发布该目录，不提交构建产物。
- 目录页 canonical 固定为 `https://meathill.github.io/meathill/`；SEO 标题、摘要、分享图和每个产品的一句话说明都在 `products.json` 维护。
