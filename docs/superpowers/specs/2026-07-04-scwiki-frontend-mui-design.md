# SC-Wiki React MUI Frontend Design Spec

## Context

SC-Wiki 前端当前处于断层状态：`frontend_old/frontend_test/` 仅有 RAG 单页（Bootstrap），`src/` 是空壳。甲方要求用 React + MUI 重做全部前端，外观必须与 `future-plan/` 中各模块的 HTML Demo **完全一致**。

本 spec 定义前端项目的完整设计方案，覆盖架构、路由、组件树、Theme 映射和实现优先级。

## Reference Documents

- 视觉规范：[design.md](../../../design.md)（根目录，全局唯一来源）
- 7 模块设计：[future-plan/](../../../future-plan/)（5 文档/模块 + index.html demo）
- HTML Demo 样式：[material-demo.css](../../../future-plan/material-demo.css)（design.md 的 CSS 实现）
- 产品定义：[PRODUCT.md](../../../PRODUCT.md)
- 后端 API：`backend/main.py` + `backend/api/`

## Tech Stack

| 层 | 选型 | 版本 |
|------|------|------|
| 框架 | React | ^19.2 |
| 构建 | Vite | ^8.0 |
| 语言 | TypeScript | ~6.0 |
| UI 组件 | @mui/material + @mui/icons-material | latest |
| 样式引擎 | @emotion/react + @emotion/styled | (MUI 内置) |
| 路由 | react-router-dom | ^7 |
| 图表 | recharts | latest |
| 数据表格 | @mui/x-data-grid | latest |
| Markdown | react-markdown + rehype-katex + remark-gfm | ^10 |
| 数学公式 | katex | ^0.17 |

## Route Design

```
/                    首页 — 元素周期表选择器
/search              03 超导数据检索（query: ?elements=La,H&mode=combination）
/rag                 05 RAG 智能问答
/tc-predict          06 AI Tc 预测
/charts              07 图表社区（Tc-year / Tc-pressure）
```

## Component Tree

```
<App>
  <ThemeProvider theme={scWikiTheme}>
    <CssBaseline />
    <BrowserRouter>
      <AppShell>
        <TopAppBar />                 {/* 品牌 + 页面标题 + 用户区 */}
        <NavigationRail />            {/* 7模块入口，当前高亮 */}
        <Routes>
          <Route path="/"            element={<HomePage />} />
          <Route path="/search"      element={<SearchPage />} />
          <Route path="/rag"         element={<RagPage />} />
          <Route path="/tc-predict"  element={<TcPredictPage />} />
          <Route path="/charts"      element={<ChartsPage />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  </ThemeProvider>
</App>
```

## File Structure

```
frontend_new/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx                   # 入口：ThemeProvider + Router + App
    ├── App.tsx                    # AppShell 布局
    ├── theme.ts                   # MUI Theme 定义（核心）
    ├── data/
    │   └── elements.ts            # 118元素数据（从 periodic_table.js 提取）
    ├── lib/
    │   ├── api.ts                 # fetch 封装（复用 frontend_test）
    │   └── useStreamingChat.ts    # SSE 流式 hook（复用 frontend_test）
    ├── components/
    │   ├── AppShell.tsx           # TopAppBar + NavRail + Outlet
    │   ├── TopAppBar.tsx          # 72px, sticky, border-bottom
    │   ├── NavigationRail.tsx     # 88px, 7模块入口
    │   ├── MarkdownMessage.tsx    # KaTeX + GFM（复用 frontend_test）
    │   ├── EvidenceCard.tsx       # 审稿证据卡（复用 frontend_test）
    │   └── PeriodicTable.tsx      # 118元素 Grid
    ├── pages/
    │   ├── HomePage.tsx           # 周期表 + 首页图表
    │   ├── SearchPage.tsx         # 数据检索
    │   ├── RagPage.tsx            # RAG 问答（MUI 重写）
    │   ├── TcPredictPage.tsx      # Tc 预测
    │   └── ChartsPage.tsx         # 图表社区
    └── context/
        └── AuthContext.tsx        # 认证状态（复用 frontend_test）
```

## MUI Theme → design.md Mapping

### Palette

```typescript
palette: {
  primary:       { main: '#4f46e5', contrastText: '#ffffff' },
  secondary:     { main: '#0891b2', contrastText: '#ffffff' },
  error:         { main: '#b3261e' },
  warning:       { main: '#b45309' },
  success:       { main: '#15803d' },
  background:    { default: '#f8fafc', paper: '#ffffff' },
  text:          { primary: '#1f2937', secondary: '#64748b' },
  divider:       '#e2e8f0',
}
```

### Shape

```typescript
shape: { borderRadius: 8 }  // small=8, medium=12, large=16
```

### Shadows (Elevation)

```typescript
shadows: [
  'none',                                                     // 0
  '0 1px 2px rgba(15,23,42,.12), 0 1px 3px rgba(15,23,42,.08)',  // 1
  '0 1px 2px rgba(15,23,42,.12), 0 1px 3px rgba(15,23,42,.08)',  // 2 (same as 1)
  '0 2px 6px rgba(15,23,42,.14), 0 4px 12px rgba(15,23,42,.08)',  // 3
  // ... 4-7 渐变过渡
  '0 6px 16px rgba(15,23,42,.16), 0 10px 24px rgba(15,23,42,.10)', // 8
  // ...
  '0 12px 28px rgba(15,23,42,.18), 0 18px 40px rgba(15,23,42,.12)', // 12
]
```

### Typography

```typescript
typography: {
  fontFamily: '"Roboto", "Inter", system-ui, -apple-system, sans-serif',
  h1:    { fontSize: 'clamp(32px, 5vw, 52px)', fontWeight: 700, letterSpacing: '-0.01em' },
  h2:    { fontSize: 20, fontWeight: 600 },
  h3:    { fontSize: 16, fontWeight: 600 },
  overline: { fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', color: '#4f46e5', textTransform: 'uppercase' },
  body1: { fontSize: 14, lineHeight: 1.65 },
  body2: { fontSize: 13, color: '#64748b' },
  caption: { fontSize: 12, fontWeight: 600 },
}
```

### Component Overrides (Critical)

这些覆盖确保 MUI 组件外观 = HTML Demo：

| 组件 | 覆盖 |
|------|------|
| **MuiButton** | `borderRadius: '999px'`, `minHeight: 40`, `textTransform: 'none'`, `disableElevation: true` |
| **MuiCard** | `borderRadius: 16`, `borderColor: '#e2e8f0'` |
| **MuiChip** | `borderRadius: '999px'`, `height: 32` |
| **MuiAppBar** | `elevation: 1` (shadow[1]), `minHeight: 72`, `borderBottom: '1px solid #e2e8f0'` |
| **MuiDataGrid** | row height 52, header 12px/800 weight, selected row bg `#e0e7ff` |
| **MuiDialog** | `borderRadius: 16`, `shadow: 8` (elevation-3) |
| **MuiDrawer** | paper `borderRadius: 0`, `shadow: 8` |
| **MuiSnackbar** | `borderRadius: 8` (small) |

## Page Designs

### 1. HomePage (`/`)

**来源参考**：`frontend_old/frontend/templates/elements.html`（周期表）+ future-plan 无独模块 demo（meta + charts）

**布局**：
- Page Header：Eyebrow "Periodic Table Explorer" + H1 "超导文献数据库"
- 选中面板 Card（已选元素 + 检索模式 Chips + 进入按钮）
- 周期表 Grid（18列 × 9行，118 元素）
- 下方依次：Tc-history Recharts 散点图、P-Tc 分布图（含 s 因子曲线）、贡献者排行 Bar Chart

**数据来源**：
- `GET /api/elements/` → 元素目录（可选）
- `GET /api/papers/stats/chart-data` → 图表数据
- `GET /api/papers/stats/user-ranking` → 排行榜

### 2. SearchPage (`/search?elements=La,H`)

**来源参考**：`future-plan/03-data-search-and-database-discovery/index.html`

**布局**（1.6fr + 0.9fr 两列）：
- 左侧：
  - 检索上下文 Chips（当前元素 + 模式）
  - 数据源切换 SegmentedButtons（本地/Alexandria/HTSC/全部）
  - 筛选区（Formula/Tc/压强/年份/空间群/关键词）
  - DataGrid 结果表格（9列固定：年份/Formula/类型/压强/代表Tc/空间群/来源/审核/DOI）
- 右侧：Detail Side Sheet（分区折叠：基础信息/超导参数/结构信息/计算备注）

**数据来源**：
- `POST /api/papers/search/all` → 多源聚合搜索
- `GET /api/papers/{id}` → 论文详情（Side Sheet）

### 3. RagPage (`/rag`)

**来源参考**：`future-plan/05-rag-question-answering/index.html` + `frontend_test/src/pages/RagPage.tsx`

**布局**（三列）：
- 左侧 230px：会话列表（MUI List）
- 中间 flex：对话流（MarkdownMessage + EvidenceCard + 输入栏）
- 右侧 300px：文献来源面板

**复用文件**（直接从 frontend_test 搬）：
- `useStreamingChat.ts` — SSE 流式核心逻辑（350行）
- `MarkdownMessage.tsx` — KaTeX + GFM + [PID_xxx] 引用
- `EvidenceCard.tsx` — 灵感证据卡片

**需 MUI 重写的部分**：RagPage.tsx 的 inline 样式 → MUI 组件

### 4. TcPredictPage (`/tc-predict`)

**来源参考**：`future-plan/06-ai-assisted-tc-estimation/index.html` + `frontend_old/frontend/templates/tc_pre.html`

**布局**（双列）：
- 左侧：FileUpload Card（CONTCAR） + FileUpload Card（PDOS）+ Config Card
- 右侧：Result Card（预测 Tc + 解释字段）+ 历史任务 Table

**数据来源**：
- `POST /api/tc-predict/` → 上传 CONTCAR + PDOS 文件

### 5. ChartsPage (`/charts`)

**来源参考**：`future-plan/07-researcher-community-forum/index.html`

**布局**：
- Tabs 切换（Tc-year / Tc-pressure）
- 每张图：独立卡片（标题 + 工具栏图标按钮 + Recharts ScatterChart + 下方搜索结果 Table）
- Point Detail Side Sheet

**数据来源**：
- `GET /api/papers/stats/tc-pressure` → Tc-压强数据
- `GET /api/papers/stats/tc-year` → Tc-年份数据

**图表功能**（Recharts 实现）：
- 散点图，实验点用方形/理论点用三角形
- 超导类型颜色图例（铜基/铁基/镍基/氢化物/碳基/有机/其他）
- Tc-pressure 图含 s 因子参考曲线（s=1~10）
- N₂(77K) 和室温(300K) 标线
- 点击数据点 → 打开详情 Sheet

## Reuse Strategy

| 来源 | 文件 | 动作 |
|------|------|------|
| `frontend_test/src/lib/api.ts` | fetch + Bearer Token 封装 | 直接复制 |
| `frontend_test/src/hooks/useStreamingChat.ts` | SSE 流式对话 | 直接复制 |
| `frontend_test/src/components/MarkdownMessage.tsx` | KaTeX + GFM | 直接复制 |
| `frontend_test/src/components/EvidenceCard.tsx` | 证据卡片 | 直接复制 |
| `frontend_test/src/context/AuthContext.tsx` | localStorage 认证 | 直接复制 |
| `frontend_old/frontend/static/js/periodic_table.js` | 118元素数据 | 提取为 `data/elements.ts` |
| `frontend_old/frontend/static/css/style.css` | 元素类别颜色、图表配色 | 提取为 theme 常量 |
| `design.md` | 全局设计规范 | MUI Theme 精确映射 |

## Verification

1. `npm run dev` → 确认 5 个页面均可正常渲染
2. 用 Playwright 截图每个页面，与 `future-plan/*/index.html` 同屏对比
3. 对比维度：
   - TopAppBar/NavigationRail 布局位置一致
   - Card 圆角、阴影、间距一致
   - Button/Chip 形状、颜色一致
   - DataTable 表头、行高、选中态一致
   - Side Sheet 宽度、elevation、sticky 位置一致
4. 功能验证：
   - 首页选元素 → 跳转 SearchPage → 自动请求搜索结果
   - RAG 流式对话正常（SSE 事件解析正常）
   - Tc 预测文件上传 → 返回结果展示
   - Charts 页面图例、数据点交互正常
