# 数据模型：材料状态多维分类

## 关系概览

```text
MaterialFamily 1 <- N MaterialState
MaterialState  N <-> N StructureFamily
MaterialState  1 <- N ClassificationProposal
MaterialState  1 <- N ClassificationEvidence
Catalog term   1 <- N Alias
User           1 <- N ClassificationAuditEvent
```

空间群继续是 `material_states.reported_space_group_*` 和 `structure_models.space_group_*` 的结构事实，不进入结构家族目录。

## material_families

| 字段 | 类型/约束 | 含义 |
| --- | --- | --- |
| `id` | PK | 正式关系使用的稳定 ID |
| `code` | varchar(64)，唯一、不可空 | 内部稳定编码，普通界面不显示 |
| `name_zh` | varchar(100)，唯一、不可空 | 规范中文名 |
| `name_en` | varchar(160)，不可空 | 规范英文名 |
| `normalized_name` | varchar(160)，唯一、不可空 | 中文规范名的确定性匹配键 |
| `is_active` | bool，默认 true | 是否允许新选择 |
| `merged_into_id` | 自引用 FK，可空 | 被合并后的规范目标 |
| `created_by_user_id` | users FK，可空 | 系统 seed 为 null |
| `created_at/updated_at` | datetime | 生命周期时间 |

首批 seed：

| code | name_zh | name_en |
| --- | --- | --- |
| `hydrogen_based` | 氢基超导体 | Hydrogen-based superconductor |
| `copper_based` | 铜基超导体 | Copper-based superconductor |
| `iron_based` | 铁基超导体 | Iron-based superconductor |
| `nickel_based` | 镍基超导体 | Nickel-based superconductor |
| `inorganic_bcn_based` | 无机硼碳氮基超导体 | Inorganic boron-carbon-nitrogen-based superconductor |
| `organic` | 有机超导体 | Organic superconductor |
| `heavy_fermion` | 重费米子超导体 | Heavy-fermion superconductor |

## material_family_aliases

| 字段 | 类型/约束 | 含义 |
| --- | --- | --- |
| `id` | PK | 别名 ID |
| `material_family_id` | FK，RESTRICT | 目标家族 |
| `alias` | varchar(160)，不可空 | 审核后的原始别名 |
| `normalized_alias` | varchar(160)，唯一、不可空 | 确定性匹配键 |
| `language` | `zh/en/code/other` | 别名来源语言 |
| `created_by_user_id` | users FK，可空 | 建立人 |
| `created_at` | datetime | 建立时间 |

初始别名包括旧编码、规范英文名和已确认中文同义词。`carbon`、`others` 不作为正式别名。`高压氢化物`只解析出家族部分，压力仍由材料状态数值提供。

## structure_families / structure_family_aliases

字段和材料家族目录一致。首批只建立“笼状结构”，别名包括 `clathrate` 和已确认中文同义词；其他结构家族通过建议审核扩展。

## material_states 新增字段

| 字段 | 类型/约束 | 含义 |
| --- | --- | --- |
| `material_family_id` | material_families FK，可空 | 待审核期间允许空，论文批准前必填 |
| `element_count` | smallint，可空，1–118 | 不同元素种类数 |
| `material_dimensionality` | enum-like varchar，不可空，默认 `unknown` | 零维至三维及准维度 |

`material_dimensionality` 内部值：

```text
zero_dimensional
one_dimensional
two_dimensional
three_dimensional
quasi_one_dimensional
quasi_two_dimensional
unknown
```

## material_state_structure_families

| 字段 | 类型/约束 | 含义 |
| --- | --- | --- |
| `material_state_id` | 联合 PK、FK | 材料状态 |
| `structure_family_id` | 联合 PK、FK | 结构家族 |
| `is_primary` | bool，默认 false | 是否主结构家族 |
| `primary_marker` | 生成列，唯一 | 主项时等于状态 ID，否则 null |
| `created_at` | datetime | 建立时间 |

唯一 `primary_marker` 保证并发写入时同一状态最多一个主结构家族。

## classification_proposals

| 字段 | 类型/约束 | 含义 |
| --- | --- | --- |
| `id` | PK | 建议 ID |
| `material_state_id` | material_states FK | 建议对应状态 |
| `dimension` | `material_family/structure_family` | 建议维度 |
| `raw_name` | varchar(255) | 用户或 AI 的待确认名称 |
| `normalized_name` | varchar(255) | 去重和精确匹配键 |
| `status` | `proposed/under_review/resolved/rejected` | 状态机 |
| `source_kind` | `ai/user/admin/migration` | 建议来源 |
| `resolution_kind` | 可空 | `mapped_existing/alias_created/formal_created/rejected` |
| `material_family_id` | 可空 FK | 材料家族处理结果 |
| `structure_family_id` | 可空 FK | 结构家族处理结果 |
| `proposed_by_user_id` | 可空 FK | 用户建议者，AI/迁移可空 |
| `reviewed_by_user_id` | 可空 FK | 处理管理员 |
| `review_note` | text，可空 | 处理说明 |
| `created_at/updated_at/resolved_at` | datetime | 生命周期时间 |

约束：待处理状态不能有处理结果；已解决状态必须有且只能有与维度一致的目标 FK；拒绝状态不能有目标 FK。

状态转换：

```text
proposed -> under_review -> resolved
                         -> rejected
proposed ----------------> resolved/rejected
```

终态不可回退；误处理通过新建议和审计事件纠正。

## classification_evidences

| 字段 | 类型/约束 | 含义 |
| --- | --- | --- |
| `id` | PK | 证据 ID |
| `paper_id/paper_revision` | 当前论文 revision | 证据代际 |
| `material_state_id` | FK | 支持的材料状态 |
| `dimension` | 材料/结构/元素数/维度 | 证据支持的分类维度 |
| `material_family_id` | 可空 FK | 支持的正式材料家族 |
| `structure_family_id` | 可空 FK | 支持的正式结构家族 |
| `proposal_id` | 可空 FK | 支持的待审核建议 |
| `source_kind` | `reported/derived/reviewed` | 论文报告、程序派生或人工确认 |
| `scope` | `current_paper/referenced_work` | 证据主体 |
| `raw_value` | varchar(255)，可空 | AI 原始名称或派生输入 |
| `section/page_start/page_end/quote` | 可空 | 原文定位；`reported` 时必须有 quote |
| `reviewed_by_user_id` | 可空 FK | 人工证据的审核人 |
| `created_at` | datetime | 建立时间 |

普通草稿和论文 DTO 不序列化 `raw_value`、`referenced_work` 证据；管理员审核证据端点可返回。

## classification_audit_events

| 字段 | 类型/约束 | 含义 |
| --- | --- | --- |
| `id` | PK | 审计 ID |
| `actor_user_id` | users FK，RESTRICT | 操作者 |
| `dimension` | 材料/结构 | 目录维度 |
| `entity_kind` | `term/alias/proposal` | 被操作对象 |
| `entity_id` | bigint | 对象 ID |
| `action` | varchar(32) | create/rename/activate/deactivate/merge/approve/reject/map |
| `reason` | text，不可空 | 操作原因 |
| `before_json/after_json` | JSON，可空 | 变更前后快照 |
| `created_at` | datetime | 操作时间 |

审计表只追加，不提供修改或删除接口。

## 删除与兼容

- 新正式 Schema 不新增或保留 `sc_type`、`type_code`、`type_proposal_raw`。
- Go 的 `KeyProperty.SuperconductorType` 编译兼容字段从管理员分类路径删除。
- Alembic、SQLAlchemy 和 GORM 从目标正式 Schema 删除 `papers.referenced_materials`；旧聚合值不迁移为其他正式字段。本 Feature 只在管理员分类证据中保留必要的带作用域原句，不重建论文级引用材料列表。
- 旧草稿转换仅存在于 GET 边界；PUT/submit 只接受新结构。
- 旧数据库迁移以 `paper_id + superconductor_id + pressure` 唯一匹配材料状态，无法唯一匹配时不写入。

## 删除与合并规则

- 已被材料状态引用的正式目录项不能物理删除，只能停用或合并。
- 合并在一个事务中迁移材料状态归属、结构关联和别名，设置 `merged_into_id`，并追加审计。
- 别名冲突、循环合并、跨维度合并和合并到停用项均拒绝。
