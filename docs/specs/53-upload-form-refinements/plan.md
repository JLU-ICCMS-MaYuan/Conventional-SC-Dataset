# 实施计划：校对表单迭代

**GitHub Issue**：[#53](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/53)

**日期**：2026-08-26

**Spec**：[spec.md](spec.md)

## 摘要

后端：`space_groups.py` 增加晶系↔群号范围映射；迁移 0015 给 `material_states` 加 `crystal_system`；草稿规范化增加晶系白名单与群号权威推导、研究方法→超导类型/Tc 方法的确定性推导；SUMMARY prompt 增加晶系提取；提交入库与 goserver 同步。前端：`EvidenceNotes` 单行截断；晶系 Select 与空间群符号/群号三方联动；移除主结构家族并改名；超导类型两项全称。

## 技术上下文

- 与 #52 相同（Python 3.12 / FastAPI、React+MUI、Go GORM、MySQL 8.4、pytest/vitest）。
- 新增：alembic 迁移 `20260826_0015_crystal_system.py`；无新第三方依赖。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| #52 契约 | 超导类型 unknown 默认保留 | 仅 UI 收敛选项，数据层不动 | 通过 |
| #51 FR-003 | 结构家族最多一个主项 | 编辑器不再写 is_primary（零主项合法） | 通过 |
| ck_material_states_* | 新列需 CHECK | 迁移含 8 值 CHECK | 通过 |

## 源代码结构

```text
backend/
├── services/space_groups.py            # 追加：crystal_system_for_number / numbers_for_crystal_system
├── ingest/upload_jobs.py               # 晶系白名单+群号权威推导、研究方法推导、SUMMARY prompt 加晶系
├── ingest/scientific_drafts.py         # crystal_system 入库
├── models.py                           # MaterialState.crystal_system + CHECK
└── tests/（test_space_groups / test_upload_jobs / test_scientific_drafts）
alembic/versions/20260826_0015_crystal_system.py
goserver/models/models.go、handlers/papers.go、handlers/classifications.go
frontend/src/components/UploadTaskEditor.tsx   # EvidenceNotes 单行、晶系联动、结构家族、超导类型文案
frontend/src/lib/paperProcessing.ts            # crystal_system 类型
tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx（追加）
```

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001 / US1 | EvidenceNotes 单行截断 | 前端测试 |
| FR-002~004 / US2 | upload_jobs 研究方法推导 | pytest |
| FR-005~007 / US3 | space_groups 晶系映射 + 迁移 + 规范化 + 前端联动 | pytest + 前端测试 |
| FR-008 / US4 | 编辑器删改 | 前端测试 |
| FR-009 / US5 | 编辑器 Select 选项 | 前端测试 |

## 阶段与依赖

1. 后端：晶系映射 → 迁移/模型 → 规范化/prompt → 入库 → goserver。
2. 前端：类型 → EvidenceNotes → 晶系联动 → 结构家族 → 超导类型文案（同一文件串行）。
3. 回归、quickstart、提交。
