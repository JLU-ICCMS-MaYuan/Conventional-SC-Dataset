# SC-Wiki Future UI Design System

## Design Principle

SC-Wiki 的未来规划示例页面采用 Google Material Design 家族的视觉语言。它适合跨端应用、管理后台、生产力工具和内容型系统，重点是让复杂信息通过一致的组件、层级和交互反馈变得可理解。

本文件是 future-plan 示例页面唯一的全局视觉规范来源。所有颜色、按钮、圆角、阴影、组件状态、动效和响应式规则都以本文件为准。历史视觉偏好不再作为 future-plan 的判断依据，新的示例页面只遵循本文件定义的 Material Design 方向。

## Visual Positioning

Material Design 的核心是“纸张隐喻 + 层级阴影”。页面由不同高度的 Surface 组成：背景是最低层，卡片和表格是中间层，菜单、抽屉和对话框更高，FAB 是最突出的行动层。用户通过阴影、圆角、色彩、触摸反馈和动效理解页面中对象的关系。

SC-Wiki 使用 Material 时应保持现代、友好、清晰、系统化。它不是营销页，也不是重拟物界面；它应像一套稳定的科学数据生产力工具，让用户能快速理解导航、筛选、录入、审核、下载、问答和预测的操作路径。

## Color Tokens

```css
:root {
  --md-sys-color-primary: #4f46e5;
  --md-sys-color-on-primary: #ffffff;
  --md-sys-color-primary-container: #e0e7ff;
  --md-sys-color-on-primary-container: #312e81;

  --md-sys-color-secondary: #0891b2;
  --md-sys-color-on-secondary: #ffffff;
  --md-sys-color-secondary-container: #cffafe;
  --md-sys-color-on-secondary-container: #164e63;

  --md-sys-color-tertiary: #16a34a;
  --md-sys-color-error: #b3261e;
  --md-sys-color-warning: #b45309;
  --md-sys-color-success: #15803d;

  --md-sys-color-background: #f8fafc;
  --md-sys-color-on-background: #1f2937;
  --md-sys-color-surface: #ffffff;
  --md-sys-color-surface-container-low: #f8fafc;
  --md-sys-color-surface-container: #f1f5f9;
  --md-sys-color-surface-container-high: #e2e8f0;
  --md-sys-color-on-surface: #1f2937;
  --md-sys-color-on-surface-variant: #64748b;
  --md-sys-color-outline: #cbd5e1;
  --md-sys-color-outline-variant: #e2e8f0;

  --md-shape-corner-small: 8px;
  --md-shape-corner-medium: 12px;
  --md-shape-corner-large: 16px;
  --md-shape-corner-full: 999px;
}
```

- 主色用于导航选中态、Filled Button、关键 FAB、选中 Chips 和主要链接。
- 辅色用于辅助操作、信息提示、次级图表系列和轻量标签。
- 功能色只用于明确状态：error、warning、success，不做大面积背景。
- 背景使用浅灰 Surface，卡片和表格使用白色或浅色 Surface。
- 文本遵循 Material 的层级：主要文本高对比，辅助文本使用 `on-surface-variant`。

## Typography

- 字体：`Roboto`, `Inter`, system-ui, sans-serif。
- Display：44-56px，700，用于少量页面总标题。
- Headline：28-36px，650，用于页面标题。
- Title：18-22px，600，用于卡片标题、表格区标题、面板标题。
- Body：14-16px，400-500，用于正文和字段说明。
- Label：12-14px，600，用于按钮、Chip、状态、表头和输入标签。
- 数字、公式、DOI、代码字段可使用 `Roboto Mono`, ui-monospace, monospace。

## Layout

- 页面采用 App Shell：顶部 App Bar + 左侧 Navigation Rail 或 Drawer + 内容区。
- 内容区最大宽度按页面复杂度控制在 1280-1440px。
- 间距使用 8px 系统：8 / 16 / 24 / 32 / 40 / 48。
- 复杂页面优先使用“筛选 Surface + 主数据 Surface + 详情 Side Sheet”的结构。
- 卡片之间必须有明确职责，不为了装饰堆叠无意义卡片。
- 移动端将 Navigation Rail 收敛为底部导航、菜单按钮或 Drawer。

## Material Components

### App Bar And Navigation

- Top App Bar 承载页面标题、全局搜索、语言或账户入口。
- Navigation Rail 承载七大模块入口，选中态使用 primary container。
- 复杂页面可使用 Tabs 或 Segmented Buttons 切换数据范围。

### Buttons

- Filled Button：主操作，例如提交、运行预测、下载当前筛选结果。
- Outlined Button：次级操作，例如重置、导出、查看详情。
- Text Button：低优先级操作，例如取消、展开更多。
- FAB：只用于页面最核心的创建或上传动作，例如新增记录、上传 PDF。
- 所有按钮需要 ripple 反馈、disabled 态和 loading 态。

### Cards And Surfaces

- Card 是 Material 的主要纸片单元，使用 `surface` 背景、medium 圆角和 elevation。
- Elevated Card 用于可点击对象、结果摘要和详情容器。
- Filled Card 用于弱分组，例如说明、空状态和辅助区域。
- Outlined Card 用于密集数据和低强调容器。
- hover 时可临时提升 elevation，但不能让阴影喧宾夺主。

### Forms

- 输入框使用 Filled Text Field 或 Outlined Text Field。
- 必填、错误、帮助文本必须靠近字段自身。
- 上传区使用 Card + Drag Area，并在 Card 内展示文件状态、帮助文本和错误反馈。
- 表单分组使用 Card Header + Card Content，避免长表单失去结构。

### Tables And Lists

- 数据表使用 Material Data Table：清晰表头、排序状态、行 hover、选中态和分页。
- 密集科学字段允许横向滚动，不压缩字段含义。
- 列表项可使用 List Item + leading icon/avatar + trailing metadata。
- 详情通过 Side Sheet、Drawer 或右侧 Elevated Card 展示。

### Chips And Status

- Filter Chip 用于筛选条件。
- Assist Chip 用于快捷建议。
- Input Chip 用于已选择元素、公式或来源。
- 状态 Chip 可使用功能色轻量表达，但必须配合文字，不只靠颜色区分。

### Dialogs, Sheets And Snackbar

- Dialog 用于确认、危险操作、权限中断和需要用户决策的流程。
- Side Sheet 用于结果详情、证据详情、图谱节点详情。
- Snackbar 用于保存成功、下载开始、上传完成、轻量失败等临时反馈。
- Banner 用于系统级降级和跨页面提示。

### Charts And Domain Views

- 图表、周期表、知识图谱、Markdown 流式回答属于领域视图，可以自定义渲染。
- 外层控制、图例、筛选、详情、空状态仍应使用 Material 组件。
- 图表颜色可使用主色、辅色和功能色，但保持克制，不做彩虹图例。

## Elevation

```css
:root {
  --md-elevation-0: none;
  --md-elevation-1: 0 1px 2px rgba(15, 23, 42, 0.12), 0 1px 3px rgba(15, 23, 42, 0.08);
  --md-elevation-2: 0 2px 6px rgba(15, 23, 42, 0.14), 0 4px 12px rgba(15, 23, 42, 0.08);
  --md-elevation-3: 0 6px 16px rgba(15, 23, 42, 0.16), 0 10px 24px rgba(15, 23, 42, 0.10);
  --md-elevation-4: 0 12px 28px rgba(15, 23, 42, 0.18), 0 18px 40px rgba(15, 23, 42, 0.12);
}
```

- 背景：Elevation 0。
- 普通 Card、表格、筛选栏：Elevation 1。
- 可点击 Card、悬停 Card、下拉菜单：Elevation 2。
- Dialog、Drawer、Side Sheet：Elevation 3。
- FAB 和关键浮层：Elevation 4。

## Motion And Feedback

- 点击：使用 ripple 或短暂 pressed state。
- Card hover：阴影提升 + 轻微 `translateY(-1px)`，不超过 160ms。
- Menu/Dialog/Sheet 出现：透明度 + 轻微缩放或位移。
- Snackbar：底部滑入，自动消失前不遮挡主流程。
- Loading：局部使用 Circular Progress，全局或表格刷新使用 Linear Progress。
- 动效曲线遵循 Material standard easing，整体稳定，不追求炫技。
- 尊重 `prefers-reduced-motion`。

## Responsive

- 桌面端：Navigation Rail + 双列/三列工作区。
- 平板端：Drawer + 主内容优先，详情可变为下方 Sheet。
- 移动端：单列布局，底部操作栏或 FAB，表格横向滚动。
- 复杂详情不强塞到移动端右侧，改用 Bottom Sheet 或完整详情页。

## Prohibited

- 禁止引入与本文件冲突的历史视觉体系作为 future-plan 主风格。
- 禁止无意义堆砌 Card，Card 必须对应真实信息分组或可操作对象。
- 禁止厚重拟物、强烈发光、廉价渐变和过度阴影。
- 禁止不同模块自行发明独立视觉语言。
- 禁止只靠颜色表达状态，必须有文字、图标或位置辅助。
- 禁止把正式 React/Vite 代码和 future-plan 静态 demo 混在一起。
