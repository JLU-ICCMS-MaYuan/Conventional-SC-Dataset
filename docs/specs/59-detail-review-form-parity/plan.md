# 实施计划：只读详情页与校对表单一致

**GitHub Issue**：[#59](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/59)

**日期**：2026-08-27

**Spec**：[spec.md](spec.md)

## 摘要

[#57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57) 已让详情接口按材料状态嵌套返回完整科学数据，但前端 `PaperEditView` 仍按旧字段假设渲染：显示校对页不存在的 min/max、缺失整套分类字段、把研究方法当 JSON 原文回显、把分类理由标成「研究理由」，并保留一批无法保存的编辑控件。

方案是以校对页 `UploadTaskEditor` 的材料状态卡片为字段集基准，重写 `PaperEditView` 的展示结构：按材料状态组织（分类字段 → 压强 → 结构 → Tc 与计算上下文 → 其他普通物性），字段标签与校对页对齐，研究方法改列表展示，分类理由改用正确标签，并删除全部编辑态控件与死函数使其成为纯只读组件。不引入「已提交论文 → draft」适配层（路线依据见 [spec.md](spec.md) 澄清记录）。

## 技术上下文

- **语言与版本**：TypeScript + React 18，MUI
- **主要依赖**：MUI（`Card`、`TextField`、`Chip`、`Typography`）、`StructureViewer3D`（3Dmol）
- **数据存储**：不适用（纯前端展示；数据由 `GET /api/papers/:id` 提供，契约见 #57 的 `contracts/paper-detail.md`）
- **测试体系**：Vitest + Testing Library，`cd frontend && npm run test:upload-ui`；测试目录 `tests/01_decentralized_uploading/`
- **目标平台**：Docker Compose dev 栈（`/home/mayuan/work/SC-Wiki-docker/dev.yaml`），服务名 `frontend`
- **性能目标**：不适用（无新增请求；渲染量与材料状态数同阶）
- **约束**：不改后端读取契约与写入侧；不改 #56 的路由与入口行为；详情页必须保持只读
- **规模范围**：1 个组件文件重写、1 个新增测试文件

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| Spec FR-005 / SC-001 | 字段集与校对页逐项一致，无缺项无多余项 | 以校对页卡片字段清单（见下「字段集基准」）为唯一依据逐项落地，并用测试断言该清单 | 通过 |
| Spec FR-010 | 不保留无法持久化的编辑控件 | 组件改为纯展示：删除 `updateKp`/`addKp`/`deleteKp`、全部 `onChange`、`editKps` 状态与 `fieldset disabled` 包裹 | 通过 |
| Spec FR-011 | 既有行为不回归 | 保留 `onBack`、`onOpenMyPapers`、状态标签与权限提示分流；前端全量测试作为门槛 | 通过 |
| Spec 范围外 / Skill 规则 | 不悄悄改变数据所有权或写入契约 | 只读展示，不新增任何写请求；`rationale` 列语义按现状如实呈现，不改后端 | 通过 |
| Spec 假设 | 不把未落地能力写成已实现 | `structure_models` 为 0 行，结构渲染路径只验空态，有结构数据的场景在 quickstart 标注待真实数据核验 | 通过 |
| AGENTS.md | `docs/` 用简体中文；按明确路径暂存 | 全部 Spec 文档为简体中文；提交按文件路径逐个暂存 | 通过 |
| Overview 既有事实 | 草稿按 `material_states[]` 组织；λ/ωlog 属计算上下文、Tc 属 `tc_results` | 详情页同样按材料状态组织，Tc 与 λ/ωlog/μ* 在 Tc 区内展示，与校对页一致 | 通过 |

## 字段集基准（来自校对页材料状态卡片，已逐项核实）

| 区块 | 字段 |
|---|---|
| 材料状态头部 | 材料状态序号、材料 |
| 分类 | 材料、材料家族、不同元素种类数、材料维度、更多类型标签（结构家族）、晶系、空间群符号、空间群号、超导类型 |
| 压强 | 压强 (GPa)；无值时显示原文压力与原文单位 |
| 临界温度 Tc | 电声耦合强度 λ、对数声子频率 ωlog (K)、库伦屏蔽常数 μ*、Tc 数值 (K)、Tc 方法（含自定义 Tc 方法）；非常规/未知类型只有 Tc 数值 |
| 其他普通物性 | 物性 #N 名称、原始值、单位 |
| 论文层面 | 关键词（每行一个）、研究方法（每行一项）、分类理由 |

**关键差异说明**：校对页 Tc 区的 λ/ωlog/μ* 挂在**每条 Tc 结果**的 `calculation_context` 上；详情接口返回的是材料状态级 `calculation_contexts` 数组。展示时按材料状态级数组完整列出，不强行塞进单条 Tc（避免数组→单数丢数据，这正是否决 readOnly 复用路线的同一理由）。

## 源代码结构

```text
frontend/src/components/
└── PaperEditView.tsx          # 重写：字段集对齐、纯只读、结构改源、标签纠正

tests/01_decentralized_uploading/
└── paper-detail-form-parity.test.tsx   # 新增：字段集一致性、标签语义、只读性、空态
```

**结构选择**：改动集中在单个展示组件。不拆分子组件——当前展示层级只有「论文 → 材料状态 → 区块」三层，抽子组件会引入与校对页并行的第二套组件树，反而增加漂移面。不复用 `UploadTaskEditor`，理由见 spec 澄清记录。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001 / US1 | `PaperEditView` 材料状态分类区，读 `crystal_system`、`reported_space_group_symbol`/`_number`、`superconductor_kind`、`material_dimensionality`、`material_family`、`element_count` | 测试断言六项均渲染；quickstart 场景 1 |
| FR-002 / US1 | 压强区读 `pressure_value_gpa`、`pressure_raw`、`pressure_unit_raw`、`pressure_min_gpa`、`pressure_max_gpa` | 测试断言单臂区间只显示存在的一侧；quickstart 场景 2 |
| FR-003 / US1 | Tc 区读 `tc_results[]` 与材料状态级 `calculation_contexts[]` | 测试断言 Tc 数值/方法与 λ/ωlog/μ* 可见；quickstart 场景 3 |
| FR-004 / US1 | 物性区只渲染名称、原始值、解析值、单位 | 测试断言不存在「最小值」「最大值」文本；quickstart 场景 4 |
| FR-005 / US1 | 字段集基准表逐项落地 | 测试以基准清单断言渲染项集合；quickstart 场景 1 |
| FR-006、FR-007 / US2 | 论文层面区块把 `rationale` 标为「分类理由」，移除「研究理由」标签 | 测试断言页面含「分类理由」且不含「研究理由」；quickstart 场景 5 |
| FR-008 / US2 | 研究方法按数组逐行渲染 | 测试断言无 `["` 片段且每项独立可见；quickstart 场景 5 |
| FR-009 / US3 | 结构预览读 `material_states[].structures[]`，空态文案保留 | 测试覆盖有结构与无结构两分支；quickstart 场景 6 |
| FR-010 / US3 | 删除 `editKps`、`updateKp`/`addKp`/`deleteKp`、全部 `onChange` 与 `fieldset disabled` | 测试断言无可编辑输入框；源码无残留增删改函数 |
| FR-011 / 全部 | 保留 `onBack`、`onOpenMyPapers`、状态标签 | 前端全量测试 + `tsc --noEmit` |

## 阶段与依赖

1. **准备**：记录前端测试修复前基线，确认既有 8 文件 65 用例全绿。
2. **用户故事 1（P1）**：材料状态字段集对齐（分类、压强、Tc 与计算上下文、物性）。这是改动主体。
3. **用户故事 2（P1）**：论文层面字段语义与形态（研究方法列表、分类理由标签）。与故事 1 同文件，需串行。
4. **用户故事 3（P2）**：结构预览按 `structures` 渲染 + 死代码清理。死代码清理与故事 1、2 的重写天然合并——重写字段集时编辑控件一并移除。
5. **收尾**：前端全量回归、`tsc`、重建部署 `frontend` 镜像、quickstart 人工验收、Overview 回写、关闭 Issue。

**顺序约束**：三个故事都改同一个文件 `PaperEditView.tsx`，必须串行。故事 3 的死代码清理不能独立于故事 1——移除编辑控件与重写字段展示是同一处代码的同一次改写，拆开会产生中间不可编译状态。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|---|---|---|
| 计算上下文按材料状态级数组展示，而非嵌进单条 Tc 结果 | 详情接口返回材料状态级数组（paper 4 有 2 条，其中 1 条全 NULL）；塞进单条 Tc 必须人为定丢弃或合并规则 | 只取第一条计算上下文：paper 4 第一条恰好全为 NULL，会导致 λ=2.56 不可见，直接违反 SC-002 |
| 保留 `PaperEditView` 而非复用 `UploadTaskEditor` readOnly | 复用需「已提交论文 → draft」适配层，且数组→单数会丢数据 | 见 spec 澄清记录；代价是两套代码仍可能漂移，由 SC-001 的字段集一致性测试约束 |
