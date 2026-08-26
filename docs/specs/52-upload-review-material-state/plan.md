# 实施计划：上传校对页布局重构与材料状态卡片完善

**GitHub Issue**：[#52](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/52)

**日期**：2026-08-26

**Spec**：[spec.md](spec.md)

## 摘要

后端：引入 spglib 生成 230 空间群标准表并暴露查询接口；改造草稿规范化（元素种类数锁定语义、宽松元素解析、空间群全表补群号、超导类型字段、Tc 条目级计算上下文、energy above hull 提取）；提交入库时每条 Tc 独立创建 CalculationContext、`research_materials` 自动汇总；新增 alembic 迁移（`superconductor_kind` 列、`tc_method` 约束扩展、`tc_method_custom` 列）；goserver 同步字段。前端：校对页布局重排（移除研究材料、关键词/研究方法并排等高）、材料状态卡片折叠、元素种类数可编辑、超导类型驱动的条件化 Tc 表单、空间群可搜索下拉、压强文案、结构附件下移、energy above hull 快捷添加。

## 技术上下文

- **语言与版本**：Python 3.12（FastAPI/SQLAlchemy 2.x）、TypeScript + React 18 + MUI 5（Vite）、Go 1.22+（GORM）
- **主要依赖**：pymatgen≥2023.9（传递引入 spglib，本 Feature 显式声明）、MUI Autocomplete/Collapse
- **数据存储**：MySQL 8.4（alembic 迁移，裸 `op.add_column`/`op.create_check_constraint` 模式）；未提交草稿在 Redis（JSON）
- **测试体系**：后端 pytest（`backend/tests/`）；前端 vitest + jsdom（`tests/01_decentralized_uploading/`，`npm run test:upload-ui`，根 `vitest.config.ts`）
- **目标平台**：Docker Compose（python worker/api + goserver + nginx）
- **约束**：#51 批准事务与分类契约不回退；`ck_tc_results_context_kind`（theoretical Tc 必须挂计算上下文）不得破坏；对外 DTO 白名单不泄露内部字段
- **规模范围**：单页面（上传校对）+ 草稿/提交两条后端链路 + 1 个新只读接口

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| AGENTS.md | KISS/最小改动、注释语言一致、自动提交规范 | 复用现有 CalculationContext/迁移模式/组件，无新抽象层 | 通过 |
| #51 FR-022 | 元素种类数缺失阻塞批准 | 手动锁定值视为已确认（spec FR-004 显式修订） | 通过 |
| models.py ck_tc_results_context_kind | theoretical Tc 必须有 calculation_context_id | 常规 Tc 逐条建 context；无专属 context 时回退状态级共享 context（现状行为） | 通过 |
| Overview pdf-ingestion | 草稿 GET/PUT 走 `_normalize_draft`、5 秒自动保存 | 不改链路，只在规范化函数内扩展 | 通过 |
| docs/ 语言 | 简体中文 | 全部文档中文 | 通过 |

## Feature 文档结构

```text
docs/specs/52-upload-review-material-state/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── draft-and-api.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
backend/
├── services/space_groups.py            # 新增：spglib 230 空间群标准表与符号→群号查询
├── ingest/upload_jobs.py               # 规范化：元素数锁定/宽松解析、空间群全表、超导类型、Tc 级 context、汇总 prompt
├── ingest/scientific_drafts.py         # 提交：element_count 尊重草稿值、Tc 级 CalculationContext
├── api/rag.py                          # research_materials 自动汇总、校验放宽、GET /api/rag/space-groups
├── models.py                           # material_states.superconductor_kind、tc_method 约束+tc_method_custom
├── db_helpers.py                       # 新增 loose 元素提取（变量化学式）
└── tests/test_upload_jobs.py、test_scientific_drafts.py、test_classification_catalog.py
alembic/versions/20260826_0014_superconductor_kind_tc_method.py  # 新增迁移
goserver/models/models.go               # MaterialState.SuperconductorKind、TcResult.TcMethodCustom
goserver/handlers/papers.go             # 输出字段同步
frontend/src/
├── lib/paperProcessing.ts              # 草稿类型扩展
└── components/UploadTaskEditor.tsx     # 布局、折叠、条件化 Tc、空间群下拉（内联 freeSolo，见 research D9）、压强、附件下移
tests/01_decentralized_uploading/upload-task-editor-classification.test.tsx 等
requirements.txt、docker/requirements.txt  # spglib 显式声明
```

**结构选择**：空间群表独立成 `services/space_groups.py`（与 `classification_catalog.py` 同级，单一职责）；元素宽松解析放 `db_helpers.py` 与 `normalize_formula` 并列；前端改动集中于 `UploadTaskEditor.tsx`（现有效校对表单唯一组件），不新增页面。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001/002 / US1 | rag.py `_create_pending_paper` 汇总 + `_validate_draft` 放宽；UploadTaskEditor 布局重排 | 后端 submit 测试 + 前端组件测试 + quickstart 场景 1 |
| FR-003 / US1 | UploadTaskEditor 折叠状态（会话级） | 前端组件测试 |
| FR-004/005 / US2 | upload_jobs `_normalize_material_states` 锁定语义 + db_helpers 宽松解析；scientific_drafts 尊重草稿值；编辑器可编辑 | pytest 三样例 + 前端编辑保存测试 |
| FR-006 / US5 | 编辑器标签文案 | 前端组件测试 |
| FR-007/008 / US4 | services/space_groups.py + GET /api/rag/space-groups + 规范化补群号 + 前端下拉 | pytest 抽查映射 + 接口测试 + 前端测试 |
| FR-009~012 / US3 | 迁移 0014 + models + 草稿类型 + 条件化 Tc 表单 + scientific_drafts 逐条 context | 迁移升级测试 + submit 集成测试 + 前端交互测试 |
| FR-013 / US5 | 编辑器渲染顺序调整 | 前端组件测试 |
| FR-014 / US5 | 编辑器主结构家族 helperText（prompt 已含结构家族建议，不改） | 前端组件测试 |
| FR-015 / US6 | 汇总 prompt + 编辑器快捷添加按钮 | pytest（prompt 契约）+ 前端测试 |

## 阶段与依赖

1. 准备：spglib 依赖声明。
2. 基础能力（后端）：空间群服务、迁移 0014、模型与规范化、提交链路、接口、goserver 同步。
3. 前端按 US1→US3→US4→US5/US6 实施（US1/US2 可先行独立验收）。
4. 收尾：全量测试、quickstart、Overview 回写（由 issue-manager 关闭流程触发）。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|------------|------------|--------------------------|
| 元素种类数锁定标志 | 区分「服务端/AI 填充」与「手动确认」，兼顾改化学式后重算与手动值不被覆盖 | 「非空即不重算」会在用户修改化学式后保留错误旧值 |
| tc_method_custom 独立列 | tc_method 有 CHECK 枚举约束，自定义文本无法入库 | 删除枚举约束会弱化全部行的完整性 |
| 常规 Tc 逐条 CalculationContext | 每条 Tc 的 λ/ωlog/μ* 独立归属；ck 约束要求 theoretical Tc 必挂 context | 共享状态级单份无法表达多条 Tc 不同参数 |
