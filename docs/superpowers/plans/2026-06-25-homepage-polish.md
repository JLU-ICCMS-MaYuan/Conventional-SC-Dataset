# 首页 UI 打磨 Implementation Plan

> **For agentic workers:** Use inline execution. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一首页字体/间距/配色，添加卡片hover、骨架屏、数字滚动、滚动淡入等动态效果

**Architecture:** 纯前端 CSS + 少量 JS，只改 `style.css` 和 `index.html`，不动 HTML 结构和现有 JS 逻辑

**Tech Stack:** CSS Variables, CSS Animations, IntersectionObserver, requestAnimationFrame

---

### Task 1: CSS 变量 + 基础重置

**Files:**
- Modify: `frontend/static/css/style.css:1-6` (body)
- Modify: `frontend/static/css/style.css:340-353` (:root)

- [ ] **Step 1: 扩展 :root 变量**

将现有 `:root` 块（约 L340）替换为完整变量定义：

```css
:root {
    /* 间距 */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 40px;

    /* 圆角 */
    --radius: 8px;

    /* 配色 */
    --primary: #4d6bfe;
    --primary-hover: #3b5de7;
    --text: #1a1a1a;
    --text-secondary: #555;
    --text-muted: #888;
    --bg: #fafafa;
    --card-bg: #fff;
    --border: #e5e5e5;

    /* 动画 */
    --transition: 0.2s ease;
    --transition-slow: 0.4s ease;

    /* 图表颜色 - 保持不变 */
    --sc-color-cuprate: rgba(255, 99, 132, 0.8);
    --sc-color-iron: rgba(75, 192, 192, 0.8);
    --sc-color-nickel: rgba(75, 239, 58, 0.8);
    --sc-color-hydride: rgba(153, 102, 255, 0.8);
    --sc-color-carbon: rgba(54, 162, 235, 0.8);
    --sc-color-organic: rgba(255, 206, 86, 0.8);
    --sc-color-others: rgba(204, 70, 70, 0.8);
    --sc-color-unknown: rgba(201, 203, 207, 0.8);
    --sc-shape-experimental: rectRot;
    --sc-shape-theoretical: triangle;
}
```

- [ ] **Step 2: 更新 body 基础样式**

将 body 的硬编码颜色替换为变量：

```css
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: var(--bg);
    padding-bottom: 50px;
    color: var(--text);
    line-height: 1.6;
}
```

- [ ] **Step 3: 添加标题统一规则**

在 body 之后添加：

```css
h1, h2, h3, h4, h5, h6 {
    line-height: 1.4;
    color: var(--text);
}
h1 { font-size: 2rem; }
h2 { font-size: 1.5rem; }
```

---

### Task 2: 配色替换

**Files:**
- Modify: `frontend/static/css/style.css` (多处)

- [ ] **Step 1: 卡片统一样式**

在 `.image-grid-nobel` 之前添加通用卡片规则：

```css
/* 通用卡片样式 */
.card {
    border-radius: var(--radius);
    border: 1px solid var(--border);
    transition: transform var(--transition), box-shadow var(--transition);
}
.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}
```

- [ ] **Step 2: 替换硬编码颜色**

逐个替换以下位置：

`style.css:4` — `background-color: #f8f9fa;` → `background-color: var(--bg);`
`style.css:47` — `color: #666;` → `color: var(--text-secondary);`
`style.css:62` — `color: #666;` → `color: var(--text-secondary);`
`style.css:160` — `background-color: #f8f9fa;` → `background-color: var(--bg);`
`style.css:195` — `border-color: #0d6efd;` → `border-color: var(--primary);`
`style.css:200` — `background-color: #f8f9fa;` → `background-color: var(--bg);`
`style.css:202` — `border-radius: 4px;` → `border-radius: var(--radius);`
`style.css:238` — `border-radius: 4px;` → `border-radius: var(--radius);`
`style.css:303` — `background-color: #fff;` → `background-color: var(--card-bg);`

- [ ] **Step 3: 按钮主色覆盖**

在 navbar 样式之后添加：

```css
/* 按钮主色覆盖 */
.btn-primary {
    background-color: var(--primary);
    border-color: var(--primary);
    transition: all var(--transition);
}
.btn-primary:hover {
    background-color: var(--primary-hover);
    border-color: var(--primary-hover);
    transform: translateY(-1px);
}
.btn-outline-primary {
    color: var(--primary);
    border-color: var(--primary);
}
.btn-outline-primary:hover {
    background-color: var(--primary);
    border-color: var(--primary);
}
```

---

### Task 3: 统计卡片 HTML

**Files:**
- Modify: `frontend/templates/index.html` (在 `<div class="container-fluid">` 开头，header 上方)

- [ ] **Step 1: 添加统计卡片**

```html
<!-- 统计卡片 -->
<div class="row mb-4" id="stats-row">
    <div class="col-md-4">
        <div class="card shadow-sm animate-on-scroll">
            <div class="card-body text-center py-4">
                <div class="stat-number" data-target="638" data-suffix="篇">0</div>
                <div class="text-muted mt-2">收录论文</div>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card shadow-sm animate-on-scroll">
            <div class="card-body text-center py-4">
                <div class="stat-number" data-target="1012" data-suffix="种">0</div>
                <div class="text-muted mt-2">超导体</div>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card shadow-sm animate-on-scroll">
            <div class="card-body text-center py-4">
                <div class="stat-number" data-target="4709" data-suffix="条">0</div>
                <div class="text-muted mt-2">超导数据记录</div>
            </div>
        </div>
    </div>
</div>
```

---

### Task 4: 动态效果 CSS

**Files:**
- Modify: `frontend/static/css/style.css` (末尾追加)

- [ ] **Step 1: 滚动淡入动画**

```css
/* 滚动淡入 */
.animate-on-scroll {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.6s ease, transform 0.6s ease;
}
.animate-on-scroll.visible {
    opacity: 1;
    transform: translateY(0);
}
```

- [ ] **Step 2: 骨架屏样式**

```css
/* 骨架屏 */
.skeleton {
    background: linear-gradient(90deg, #eee 25%, #f5f5f5 50%, #eee 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: var(--radius);
    min-height: 300px;
}
@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

- [ ] **Step 3: 统计数字样式**

```css
/* 统计数字 */
.stat-number {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--primary);
    line-height: 1.2;
}
```

- [ ] **Step 4: 卡片进入延迟（交错动画）**

```css
.animate-on-scroll:nth-child(1) { transition-delay: 0s; }
.animate-on-scroll:nth-child(2) { transition-delay: 0.1s; }
.animate-on-scroll:nth-child(3) { transition-delay: 0.2s; }
```

---

### Task 5: 动态效果 JS

**Files:**
- Modify: `frontend/templates/index.html` (内联 `<script>` 末尾，`</script>` 之前)

- [ ] **Step 1: 统计数字滚动函数**

在 `Chart === 'undefined'` 检查之前添加：

```javascript
// 统计数字滚动动画
function animateStats() {
    document.querySelectorAll('.stat-number').forEach(el => {
        const target = parseInt(el.dataset.target);
        const suffix = el.dataset.suffix || '';
        const duration = 1500;
        const start = performance.now();
        function update(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out
            el.textContent = Math.floor(target * eased) + suffix;
            if (progress < 1) requestAnimationFrame(update);
        }
        requestAnimationFrame(update);
    });
}
```

- [ ] **Step 2: 滚动触发淡入 + 数字动画**

```javascript
// 滚动时触发淡入和数字动画
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            // 统计卡片首次可见时启动数字滚动
            if (entry.target.id === 'stats-row') {
                animateStats();
            }
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.15 });

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.animate-on-scroll').forEach(el => observer.observe(el));
    // 也监听统计行整体
    const statsRow = document.getElementById('stats-row');
    if (statsRow) observer.observe(statsRow);
});
```

---

### Task 6: 图表骨架屏

**Files:**
- Modify: `frontend/templates/index.html` (图表 canvas 区域)

- [ ] **Step 1: 给图表区域加骨架屏**

三个图表 canvas 外层各包裹骨架占位。将原始的：

```html
<canvas id="staticChart"></canvas>
```

改为：

```html
<div class="skeleton" id="staticChartSkeleton"></div>
<canvas id="staticChart" style="display:none;"></canvas>
```

同样处理 `dynamicChart` 和 `rankingChart`。

- [ ] **Step 2: 数据加载完成后切换**

在 `fetch('/api/papers/stats/chart-data')` 的 `.then()` 回调最末尾添加：

```javascript
// 隐藏骨架，显示图表
document.getElementById('staticChartSkeleton')?.remove();
document.getElementById('staticChart').style.display = '';
document.getElementById('dynamicChartSkeleton')?.remove();
document.getElementById('dynamicChart').style.display = '';
```

在 `fetch('/api/papers/stats/user-ranking')` 的 `.then()` 回调末尾添加：

```javascript
document.getElementById('rankingChartSkeleton')?.remove();
document.getElementById('rankingChart').style.display = '';
```

---

### Task 7: 验证

- [ ] **Step 1: 启动服务器**

```bash
RAG_DATA_ROOT="/home/work/workshop/git/Conventional-SC-Dataset-talk" PYTHONPATH="/home/work/workshop/git/SC-Wiki" conda run -n Conventional-SC-Dataset uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
```

- [ ] **Step 2: 浏览器验证**

打开 `http://localhost:8000/`，检查：
1. 统计卡片显示并数字滚动
2. 卡片 hover 上浮效果
3. 滚动时淡入动画
4. 图表加载时先显示灰色骨架，数据到达后切换为 canvas
5. 按钮主色统一为 `#4d6bfe`
6. 周期表不受影响
