# 技术调研：论文详情数据一致性（后端读取契约补全）

**Feature**：[spec.md](spec.md)

**日期**：2026-08-27

本文只记录本 Feature 内的技术决策与实测依据，不复制项目级稳定事实。

## D1：三个根因的实测确认

| 根因 | 位置 | 实测结论 |
|---|---|---|
| 不查 Tc 结果与计算上下文 | `goserver/handlers/papers.go:34-39` `GetPaper`、`:463-486` `paperToDict` | Preload 仅 4 项（`KeyProperties`、`MaterialStates.Superconductor`、`MaterialStates.MaterialFamily`、`MaterialStates.StructureFamilyLinks.StructureFamily`）；输出仅 `key_properties` 与 `material_states`。论文 4 实有 `tc_results` 1 条、`calculation_contexts` 2 条，全部不返回。 |
| 兼容字段恒零值 | `goserver/models/models.go:437-448` | 12 个字段标 `gorm:"-"`，全仓库无赋值点（`admin.go` 的赋值也因 `gorm:"-"` 不落库）；`keyPropertiesToDict`（`papers.go:515-542`）仍将其序列化。 |
| 材料状态字段裁剪 | `goserver/handlers/papers.go:503-510` | 仅输出 9 个字段；`MaterialState` 模型（`models.go:260-293`）实有压强区间、原文压强、报告空间群、温度、磁场、`state_kind`、`note` 等字段。 |

论文 4 实测数据（用于验收）：

```
material_states  : pressure_value_gpa=250, pressure_min_gpa=200, pressure_max_gpa=NULL,
                   pressure_raw='above 200 GPa', reported_space_group_symbol='Fm-3m',
                   reported_space_group_number=225, crystal_system='cubic', state_kind='theoretical'
tc_results       : 1 条 — result_kind=theoretical, tc_method='unknown', tc_value_k=274, value_raw='274', unit_raw='K'
calculation_contexts : 2 条 — id=1 全 NULL；id=2 lambda_ep=2.56, mu_star=0.10, omega_log_k=NULL
superconductor_properties : 1 条 — property_definition_id=1, name_raw='thermodynamic stability',
                   value_raw='0', value_number=200, unit_raw='meV/atom', canonical_unit='meV/atom'
structure_models : 0 条（全库亦为 0 条）
```

## D2：不需要新增数据建模

**决策**：只补 Preload 与序列化，不新增模型。

**依据**：`TcResult`（`models.go:377`）、`CalculationContext`（`:330`）、`StructureModel`（`:305`）、`PropertyDefinition`（`:402`）均已定义；`MaterialState` 上已有 `TcResults`、`CalculationContexts`、`Structures`、`Properties`、`ExperimentalContexts` 关联（`:285-292`）。

**唯一例外**：`SuperconductorProperty` 上**没有** `PropertyDefinition` 关联（`models.go:415-449` 只有 `PropertyDefinitionID` 外键字段）。FR-005 需要展示名，因此需补一个 `belongsTo` 关联。这是本 Feature 唯一的建模改动，属补齐既有外键的读取路径，不改变数据所有权。

## D3：新增数据段挂在材料状态之下，不平铺到论文顶层

**决策**：`tc_results`、`calculation_contexts`、`structures`、`properties` 作为每个 `material_states[]` 元素的子数组返回，而非在论文顶层新增四个平铺数组。

**理由**：三张表的外键都是 `material_state_id`，数据本身就隶属材料状态。平铺后消费方必须自己按 `material_state_id` 重新分组才能知道「哪个 Tc 属于哪个材料状态」，等于把关系重建的责任推给每个前端消费方，且 #59 要按材料状态卡片展示，嵌套形态正是它需要的。

**备选方案**：论文顶层平铺 + 各元素带 `material_state_id`。放弃原因：与 Overview 已记录的「草稿按 `material_states[]` 组织」不一致，且会让 #59 多写一层分组逻辑。

**兼容性**：`key_properties` 顶层键保留（`share.tsx`、`ChartGroupEditor.tsx`、`AdminPage.tsx` 在用），本 Feature 只修正其字段内容，不改变其位置；新增内容一律走嵌套形态。

## D4：兼容字段的处理方式逐个定档

12 个 `gorm:"-"` 字段按「能否映射到真实列」分三类处理：

| 字段 | 处理 | 依据 |
|---|---|---|
| `Name` | 改为从关联的 `PropertyDefinition.DisplayName` 取值，回退 `NameRaw` | 论文 4 两者均为 `thermodynamic stability`；`property_definitions.display_name` 是规范名的权威来源 |
| `SourceLabel` | 移除 | 新模型无对应列；`admin.go:266` 赋 `"manual"` 也从未落库 |
| `SuperconductorID` | 移除；材料归属由 `material_state_id` 表达 | `superconductor_properties` 无此列，超导体身份挂在 `material_states.superconductor_id` |
| `PressureGpa`、`TemperatureK` | 移除；条件由所属材料状态的压强/温度字段表达 | 表结构确认无这两列；条件化模型把条件上提到材料状态，这正是 FR-003/FR-004 补齐的内容 |
| `SuperconductorType` | 移除；改由材料状态的 `state_kind` 或 Tc 结果的 `result_kind` 表达 | 表无此列；理论/实验区分在新模型中由 `state_kind`/`result_kind` 承载 |
| `IsPrimary` | 移除 | 表无此列；物性无「主记录」概念，主次标记在 `material_state_structure_families.is_primary` 上（另一实体） |
| `NameNote`、`ConditionJSON`、`ArticleType` | 移除 | 表无对应列；`condition_note` 是真实列，已在输出中 |
| `StructureText`、`StructureFormat` | 移除；结构数据改由 `structure_models` 提供 | 表无这两列；`StructureModel` 有 `structure_text`/`structure_format` 真实列 |

**判定原则**：FR-006 要求「值与数据库内容无关的字段必须移除」。保留一个恒 null 的键比移除它更糟——消费方无法区分「该论文无此数据」与「系统不读此数据」。

## D5：记录搜索改查真实表

**问题**：`approvedRecordSearchQuery`（`papers.go:295-302`）`Table("key_properties")`，而该表已不存在。

**实测**：`POST /api/papers/search/records` 返回 `{"items":[],"total":0}`，goserver 日志同步报
`Error 1146 (42S02): Table 'scwiki.key_properties' doesn't exist`（`papers.go:268`）。该接口是 `frontend/src/pages/SearchPage.tsx:228` 的数据源，即用户可见的搜索恒为空。

**决策**：改为 `superconductor_properties` JOIN `material_states` JOIN `papers`，筛选列按下表重映射。

| 原筛选 | 原列（不存在） | 新来源 |
|---|---|---|
| Tc 下限/上限 | `key_properties.value_max` / `value_min` | `tc_results.tc_value_k`（Tc 已迁出普通物性表） |
| 压强 | `key_properties.pressure_gpa` | `material_states.pressure_value_gpa` |
| 超导类型 | `key_properties.superconductor_type` | `material_states.state_kind` |
| 主记录过滤 | `key_properties.is_primary` | 取消该过滤（新模型无对应语义，见 D4） |
| 元素匹配 | `key_properties.superconductor_id` | `material_states.superconductor_id` |
| 关键词 | `key_properties.material` | `material_states.superconductor_id` 关联的化学式，或 `superconductor_properties.material_raw` |
| 记录筛选基准 | `name='critical_temperature'` | 改以 `tc_results` 为记录主体（Tc 是搜索结果的核心列） |

**关键调整**：搜索结果的「一条记录」原本是一条 `key_properties` 的 Tc 行；新模型中 Tc 在 `tc_results`，因此记录主体改为 `tc_results` JOIN `material_states` JOIN `papers`。这保持了「一行 = 一个材料在一组条件下的一个 Tc」的既有语义，不改变前端对结果形状的预期。

**范围界定**：`flatRecordToDict`（`papers.go:790`）产出搜索行，其 `pressure`/`type` 取自兼容字段，随本次改造一并改为取真实来源；`space_group` 原为硬编码 `"-"`，现可取 `material_states.reported_space_group_symbol`。

## D6：管理员物性写入映射到真实列

**问题**：`newKeyProperty`（`admin.go:265-283`）与 `keyPropertyUpdateFields`（`:39-43`）包含 `name`、`pressure_gpa`、`temperature_k`、`is_primary`、`article_type`、`condition_json`、`structure_text`、`structure_format`、`name_note` 九个无真实列的字段。新建路径经 `gorm:"-"` 静默丢弃；更新路径用 `Updates(map)` 直接拼列名，会命中不存在的列。

**决策**：更新字段白名单收敛为真实列（`material_raw`、`name_raw`、`value_raw`、`unit_raw`、`value_number`、`value_min`、`value_max`、`canonical_unit`、`condition_note`），移除无列字段。前端 `AdminPage.tsx:351` 的 payload 同步收敛。

**为何不做「接受并转写到材料状态」**：那会让管理员通过物性接口间接改材料状态的条件字段，越过材料状态自身的校验与审核语义，属悄悄改变数据所有权，Skill 规则明确禁止。FR-009 因此表述为「写入真实列或明确不接受」。

## D7：前端消费方的最小适配（避免与 #59 冲突）

本 Feature 只做「让消费方在新契约下取到真实值且不回归」，不重构展示：

| 消费方 | 现状 | 本次处理 |
|---|---|---|
| `ChartGroupEditor.tsx:210-211`、`:467-468` | 读 `kp.pressure_gpa`、`kp.superconductor_type`（恒 null） | 改读所属材料状态的 `pressure_value_gpa`、`state_kind` |
| `share.tsx:588/591/597` | 读 `kp.is_primary`、`kp.pressure_gpa`、`kp.temperature_k` | 移除主记录高亮（无对应语义）；条件列改读材料状态 |
| `AdminPage.tsx:351` | payload 含 9 个无列字段 | 收敛为真实列 |
| `PaperEditView.tsx` | 读 `kp.structure_text`、`kp.name` 等 | 仅改字段来源使其不再取恒零值；**死代码清理留给 #59** |

**`PaperEditView` 死代码为何不在本 Feature 清理**：#59 将评估以 `UploadTaskEditor` 只读模式替代该组件。若替代成立则整体删除，现在清理内部 20 处 `onChange` 与三个增删改函数属重复劳动。已记入 spec 范围外事项。

## D8：验证策略——真实插入而非 SQL 字符串断言

**决策**：新增 Go 测试用 SQLite 内存库 `AutoMigrate` + 真实 `Create` 插入 + 真实读取断言，不用 `DryRun` 断言 SQL 文本。

**理由**：本 Feature 的故障边界恰恰是「SQL 看起来对但表/列不存在」。既有 `TestPublicQueriesRequireApprovedPapers`（`papers_test.go:88-111`）用 `DryRun` 只断言 SQL 含 `review_status`，正因如此它对 `key_properties` 表不存在这个致命缺陷完全无感。仓库已有 SQLite 真实插入的成熟先例（`admin_applications_test.go:15-27`），沿用该模式。

**已确认的执行环境**：本机无 `go`；`golang:1.25` 镜像无法联网拉模块（实测 `proxy.golang.org` i/o timeout）；`scwiki-goserver-test-runner` 有模块缓存但无 gcc（`CGO_ENABLED=1` 时报 `gcc not found`，而 `go-sqlite3` 需要 cgo）。可用命令：

```bash
docker run --rm -v /home/mayuan/code/SC-Wiki/goserver:/src -w /src \
  -e GOFLAGS=-mod=mod -e GOPROXY=off -e CGO_ENABLED=1 \
  scwiki-auth-test-cgo:latest sh -c 'go test ./... -count=1'
```

该镜像同时具备 gcc 与预热模块缓存。**已实测基线全绿**：`scwiki/server`、`handlers`、`middleware`、`models` 四个包 `ok`，其余无测试文件。

## D9：SC-004 需要构造已批准数据

当前 dev 库 `papers.review_status='approved'` 计数为 0，因此即使修好搜索，结果仍为空。SC-004 的「返回非空结果」需在 Go 测试内用 SQLite 构造已批准论文验证；dev 环境的人工验收只能确认「日志不再报表不存在」，除非先审核通过一篇论文。此约束已写入 spec 假设与依赖。

## D10：历史数据不一致不在本次修复

论文 4 物性 `value_raw='0'` 而 `value_number=200`，源于写入侧 `backend/ingest/scientific_drafts.py:441`
`value_raw = str(item.get("value_raw") or item.get("value") or "")`——当 `value_raw` 为 `"0"` 这类假值时逻辑仍取到 `"0"`，与 `value_number` 脱节。属写入侧独立问题，本 Feature 只如实返回两列，展示优先级由 #59 决定。已记入 spec 范围外事项。
