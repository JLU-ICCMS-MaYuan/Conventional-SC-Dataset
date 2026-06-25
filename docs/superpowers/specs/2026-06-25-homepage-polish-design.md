# 首页 UI 打磨设计

## 范围

仅修改 `frontend/static/css/style.css` 和 `frontend/templates/index.html` 中的内联样式。不改 HTML 结构、不改 JS 逻辑、不调整周期表。

## 1. 统一大小和间距

### CSS 变量（加到 style.css 顶部 `:root`）

```css
:root {
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 40px;
  --radius: 8px;
  --primary: #4d6bfe;
  --text: #1a1a1a;
  --text-secondary: #555;
  --bg: #fafafa;
  --card-bg: #fff;
  --transition: 0.2s ease;
}
```

### 统一规则

| 元素 | 修改 |
|------|------|
| 所有卡片 `.card` | `border-radius: var(--radius)` + `transition: transform var(--transition), box-shadow var(--transition)` |
| 标题层级 | `h1` 2rem, `h2` 1.5rem, `.card-title` 1.1rem，统一 `line-height: 1.4` |
| 按钮 | 操作区按钮统一 `btn` 尺寸，核心按钮用 `btn-lg` |
| 段落/说明文字 | `color: var(--text-secondary)`, `font-size: 0.95rem` |
| 页面背景 | `body { background: var(--bg) }` |

## 2. 配色

| 位置 | 现状 | 改为 |
|------|------|------|
| 强调色 | Bootstrap Primary `#0d6efd` | `var(--primary)` `#4d6bfe` |
| 文字色 | 各处不统一 | `var(--text)` `#1a1a1a` |
| 次要文字 | `#666` / `#999` | `var(--text-secondary)` `#555` |
| 卡片背景 | `#fff` | `var(--card-bg)` `#fff` |
| 页面背景 | `#f8f9fa` | `var(--bg)` `#fafafa` |
| 已选元素 badge | `bg-primary` | `background: var(--primary)` |
| 导航栏 | 已统一，不动 | — |

## 3. 动态效果

### 3.1 卡片 hover 上浮

```css
.card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
```

### 3.2 按钮 hover 渐变

```css
.btn-primary {
  background: var(--primary);
  border-color: var(--primary);
  transition: all 0.2s ease;
}
.btn-primary:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}
```

### 3.3 统计数字滚动（新增 JS）

顶部统计卡片首次进入视口时，数字从 0 滚动到目标值（论文 638、超导体 1012、记录 4709），持续时间 1.5s，ease-out。

### 3.4 页面滚动淡入（新增 CSS + 少量 JS）

图表区、图片墙、说明卡片初始 `opacity: 0; transform: translateY(20px)`，进入视口时添加 `.visible` 类 → `opacity: 1; transform: translateY(0); transition: 0.6s ease`。

### 3.5 图表骨架屏

三个 canvas 区域初始显示灰色脉冲占位块（`class="skeleton"` → `background: linear-gradient(90deg, #eee 25%, #f5f5f5 50%, #eee 75%); animation: shimmer 1.5s infinite`）。数据加载完成后隐藏骨架、显示 canvas。

## 4. 不修改

- HTML 标签结构不变
- `periodic_table.js` 不变
- `chart.js` 逻辑不变
- 周期表元素样式不变
- 导航栏不变（已统一）
- 诺贝尔图片墙 HTML 不变
- 开发者信息不变

## 5. 实现清单

| # | 文件 | 改动 |
|---|------|------|
| 1 | `style.css` | 新增 `:root` 变量 + 通用重置 + 卡片/按钮/标题统一样式 + 动画 keyframes |
| 2 | `style.css` | 替换硬编码颜色为 CSS 变量 |
| 3 | `index.html` | 顶部新增统计卡片 HTML（论文/超导体/记录数） |
| 4 | `index.html` | 图表/图片区域加 `animate-on-scroll` 类和骨架屏 |
| 5 | `index.html` | 内联 script 新增：统计数字滚动 + 滚动淡入触发 + 骨架屏逻辑 |
| 6 | `style.css` | 新增 `.skeleton`, `.animate-on-scroll`, `.visible` 样式 |
