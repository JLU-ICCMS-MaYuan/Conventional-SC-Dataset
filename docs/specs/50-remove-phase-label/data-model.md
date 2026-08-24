# 数据模型：删除 phase_label 后的材料状态

## MaterialState

删除字段：

| 字段 | 处理 |
|---|---|
| `phase_label` | 从新草稿、ORM、数据库和 DTO 删除 |

保留字段：

| 字段 | 语义 |
|---|---|
| `superconductor_id` | 具体化学计量材料 |
| `pressure_*` | 材料状态的外部条件 |
| `reported_space_group_symbol/number` | 论文报告的空间群事实，不等同于完整结构模型 |
| `state_kind` | 理论、实验、混合或未知数据来源 |
| `temperature_*`、`magnetic_field_t` | 其他状态条件 |

## 结构关联

- 一个 `MaterialState` 可以有多个 `StructureModel` 或临时 `structure_candidates`。
- 同一材料、压力、`state_kind` 下报告不同空间群时，形成独立 `MaterialState`。
- 没有空间群时，不根据材料和压力自动把多个结构候选压成一个状态。
- 空间群字段不能替代 `structure_text`、结构哈希或候选来源。

## 未来分类扩展边界

本 Feature 不创建分类表。后续分类 Feature 应使用稳定分类项 ID、分类维度、父项、状态、来源、审核人和历史关系，支持一个实体关联多个分类。空间群不写入分类项。

## 历史兼容

- 旧草稿 JSON 可以暂时包含 `phase_label`，读取归一化时丢弃该字段。
- 新保存请求和新 AI 输出不得包含该字段。
- 历史原始 Evidence/JSON 中已有文字不做语义转换；结构化 MaterialState 不保留该列。
