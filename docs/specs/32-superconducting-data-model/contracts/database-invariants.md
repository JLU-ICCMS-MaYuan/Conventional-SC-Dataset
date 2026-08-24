# 数据库不变量与空库契约

## 适用范围

本契约只适用于全新空 MySQL。任何现有数据库、旧表数据、历史文件或 SQL dump 都不是输入。
检测到业务表已有记录时，目标 revision 必须失败，不执行数据转换或破坏性 DDL。

## 审核与 revision

1. 论文状态只允许 `pending/approved/rejected`。
2. 公开必须满足 `review_status=approved` 且 `approved_revision=content_revision`。
3. 科学子实体不得拥有独立审核状态、审核人或审核时间。
4. 文件、Chunk、Evidence 或科学内容变化后，整篇 revision 递增并回到 `pending`。
5. 科学记录及 Evidence 连接必须属于同一论文 revision。

## 身份

1. `superconductor_id` 只表示含同位素的规范组分。
2. 空间群报告字段只属于材料状态；同位素只属于组分。`phase_label` 已由 Issue #50 废弃。
3. 状态、结构、Tc 和普通物性使用代理主键。
4. 相同材料和压力允许多个状态、结构和结果；不同报告空间群不得静默合并。
5. 结构哈希不是全局科学唯一键；不同论文独立保存。

## 方法与上下文

1. 结构核处理、声子/EPC 核处理和 Tc 方法独立。
2. 理论 Tc 必须且只能引用同 revision 理论上下文。
3. 实验 Tc 必须且只能引用同 revision 实验上下文。
4. 理论上下文无结构时必须保存缺失原因。
5. 父结构必须属于同 revision 和组分，派生图无环。

## 数值与展示

1. 规范压力、温度、Tc 和普通物性数值使用 `DECIMAL`。
2. 范围成对且 `min <= max`，不确定度非负。
3. 原始名称、值和单位不得被规范化覆盖。
4. 网页和公开 DTO 默认原文优先，规范值作筛选和补充。
5. Tc 只存于 `tc_results`，不得注册为普通物性。

## 代表 Tc

1. 代表 Tc 由审核者指定，只影响默认展示。
2. 每个 `paper_id + material_state_id + tc_method` 最多一条代表结果。
3. 非代表 Tc 不受该约束限制，也不因代表选择失去公开资格。

## Evidence

1. 论文批准前，每条结构、Tc 和普通物性至少有一个同 revision Evidence。
2. Evidence 连接不得跨论文、跨 revision 或指向失效 Chunk。
3. 连接行可随任一端删除；不得级联删除科学内容或 Evidence。
4. quote、章节和页码是审核快照。

## ORM 一致性

- Alembic 是 MySQL Schema 的唯一建立入口。
- SQLAlchemy 与 GORM 使用相同表名、列名、空值、精度、外键和索引。
- SQLite `create_all()` 不能替代空 MySQL `upgrade head`。
- 不提供历史兼容读取；该工作属于后续 Issue。
