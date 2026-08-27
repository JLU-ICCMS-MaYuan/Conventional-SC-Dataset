# 实施计划：已提交论文详情页持久入口

**GitHub Issue**：[#56](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/56)

**日期**：2026-08-26

**Spec**：[spec.md](spec.md)

## 摘要

把论文详情页从 `UploadPage` 的组件内状态分支（`stage`/`detailPaperId`）提升为独立路由
`/papers/:id`，由 URL 唯一决定页面内容。提交成功后用路由导航跳转，返回操作改为路由导航，
从而让刷新、浏览器前进/后退和直接访问地址都能到达同一篇论文的只读详情。权限完全沿用后端
`GET /api/papers/{id}`，前端只负责按响应状态码区分无权、不存在与加载失败三类提示。

## 技术上下文

- **语言与版本**：TypeScript + React 18（前端）；后端 Go（Gin）提供论文详情接口，本次不改
- **主要依赖**：`react-router-dom`（已在用，见 `frontend/src/LazyRoutes.tsx`）、MUI
- **数据存储**：不涉及新增或变更；论文数据读自既有 `GET /api/papers/{id}`
- **测试体系**：Vitest + Testing Library，配置 `vitest.config.ts`，用例目录
  `tests/01_decentralized_uploading/`，命令 `cd frontend && npm run test:upload-ui`
- **目标平台**：浏览器（Nginx 提供前端静态资源，SPA 需回退到 index.html）
- **性能目标**：无新增性能指标；详情页首次加载仍为单次论文详情请求
- **约束**：不改动后端权限规则；不改动详情页字段展示（属 #57）；`docs/` 文档使用简体中文
- **规模范围**：1 个新增路由、1 个页面壳组件、2 个既有文件改动（`LazyRoutes.tsx`、`UploadPage.tsx`）

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| Spec FR-005 | 权限判定不得由前端放宽或自行实现 | 前端不读取角色也不判断 `review_status`，仅按 `GET /api/papers/{id}` 的 HTTP 状态码分流提示 | 通过 |
| Spec FR-006 | 无权时不得暴露论文内容 | 非 2xx 响应时不渲染任何详情字段，只渲染提示与返回操作 | 通过 |
| Issue #56 范围外 | 不改动详情页字段展示与编辑态死代码 | `PaperEditView.tsx` 仅移除对 `onBack` 的外部依赖方式，不动字段渲染与 `editKps` 相关代码 | 通过 |
| AGENTS.md KISS/YAGNI | 仅实现当前所需，不预留未来特性 | 不新增「我的论文」列表、不做状态推送、不引入全局状态库 | 通过 |
| AGENTS.md DRY | 不重复实现权限与错误语义 | 错误文案分流集中在页面壳一处，复用既有 `ApiError.status` | 通过 |
| Overview 稳定约束 | 论文可见性规则以 Overview「持久化与可见性」为准 | 前端不复制该规则，仅透传后端结果 | 通过 |
| 部署约束 | SPA 深链接需服务端回退 | 研究确认 Nginx 既有 SPA 回退配置覆盖新路径，见 [research.md](research.md) D4 | 通过 |

## Feature 文档结构

```text
docs/specs/56-paper-detail-route/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/
│   └── routing.md
├── tasks.md
└── checklists/
    └── requirements.md
```

未创建 `data-model.md`：本 Feature 不新增、不修改任何持久化实体或状态机。

## 源代码结构

```text
frontend/src/
├── LazyRoutes.tsx                      # 新增 /papers/:id 路由
├── pages/
│   ├── PaperDetailPage.tsx             # 新增：路由页面壳，解析 :id、分流错误、提供返回
│   └── UploadPage.tsx                  # 改：移除 stage/detailPaperId，提交后路由跳转
└── components/
    └── PaperEditView.tsx               # 改：仅由页面壳传入 onBack；字段渲染不动

tests/01_decentralized_uploading/
└── paper-detail-route.test.tsx         # 新增：路由渲染、刷新保持、三类失败分支
```

**结构选择**：新增 `PaperDetailPage` 作为路由页面壳，承担「解析 URL 参数 → 校验编号 → 调用详情
接口 → 按状态码分流」的单一职责；`PaperEditView` 保持纯展示职责，继续通过 `onBack` 回调解耦
导航方式，符合单一职责与依赖倒置。`UploadPage` 卸下详情渲染职责，回归上传与任务中心。

关于错误分流位置：当前 `PaperEditView` 内部自行 `loadPaper` 并把任何异常压成一句
`e.message || '加载论文失败'`，无法区分 403/404/网络失败，不满足 FR-006。将数据加载与错误分流
上移到页面壳，`PaperEditView` 通过 props 接收已就绪的论文数据——这是本次唯一的组件职责调整，
不触及字段渲染代码。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001 / US1 | `LazyRoutes.tsx` 新增 `/papers/:id`；`PaperDetailPage` 由 `useParams` 取 id | 单元测试：给定路由渲染出对应论文；quickstart 场景 1 |
| FR-002 / US1 | 页面内容仅由 URL 决定，无组件内可达性状态 | 单元测试：不同 URL 渲染不同论文；quickstart 场景 1、2 |
| FR-003 / US1 | `UploadPage.handleTaskSubmitted` 改为 `navigate('/papers/<id>')` | quickstart 场景 1 |
| FR-004 / US1 | `PaperDetailPage` 的 `onBack` 使用 `navigate('/upload')` | quickstart 场景 2 |
| FR-005 / US2 | 前端零权限判定，只透传 `GET /api/papers/{id}` 结果 | 契约见 [contracts/routing.md](contracts/routing.md)；代码审查确认无角色判断 |
| FR-006 / US2 | `PaperDetailPage` 按 403 / 404 / 无效 id / 其他失败四路分流，失败时不渲染详情 | 单元测试 4 个失败分支；quickstart 场景 3、4 |
| SC-004 | 不改动上传、解析、校对、提交既有代码路径 | 既有 6 个测试文件 45 用例全通过 |

## 阶段与依赖

1. **基础能力**：新增 `PaperDetailPage` 页面壳（含 id 校验与错误分流），注册 `/papers/:id` 路由。
   阻断后续所有工作。
2. **US1（P1，MVP）**：`UploadPage` 移除 `stage`/`detailPaperId`，提交成功后路由跳转；
   `PaperEditView` 改为接收论文数据与 `onBack`。完成后即可独立验收「刷新与前进保持」。
3. **US2（P2）**：补齐三类失败提示与对应测试。
4. **收尾**：全量前端测试与类型检查，quickstart 人工验证，Overview 回写。

US1 与 US2 都改动 `PaperDetailPage.tsx`，必须串行；测试文件为新增独立文件，可与实现并行编写。

## 复杂度说明

本 Feature 无必要复杂度需要说明：不引入新依赖、不新增状态管理层、不改动数据模型与后端接口。
唯一的结构调整（数据加载上移到页面壳）是满足 FR-006 错误分流的最小必要改动，已在「源代码结构」
说明理由。
