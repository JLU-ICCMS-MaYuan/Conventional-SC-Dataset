# 实施计划：材料状态「材料」字段改名为「化学式」

**GitHub Issue**：[#75](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/75)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)

## 摘要

把两处真正承载化学式的界面标签改为「化学式」／`Chemical formula`，并把后端化学式缺失的校验文案后半句同步改为「缺少化学式」。字段名、数据库列名与接口契约全部不变；校验文案的「第 N 个材料状态」前缀原样保留以维持前端定位能力。

图表组合编辑器的「材料名」经代码核查确认是图表数据点显示标签而非化学式，不在改动范围（[research.md](research.md) R2）。

## 技术上下文

- **语言与版本**：TypeScript 5.6 / React 19.2 / Python 3.12（FastAPI）
- **主要依赖**：MUI 7.3；Issue #74 建立的 `frontend/src/i18n/` 双语字典
- **数据存储**：无变更，不涉及迁移
- **测试体系**：Vitest（`tests/01_decentralized_uploading/`，目录已登记于 `vitest.config.ts` 白名单）；pytest
- **目标平台**：Web 浏览器；服务端不变
- **性能目标**：不涉及
- **约束**：接口契约与列名不得改动（FR-004、FR-005）；校验文案前缀不得改动（FR-007）；`docs/` 用简体中文（AGENTS.md）
- **规模范围**：2 处界面标签、1 处后端校验文案、3 处测试断言

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| AGENTS.md | 遵循 KISS/YAGNI | 只改标签与文案，不做字段名重构，不预留兼容层 | 通过 |
| AGENTS.md | 代码注释语言与现有一致 | 不新增注释；如需说明沿用简体中文 | 通过 |
| AGENTS.md | 不自动创建分支或提交 | 实施只改文件 | 通过 |
| Spec FR-004、FR-005 | 接口与列名不变 | 只动展示层与文案字符串 | 通过 |
| Spec FR-007 | 保留序号前缀 | 文案只改后半句；测试断言保留前缀校验 | 通过 |
| Spec FR-008 | 不误改语义正确的标签 | 明确排除「材料家族」「材料维度」「研究材料」及 `rag.py:262` 相邻文案 | 通过 |
| Spec SC-004 | 无行为回归 | 同步更新 3 处测试断言；三套测试全量执行 | 通过 |
| Feature #74 依赖 | 新文案走双语字典 | 标签写入 `i18n/{zh,en}/upload.ts` 与 `admin.ts`（R5） | 通过（需 #74 阶段 2 及相关文案任务先完成） |

无阻断项。

## Feature 文档结构

```text
docs/specs/75-paper-citation-extraction/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── tasks.md
└── checklists/
    └── requirements.md
```

不创建 `data-model.md`（无持久数据变更）与 `contracts/`（无接口契约变更——标签是展示层，字段名与响应形状均不变）。

## 源代码结构

```text
frontend/src/
├── i18n/zh/upload.ts        # 「化学式」条目（#74 已建文件）
├── i18n/en/upload.ts        # 'Chemical formula'
├── i18n/zh/admin.ts         # 「化学式 (material)」
├── i18n/en/admin.ts         # 'Chemical formula (material)'
├── components/UploadTaskEditor.tsx   # 第 1061 行标签改用字典键
└── pages/AdminPage.tsx               # 第 1099 行标签改用字典键

backend/api/rag.py           # 第 254 行校验文案后半句

tests/01_decentralized_uploading/submit-validation-feedback.test.tsx   # 3 处断言同步
```

**结构选择**：改动集中在展示层与单条文案字符串，无需新增文件或抽象。两处标签分属上传与管理两个功能域，因此写入各自的字典文件而非 `common.ts`。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001、FR-003 / US1 | `i18n/{zh,en}/upload.ts` + `UploadTaskEditor.tsx:1061` | Vitest：中英两种语言下标签文本断言 |
| FR-002、FR-003 / US2 | `i18n/{zh,en}/admin.ts` + `AdminPage.tsx:1099` | Vitest：中英两种语言下标签文本断言 |
| FR-004 / US1 | 不改动请求构造逻辑 | Vitest：提交后请求体含 `material` 键，逐键比对（SC-002） |
| FR-005 | 不涉及迁移 | 无迁移文件即为证据 |
| FR-006 / US1 | `backend/api/rag.py:254` | pytest：错误 message 含「化学式」 |
| FR-007 / US1 | 文案前缀保留 | Vitest：留空提交后出错卡片被定位（SC-003）；pytest：message 匹配 `第 \d+ 个材料状态` |
| FR-008 | 明确排除清单 | Vitest：「材料家族」「材料维度」标签未变；pytest：`rag.py:262` 文案未变 |
| SC-004 | 3 处测试断言同步 | `scripts/run-tests.sh frontend`、`backend` 全量通过 |

## 阶段与依赖

1. **前置**：确认 Issue #74 的 i18n 基建（阶段 2）与 `upload.ts`、`admin.ts` 字典已就位。未就位则本 Feature 阻塞——不得先写中文硬编码（R5）。
2. **文案与标签**：字典加条目、两处组件改用字典键、后端校验文案改后半句。
3. **测试同步**：更新 3 处断言，新增中英标签与定位保持的测试。
4. **验证**：三套测试全量执行 + 前端生产构建。

**关键依赖**：全部任务依赖 #74；组件改动依赖字典条目先存在。

**串行触点**：`frontend/src/components/UploadTaskEditor.tsx` 与 `frontend/src/pages/AdminPage.tsx` 同时被 #74 的文案替换任务改动（#74 的 T018、T019），本 Feature 的对应任务必须排在其后，避免同文件冲突。

## 复杂度说明

无必要复杂度。本 Feature 是纯展示层改名，未引入抽象、兼容层或新数据结构。
