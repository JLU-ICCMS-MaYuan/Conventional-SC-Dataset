# 研究记录：删除 phase_label 的数据契约调整

## 决策 1：删除结构化 phase_label，不替换成固相/液相

**理由**：当前输入示例中的 `Fm-3m` 是空间群，`clathrate` 是结构家族文字，两者都不能由一个“物相”自由文本框可靠承载。空间群已经有专用 reported 字段。

**备选方案**：保留并重命名为“结构相”。拒绝，因为仍会与结构候选、空间群和未来结构家族分类重叠。

## 决策 2：保留 state_kind

**理由**：`state_kind` 描述理论/实验数据来源，不描述晶体结构；同一空间群可以同时有理论和实验记录。

## 决策 3：空间群是事实字段，不是分类层级

**理由**：空间群符号和编号可由论文报告或结构解析获得，具有明确物理语义；分类层级应由领域知识和审核流程维护。未来的 `material_family`、`structure_family`、`pairing_mechanism` 等维度需要多对多和父子关系，另建 Feature。

## 决策 4：不做模糊历史迁移

**理由**：`Fm-3m phase` 可能可解析，但 `clathrate`、`high-pressure phase` 不是空间群。统一自动迁移会把结构家族或原文描述误写成空间群。

**处理**：删除结构化列；保留 Evidence/原始 JSON 已有的文字；旧草稿在兼容窗口内忽略字段。

## 决策 5：空间群参与状态区分

**理由**：同材料同压力可能存在多个空间群。归一化和候选聚合至少要使用材料、压力、`state_kind`、报告空间群；无空间群时禁止静默合并。

## 事实依据

- `frontend/src/components/UploadTaskEditor.tsx` 当前直接编辑 `phase_label`。
- `frontend/src/lib/paperProcessing.ts` 将其作为 `DraftMaterialState` 可选字段。
- `backend/ingest/upload_jobs.py` 的 AI 模板、归一化和 `backend/ingest/scientific_drafts.py` 持久化均使用它。
- `backend/models.py`、`goserver/models/models.go` 和 `alembic/versions/20260821_0008_add_superconducting_data_model.py` 定义数据库字段。
- `reported_space_group_symbol/number` 已在 #46/#49 链路中独立存在。
