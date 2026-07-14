# 部署指南

## GitHub Pages 产品目录

目标地址：<https://meathill.github.io/meathill/>

### 首次启用

1. 推送本仓库的 `master` 分支。
2. 打开 GitHub 仓库的 **Settings → Pages**。
3. 在 **Build and deployment → Source** 中选择 **GitHub Actions**。
4. 打开 **Actions → Deploy product directory to GitHub Pages**，运行 `Run workflow`；如果推送已经触发成功，可以跳过手动运行。
5. 等待 `deploy` job 完成，再访问目标地址。

第一次推送发生在 Pages 启用之前时，workflow 会在 `Configure Pages` 失败，这是预期行为。完成第 3 步后重新运行即可，不需要修改代码。

### 后续更新

修改 `products.json` 后执行：

```bash
pnpm run format
pnpm test
pnpm run build
```

提交并推送后，workflow 会自动校验清单、构建静态站并发布。`dist/` 是本地生成目录，不提交到 Git。

### 验收

- 首页可访问，产品链接和公开源码链接正确。
- `robots.txt`、`sitemap.xml`、`products.json` 均可直接访问。
- 查看页面源代码，确认 canonical、Open Graph、Twitter Card 和 JSON-LD 指向 `https://meathill.github.io/meathill/`。
- 随便访问一个不存在的路径，确认显示带返回入口的 404 页面。

### DR 边界

这个 Pages 站首先是产品入口目录。各产品自己的静态灾备页仍需在对应仓库单独构建和发布；动态 API、登录、数据库、上传与支付不会由 GitHub Pages 恢复。
