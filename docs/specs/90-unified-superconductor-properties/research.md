# 研究记录：统一材料状态的超导物性记录

## 1. 调研范围

本研究在创建 #90 前后只读核对了：

- GitHub Issue #11、#12、#30、#32、#33、#46、#52、#53、#57、#59、#60、#65、#72、#76、#78、#80、#84；
- 对应 `docs/specs/` 规格、契约和任务状态；
- 上传、领域模型、审核、详情、检索和图表 Overview；
- SQLAlchemy、GORM、上传草稿、持久化、详情 API、共享编辑器和展示投影代码；
- Python、Go、Vitest 和 MySQL 迁移测试入口。

检索没有发现开放 Issue 完整提出“所有物性使用平级 `SuperconductorPropertyRecord`”的目标。
#46、#52 与写入和编辑面高度重叠，但仍以 Tc、Context 参数和普通物性分组为前提，因此 #90
不是重复 Issue。

## 2. 已确认的当前事实

### 2.1 当前数据被三种来源分开

| 科学量 | 当前权威位置 | 当前上层字段 |
| --- | --- | --- |
| Tc | `tc_results` | `material_states[].tc_results[]` |
| λ、ωlog、μ* | `calculation_contexts` 的三个数值列 | 状态级或 Tc 条目内 `calculation_context`，详情另返回 `calculation_contexts[]` |
| 其他物性 | `superconductor_properties` | 草稿 `properties[]`、详情顶层 `key_properties[]` |

当前前端 `collectPropertyRows()` 已将三类来源拼成一张展示表，但这只是只读投影，写入 DTO、
Evidence、API 和领域语义仍然分离。

### 2.2 当前数据库存在硬约束

- `property_definitions` 的 `ck_property_definitions_non_tc` 禁止把 Tc 方法代码注册为普通物性。
- `tc_results.ck_tc_results_context_kind` 强制实验 Tc 关联实验 Context、其他 Tc 方法关联计算 Context。
- 代表 Tc 唯一约束按论文、材料状态、方法和代表标记生效。
- `superconductor_properties` 目前只能关联计算 Context，不能关联实验 Context。
- Tc 和通用物性分别使用 `tc_result_evidences` 与 `superconductor_property_evidences`。

这些约束说明“领域统一”不能被实现为简单改名，也不能直接把所有字段塞进当前通用物性表。

### 2.3 当前实现存在的具体缺口

1. 上传提示和 #46 明文要求 Tc、λ/ωlog/μ*、普通物性分流。
2. 共享编辑器分别维护 `state.tc_results` 与 `state.properties`，并把 λ/ωlog/μ* 嵌套在 Tc 的计算 Context 中。
3. Go 详情响应分别返回 `tc_results` 和 `calculation_contexts`，通用物性则位于论文级 `key_properties`。
4. 管理端依赖 `calculation_context_id` 重组 Tc 草稿，而详情序列化没有稳定输出该关联，已存在契约漂移风险。
5. 计算 Context Evidence 当前没有对应持久化连接；把 λ/ωlog/μ* 视为独立记录后，必须让每个参数拥有自己的 Evidence 关系。
6. `ExperimentalContext.tc_criterion` 把结果判据放在共享环境里；一旦同一实验 Context 同时关联 Tc、Hc2 和能隙，这个字段无法表达每条结果各自的判据。

## 3. Issue / Spec 关系与冲突

| 来源 | 状态 | 已有结论 | #90 的处理 |
| --- | --- | --- | --- |
| #11 | OPEN Epic | 统一超导样本上传与治理 | #90 已建立为原生子 Issue |
| #12 | OPEN Idea | 恢复 `superconductor_records` 单一主表 | 不继承；其技术前提已被 #32 取代 |
| #32 | CLOSED Feature | Tc 专用表、Context、普通物性和 Evidence；Tc 不进入普通物性字典 | 保留物理约束，部分替代上层领域解释 |
| #33 | CLOSED Feature | 论文 revision、Evidence 和审核血缘 | 完整继承 |
| #46 | OPEN Feature | 上传分流写入 Tc、Context 和普通物性 | 复用事务链路，替代草稿/API 分组；本地任务完成不等于 Issue 已关闭 |
| #52 | OPEN Feature | 每条 Tc 嵌套 λ/ωlog/μ* 计算 Context | 保留 Context 对应关系，替代物性嵌套和页面分组 |
| #53 | OPEN Feature | 从论文研究方法推导 Tc 方法 | 只能建议/预填，最终权威仍为每条 `tc_method` |
| #57 | CLOSED Bug | 详情读取三类真实来源 | 保留完整可见目标，替换分裂响应契约 |
| #59 | CLOSED Bug | 详情与校对字段一致 | 作为回归门 |
| #60 | CLOSED Bug | 论文物理删除按 FK 拓扑执行 | Schema 演进后必须回归删除顺序 |
| #65 | CLOSED Bug | 三来源共享展示投影 | 作为统一映射原型，不视为完整目标 |
| #72 | CLOSED Feature | Tc 图表直接查询 `tc_results` | 保留专用查询并验证结果一致 |
| #76/#78 | CLOSED Feature | 共享材料状态编辑器和管理独立编辑页 | 复用，不建立第二套编辑器 |
| #80 | CLOSED Feature | `superconductor_kind` 提升到论文 revision | 保留分类所有权；“控制 Tc 字段”职责由 #84 修正 |
| #84 | CLOSED Bug | 每条 `tc_method` 是理论/实验 Context 的唯一开关 | 完整保留 |

### 3.1 Overview 冲突

当前 Overview 把以下内容写成已实现事实：

- Tc 只进入 `tc_results`，不属于普通物性；
- λ、ωlog、μ* 位于 `calculation_contexts`；
- 页面分别展示 Tc 列表和普通物性列表；
- 详情和检索从三类来源读取。

#90 尚未实施，因此本阶段不修改 Overview。实现和验证完成后，必须更新：

- `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/data-structure-and-form-mapping.md`
- `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/upload-review-and-default-selection.md`
- `docs/overview/02_Decentralized_Maintenance_and_Verification/domain-model-and-schema.md`
- `docs/overview/02_Decentralized_Maintenance_and_Verification/mysql-schema-catalog.md`
- `docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md`
- `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/paper-and-property-results.md`
- `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/local-material-search.md`
- `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/tc-history-and-pressure-charts.md`

## 4. 方案比较

### 方案 A：把所有物性物理合并进一张宽表

**做法**：Tc、通用物性、方法、计算和实验字段全部放进一个物理表。

**优点**：数据库表名与领域概念表面一致。

**缺点**：

- 大量只对 Tc、计算或实验有效的可空列；
- 需要重建 #32/#84 的 CHECK、唯一键和统计索引；
- Tc 图表、搜索、Evidence、删除和历史数据需要整体迁移；
- 每新增一种需要专门结构的物性都会继续扩宽表。

**结论**：拒绝。它用存储整齐换取约束退化和高迁移风险。

### 方案 B：只在页面做统一展示

**做法**：保留当前全部草稿和 API，仅继续增强 `collectPropertyRows()`。

**优点**：改动最小。

**缺点**：

- 上传和管理端仍然按 Tc/参数/普通物性分组；
- λ、ωlog、μ* 仍没有独立记录和 Evidence；
- API 调用方继续感知表结构；
- 不能满足“解除分组”的目标。

**结论**：拒绝。#65 已经证明展示聚合不等于领域统一。

### 方案 C：平级领域记录 + 专用持久化适配（采用）

**做法**：上层只有 `SuperconductorProperties[]`。Tc 和其他物性统一为记录；Context 是可共享
关联。Tc 继续写 `tc_results`，其他物性写 `superconductor_properties`；λ、ωlog、μ* 从
Context 数值列迁为通用物性行。

**优点**：

- 满足完整平级领域结构；
- 保留 Tc 强约束、索引和图表查询；
- 每条参数可拥有独立 Evidence；
- Context 只承担“怎么计算/测量”，职责更单一；
- 新物性只扩展定义目录，不修改上层结构。

**代价**：

- 需要统一适配器和一次定点 Schema/数据迁移；
- 数据库中 `superconductor_properties` 表仍不包含 Tc，留下领域名与物理表名不完全一致的命名债务；
- 兼容期必须谨慎去重旧 Context 参数列。

**结论**：采用。该方案以最小必要迁移换取真实的单一领域契约。

## 5. Context 表达决策

### 决策

每条记录携带可选 Context 对象；同一 Context 使用系统管理的 `context_key` 关联。该键是草稿
和响应范围内的关联键，不是数据库 ID，也不由用户填写。

### 原因

- 完全删除关联会让不同 μ* 下的多个 Tc 无法配对。
- 将 Context 重新放到材料状态顶层会让表单和 API 再次要求调用方手工组装。
- 把 Context 完整嵌入每条记录可以保持记录自描述；后端按 `context_key` 去重持久化。

### 一致性要求

相同 `context_key` 的内容必须一致。前端共享编辑器应以一个 Context 草稿对象同步更新所有
关联记录，避免用户看到重复输入框；API 即使收到重复对象，也必须在持久化前验证一致性。

## 6. λ、ωlog、μ* 所有权决策

### 决策

λ、ωlog、μ* 是物性/物理参量记录，不再属于 `CalculationContext` 的值字段。结果专属的方法
原文和判据同样归单条物性；Context 只保存可共享的计算或实验条件。

### 原因

Context 回答“在什么结构、软件、方法和网格下计算”，物性记录回答“得到了什么结果”。把
结果放进 Context 会造成：

- 参数没有独立 Evidence；
- 无法用统一值/单位模型查询；
- 页面解除分组而持久化仍旧分组；
- 同一 Context 下未来扩展 DOS、声子频率或能隙时继续增加专用列。

## 7. 兼容与迁移决策

- 旧输入在边界转换一次；内部逻辑只认统一结构。
- 新写入不双写 Context 参数列。
- 数据库迁移将旧非空参数回填为通用物性行并核对数量。
- 迁移不复制不确定的 Tc Evidence，缺失证据进入显式报告。
- Tc 专用表和 Evidence 表保留，不进行物理合表。
- 详情响应完成切换后不继续输出旧科学字段。

## 8. 关键文件

| 文件 | 作用 |
| --- | --- |
| `backend/models.py` | Context、Tc、通用物性和 Evidence ORM |
| `backend/ingest/upload_jobs.py` | AI 输出和旧草稿归一化 |
| `backend/ingest/scientific_drafts.py` | 上传正式持久化 |
| `backend/services/scientific_draft_rewrite.py` | 管理端读取与整体重写 |
| `backend/api/rag.py` | 上传草稿校验和接口边界 |
| `goserver/models/models.go` | GORM 科学模型 |
| `goserver/handlers/papers.go` | 论文详情和搜索读取 |
| `goserver/handlers/stats.go` | Tc 图表专用查询 |
| `frontend/src/lib/paperProcessing.ts` | 上传草稿 TypeScript 契约 |
| `frontend/src/components/MaterialStatesEditor.tsx` | 上传与管理共享编辑器 |
| `frontend/src/lib/paperDetailView.ts` | 当前三来源展示聚合 |
| `frontend/src/pages/AdminPaperEditPage.tsx` | 管理端详情到草稿映射 |
