# 实施计划：审核编辑页补齐超导性质并支持完全编辑

**GitHub Issue**：[#76](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/76)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)

## 摘要

把上传校对页的材料状态编辑区抽成共享受控组件 `MaterialStatesEditor`，由上传页与管理员编辑弹窗共同消费，使管理员看到并能修改材料状态、Tc、普通物性与结构附件。

后端新增 Python 端点 `PUT /api/rag/papers/{paper_id}/scientific-draft`，单事务内按既有依赖顺序删除该论文科学实体后用现成的 `persist_scientific_draft` 重建；已批准论文则同时升版、清空已批准标记、退回待审核。另加 `POST /api/rag/papers/{paper_id}/structure-candidates` 支持审核时补传结构文件。

升版依靠一次外键迁移建立的单向级联链实现：只更新一次 `papers` 的三个版本字段，MySQL 在同一事务内级联更新 `paper_files`、`paper_chunks`、`paper_evidences`、`material_states` 的 `paper_revision`。原设计的「手工逐表迁移」在当前 RESTRICT 外键下不可执行（[research.md](research.md) R3）。

同时补齐 `GET /api/admin/papers/:id` 缺失的三项预加载——否则编辑页拿不到 Tc、物性与结构。

## 技术上下文

- **语言与版本**：TypeScript 5.6 / React 19.2 / Go 1.25 / Python 3.12（FastAPI、SQLAlchemy 2.x）
- **主要依赖**：MUI 7.3、GORM、SQLAlchemy、`backend/services/structure_candidates.py`
- **数据存储**：MySQL；**一次外键迁移**（4 条改 `ON UPDATE CASCADE`、删 2 条冗余直连），不新增表列、不改唯一与检查约束
- **测试体系**：Vitest（`tests/01_decentralized_uploading/`、`tests/02_identity_governance/`，两目录已登记于 `vitest.config.ts` 白名单）；pytest（`backend/tests/`、`tests/`）；`go test ./...`
- **目标平台**：Web 浏览器；服务端 Docker Compose（生产）与宿主机进程（本地）
- **性能目标**：科学数据保存为单事务，材料状态数量级为个位数至十余个，无特殊性能要求
- **约束**：不改唯一与检查约束；不引入跨服务分布式事务；`ck_papers_review_revision` 必须始终成立；上传主路径不得回退；同一子列不得被多条 `ON UPDATE CASCADE` 覆盖（MySQL 限制）
- **规模范围**：前端抽出约 265 行共享组件、管理端集成；新增 2 个 Python 端点；1 次外键迁移；Go 侧仅补预加载

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| AGENTS.md | DRY | 材料状态编辑区抽成单一共享组件（R5）；科学数据重建复用 `persist_scientific_draft`（R1）；结构校验复用 `build_structure_candidate`（R6） | 通过 |
| AGENTS.md | SOLID 单一职责 | `MaterialStatesEditor` 为受控组件，只负责编辑交互；保存逻辑归各消费方 | 通过 |
| AGENTS.md | YAGNI | 不做历史版本浏览、不做乐观锁、不支持编辑 `rejected` 论文 | 通过 |
| AGENTS.md | 代码注释语言一致 | 新增注释用简体中文 | 通过 |
| AGENTS.md | 不自动提交 | 实施只改文件 | 通过 |
| Issue #33 版本血缘 | `ck_papers_review_revision` 始终成立 | 三个版本字段在同一条 UPDATE 中写入（R7、data-model） | 通过 |
| Issue #33 组合外键 | 三张表按 `(paper_id, paper_revision)` 绑定 | 由外键级联保证一致，不手工迁移（R3、data-model） | 通过 |
| 既有唯一约束 | `uq_paper_files_main`、`uq_paper_files_path`、`uq_paper_files_order` 均不含版本号 | 级联迁移不复制行，不触碰这些约束（R3） | 通过 |
| MySQL 外键限制 | 同一子列不得被多条 `ON UPDATE CASCADE` 覆盖 | 单向链设计，删除 2 条冗余直连外键；已实测验证冲突在建表期不报错、级联时才失败（R3） | 通过 |
| 完整性不得放松 | 删除直连外键后仍须拦截孤儿行与非法删除 | 已实测验证完整性经链条传递（R3、data-model） | 通过 |
| Overview：共享目录不删 | `superconductors` 等四张目录表不动 | 删除范围限于论文私有的科学实体（R4、data-model） | 通过 |
| Spec FR-018 | 单事务原子性 | 删除、升版（含级联）、重建、审核事件同事务 | 通过 |
| Spec FR-022、SC-008 | 上传链路不回退 | US5 列为 P1；重构后既有 vitest 全量通过 | 通过 |
| Feature #74 依赖 | 新文案走双语字典 | 新增界面文案写入 i18n 字典 | 通过（需 #74 阶段 2 先完成） |
| `vitest.config.ts` 白名单 | 新测试目录须登记 | 测试落在已登记目录，不新建目录 | 通过 |

无阻断项。唯一阻塞点（升版时三张表的唯一约束冲突）已在澄清阶段解决。

## Feature 文档结构

```text
docs/specs/76-review-scientific-data-editing/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── scientific-draft-api.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
frontend/src/
├── components/MaterialStatesEditor.tsx   # 新增：从 UploadTaskEditor 抽出的受控组件（R5）
├── components/UploadTaskEditor.tsx       # 改为消费共享组件
├── pages/AdminPage.tsx                   # 编辑弹窗集成共享组件 + 升版提示 + 两段保存编排
├── lib/paperProcessing.ts                # 复用既有 DraftMaterialState 等类型
└── i18n/{zh,en}/admin.ts                 # 新增文案（升版提示、保存失败提示）

backend/
├── api/rag.py                            # 新增两个端点（契约 C1、C2）
└── services/scientific_draft_rewrite.py  # 新增：删除+升版+重建的事务编排

alembic/versions/<new>_revision_cascade_chain.py   # 新增：外键级联链迁移（R3、data-model）

goserver/handlers/admin.go                # GetPaperDetail 补 3 项 Preload（契约 C3）

tests/
├── 01_decentralized_uploading/           # 上传页重构回归、共享组件行为
└── 02_identity_governance/               # 管理端编辑、升版、权限
backend/tests/                            # 端点契约、事务回滚、校验复用
```

**结构选择**：

- 事务编排单独成模块 `scientific_draft_rewrite.py` 而非塞进 `rag.py`——后者已 1500 余行，且该编排逻辑（删除顺序、升版触发级联、重建）有独立的测试价值。
- Go 侧改动仅一处预加载，不新增 handler——科学数据的写入完全在 Python 侧（R1）。
- 共享组件放 `components/` 与既有组件同级，不新建目录。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001 / US1 | `MaterialStatesEditor` + `AdminPage` 集成 | Vitest：编辑弹窗渲染全部材料状态字段 |
| FR-002、FR-003、FR-004 / US1 | Go 补 3 项 Preload（C3）+ 组件渲染 | Go 测试：详情响应含 `tc_results`、`properties`、`structures`；Vitest：三类数据可见 |
| FR-005–FR-008、FR-011 / US2 | `MaterialStatesEditor` 受控编辑 + C1 整体替换 | Vitest：增删改交互；pytest：保存后数据与请求体一致 |
| FR-009、FR-010 / US3 | C2 端点 + `StructureCandidatePanel` 复用 | pytest：合法文件产出候选、非法文件 400 且不写库 |
| FR-012 / US2 | C1 的 `pending` 分支 | pytest：保存后 `content_revision` 不变、状态仍 `pending` |
| FR-013、FR-015 / US4 | C1 的 `approved` 分支 + 三字段同条 UPDATE（R7） | pytest：版本递增、`approved_revision` 为 NULL、状态 `pending`；Go 测试：公开查询不返回 |
| FR-014 / US4 | 外键级联链自动更新血缘（R3、data-model） | 真实 MySQL 集成测试：升版后三张表 `paper_revision` 为新值且行数不变 |
| FR-016 / US4 | 写入 `paper_review_events`（R8） | pytest：升版后存在对应审核事件 |
| FR-017 / US4 | `AdminPage` 保存前提示 + `revision_bumped` 响应 | Vitest：已批准论文的编辑页显示升版警告 |
| FR-018 / US4 | 单事务编排（data-model 事务边界） | pytest：注入失败后论文版本、状态、科学数据完全不变 |
| FR-019 | 前端两段保存编排（C4） | Vitest：科学数据失败时提示指明失败部分，论文级改动保留 |
| FR-020 | 复用 `_validate_draft`（data-model 校验规则） | pytest：压强区间非法、缺化学式等被 400 拒绝 |
| FR-021 / SC-007 | `get_current_admin` 依赖 | pytest：非管理员调用两端点均 403 |
| FR-022、FR-023 / US5 | 共享受控组件（R5） | Vitest：`tests/01_decentralized_uploading/` 既有用例全量通过 |
| SC-009 | 三字段同条 UPDATE（R7） | pytest：各状态转换后校验 CHECK 约束成立 |

## 阶段与依赖

1. **前置**：确认 #74 的 i18n 基建就位；确认 #75 若已实施，其校验文案改动与 C1 的错误契约一致；应用外键级联链迁移并验证级联生效。
2. **数据可见性**：Go 补 3 项预加载。这是 FR-002–FR-004 的前提，且独立可验证。
3. **组件抽取（阻断管理端集成）**：抽出 `MaterialStatesEditor`，上传页改为消费它，既有测试全量通过（US5，P1）。此步不新增功能，是纯重构，必须先绿。
4. **P1 故事（US1、US2）**：管理端集成组件（只读展示 → 可编辑）；后端 C1 端点的 `pending` 分支与事务编排。
5. **P2 故事（US3、US4）**：C2 结构补传端点；C1 的 `approved` 升版分支、级联验证、审核事件。
6. **收尾**：三套测试全量、前端生产构建、quickstart 走查、Overview 回写交由 `big-project-overview-maintainer`。

**关键依赖**：阶段 3 阻断阶段 4 的前端部分；阶段 4 的 C1 端点阻断阶段 5 的升版分支（同一端点的不同分支）。

**串行触点（同文件任务必须串行）**：

| 文件 | 说明 |
| --- | --- |
| `frontend/src/components/UploadTaskEditor.tsx` | 抽取组件与 #74 的 T018 文案替换、#75 的标签改名冲突，三者须串行 |
| `frontend/src/pages/AdminPage.tsx` | 本 Feature 的集成与 #74 的 T019、#75 的 T014 冲突，须串行 |
| `backend/api/rag.py` | C1 与 C2 两端点同文件，串行 |
| `goserver/handlers/admin.go` | 预加载改动与 #74 的白名单扩展冲突，须串行 |

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| 科学数据整体替换而非增量更新（C1） | 材料状态、Tc、物性、结构、上下文间有多重外键与生成列约束，增量更新需为每种实体维护匹配与差异计算 | 为每类实体设增删改端点（约 12 个）：无法保证跨实体一致性，且校验规则需重写 |
| 外键级联链 + 删除 2 条冗余直连（R3） | RESTRICT 外键使手工迁移不可执行；多条 CASCADE 作用同一子列会在运行时报 1452 | 手工逐表迁移：任一次序都在第一条语句失败。给所有外键加 CASCADE：级联时报 1452。扩展唯一约束后复制行：改动 #33 约束语义且切片随版本膨胀 |
| 三个版本字段同条 UPDATE（R7） | `ck_papers_review_revision` 联合约束三字段，分多条语句会产生违约中间状态 | 分步更新：会被 CHECK 约束拒绝 |
| 两段保存分别反馈（C4、R2） | 论文级与科学数据分属不同服务与事务，无法原子化 | 跨服务分布式事务：复杂度远超收益，两阶段提交需额外协调者 |
