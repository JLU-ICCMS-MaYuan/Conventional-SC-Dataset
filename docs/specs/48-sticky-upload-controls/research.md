# 技术研究：固定主导航与上传解析收起操作

## 决策 1：Navigation Rail 使用 CSS sticky，不使用 fixed

**决策**：导航作为 App Shell 第二行网格项，设置 `position: sticky`、顶部偏移 72px、视口剩余高度和内部纵向滚动。

**理由**：sticky 保留现有网格列占位，不需要给主内容增加人工左边距，也不会把导航从 App Shell 布局中移除。

**备选方案**：`position: fixed`。拒绝，因为需要同步维护宽度、左偏移和主内容补偿，在响应式场景更容易重叠。

**证据**：`frontend/src/components/AppShell.tsx` 当前已使用两列网格和 72px App Bar，但导航仍是 `position: relative`，因此随页面内容共同滚动。

## 决策 2：常驻收起入口放在详情卡片内部 sticky 操作栏

**决策**：把当前任务标题、阶段、加载状态和新增“收起解析”按钮组成详情操作栏；操作栏在其详情卡片范围内 sticky。

**理由**：操作与其控制对象保持上下文关联，滚动整个详情期间可达，到详情结束后自然离开；不会像 fixed/FAB 一样覆盖其他页面内容。

**备选方案**：

- 让任务列表中的选中卡片 sticky：其 sticky 范围受 `UploadTaskCenter` 父容器限制，进入后续详情区域后会停止常驻。
- 全局 fixed 按钮：容易遮挡证据内容，且脱离当前任务上下文。
- 使用滚动监听动态显示按钮：增加不必要状态、监听清理和测试复杂度。

**证据**：`UploadTaskCenter.tsx` 的按钮位于任务列表父容器内；`UploadPage.tsx` 的当前任务卡片包裹完整 `UploadParsingDetail`，能够提供正确 sticky 边界。

## 决策 3：复用单一关闭函数

**决策**：在 `UploadPage` 提取 `collapseActiveTask`，统一清空 `activeTaskId`、`taskState` 和当前用户 localStorage 活动任务键；任务行和 sticky 操作栏共同调用。

**理由**：避免两个入口未来出现不同的状态清理行为，直接满足 FR-004。

**备选方案**：在新按钮中复制三行 state/localStorage 操作。拒绝，因为会制造容易漂移的重复逻辑。

## 决策 4：测试以真实组件样式契约和点击结果为反馈环

**决策**：身份导航测试渲染真实 `AppShell` 并检查导航 sticky 样式；上传工作区测试渲染真实 `UploadPage`，检查常驻区域 sticky 样式并点击专用收起按钮验证详情、任务行和本地文件结果。

**理由**：故障发生在 React 组件调用与布局声明边界。jsdom 不计算真实滚动几何，但可以稳定验证生产组件发出的 sticky 契约和实际点击状态链；浏览器多视口检查补足几何与遮挡验证。

**备选方案**：只做源码字符串断言。拒绝，因为不能证明按钮调用真实关闭路径。
