# Meathill Studio Design System

## Theme

视觉来自柯基 Mui 的暖黄、奶油白和暖深棕。品牌营销面可以更有表达力，产品工作区采用克制的暖中性和少量品牌黄。默认浅色，支持产品已有暗色模式。

## Colors

- Cream: `#fdfaf2`
- Paper: `#f6efde`
- Paper deep: `#ede2c5`
- Ink: `#3a2e23`
- Ink soft: `#5a4938`
- Mute: `#8a7660`
- Yellow: `#e6c34a`
- Yellow warm: `#e6a23a`
- Yellow deep: `#b3851c`
- Corgi: `#f3c574`
- Tongue and danger: `#d8694e` / `#c44a32`

禁止纯白、纯黑和蓝紫渐变。品牌黄在产品界面中只用于动作、当前状态和少量强调。

## Typography

- Fraunces：品牌字标和展示标题。
- Nunito：正文和通用 UI。
- JetBrains Mono：代码、编号和元信息。
- 产品可保留已验证的本地字体，但母品牌组件使用上述字体栈。
- 字号只用 12、14、16、18、20、24、30、36、48px。

## Shape and Density

- 4px 间距基准，常用 8px 至 16px。
- 默认圆角 6px，最大 14px；pill 只用于 tag、badge 和 chip。
- 营销重点动作可使用实色 press 阴影；产品表面使用轻描边和轻阴影。
- 不嵌套卡片，不使用装饰性侧边色条。

## Brand Shell

- 完整壳层：Meathill Studio、当前产品、站点切换、产品本地导航和 Footer。
- 紧凑壳层：在现有顶栏或侧栏内提供母品牌入口，不增加第二条导航。
- Breadcrumb：公开页面使用 `Meathill Studio > 当前产品 > 当前页面`；工作区深层导航保留产品自己的业务层级。
- Footer：Meathill LLC 法律声明、最多 6 个同组站点和全部产品入口。

## Assets and Motion

- 正式署名和 wordmark 使用 Meathill Studio；Mui mascot 只用于人格化和装饰。
- 图标使用产品已有第三方图标库，不新增内嵌 SVG 图标。
- 动效 120ms 至 180ms，使用自然减速，只表达状态，并遵守 `prefers-reduced-motion`。
