# Feature 规格：提交审核压强区间校验与草稿保存语义修复

**GitHub Issue**：[#54](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/54)（type:bug）

**创建日期**：2026-08-26

**状态**：已实现（commit 16298c9），待镜像重建后按 quickstart 验收关闭

## 背景与目标

上传任务 `6b5bf07cac944ed6acbaa6422bdbeee7`（PNAS 2017 LaHn/YHn）提交审核返回 500：材料状态 LaH10 的压强为单臂区间（`pressure_min_gpa=200`、`pressure_max_gpa=NULL`，AI 从 "above 200 GPa" 提取），违反 `ck_material_states_pressure_range`（min/max 必须成对且 min≤max）；`_validate_draft` 无此项校验，缺口直达 INSERT。同时 PUT 草稿（5 秒自动保存）与 submit 共用同一套严格校验，半成品内容使自动保存连续 400，用户编辑从未落盘，刷新后表现为「表单全部消失」。

本 Feature 修复三点：单臂区间的数据模型与校验语义、保存与提交的校验分离、失败原因的前端可见性。

## 用户场景与验收

### 用户故事 1：单臂压强区间可正常提交（优先级：P1）

论文报告 "above 200 GPa" 这类下限压强时，AI 提取的单臂区间（min=200、max 空）在校对页不可见但合法存在，贡献者点击提交审核后正常入库，不再 500。双臂区间仍要求 min≤max，倒置时在提交前得到明确 400 指引。

**优先级理由**：这是阻断提交的主路径 bug。

**独立验收**：含 `min=200, max=NULL` 的草稿 submit 成功，`material_states` 行保留 min=200、max=NULL；`min=300, max=200` 的草稿 submit 返回 400 `invalid_pressure_range` 且提示「第 1 个材料状态」。

**验收场景**：

1. **假如** 材料状态压强 min=200、max 为空，**当** 提交审核，**那么** 入库成功且单臂值保留。
2. **假如** min=300、max=200，**当** 提交审核，**那么** 400 拒绝，错误消息定位到第 N 个材料状态，不产生 500。
3. **假如** min、max 均为空或均非空且 min≤max，**当** 提交审核，**那么** 行为与修复前一致（回归）。

### 用户故事 2：半成品草稿自动保存不丢（优先级：P1）

贡献者在校对页半填内容（如刚添加的 Tc 行还没填数值）时，5 秒自动保存正常落盘；刷新页面后内容仍在。点击提交审核时，同一半成品仍被严格校验拦截，并提示具体缺失位置。

**优先级理由**：这是「刷新后表单消失」的直接根因，影响每次校对的可用性。

**独立验收**：含空值 Tc 行的草稿 PUT 返回 200 且内容持久化；同一草稿 submit 返回 400 `tc_value_required`。

**验收场景**：

1. **假如** 草稿存在未填数值的 Tc 行，**当** 自动保存触发，**那么** PUT 200，刷新后该行仍在。
2. **假如** 同一草稿，**当** 点击提交审核，**那么** 400 拒绝并指出第 N 个材料状态的第 M 条 Tc 缺少数值。
3. **假如** 草稿 JSON 结构本身损坏，**当** 自动保存，**那么** 仍被拒绝（结构性错误不因宽松放行）。

### 用户故事 3：失败原因可见（优先级：P2）

保存或提交失败时，贡献者在错误横幅看到后端返回的具体原因（如「第 1 个材料状态的压强区间 min 不能大于 max（invalid_pressure_range）」），而不是只有 Internal Server Error。

**独立验收**：mock 后端 400 带 detail.message → 横幅显示该 message 并区分「保存失败/提交失败」；500 无 detail → 回退通用文案。

## 边界与异常场景

- 单臂语义约定：min-only 表示「≥min」，max-only 表示「≤max」；当前无任何下游消费（搜索走 `key_properties.pressure_gpa`、详情 API 仅输出 `pressure_value_gpa`、无中点/BETWEEN 计算），语义仅作存储约定，未来消费时需兑现。
- 负压强由既有 `ck_material_states_nonnegative` 拦截，不在本 Feature 新增校验。
- PUT 宽松路径仍可能因分类目录解析（非法材料维度、不存在的目录项）返回 400/404——属分类解析而非业务字段校验，保持现状。
- 数值字段的宽松解析（先 float 再正则提取）与入库路径 `_number` 语义一致，避免校验与入库判定不一致。

## 需求

### 功能需求

- **FR-001**：`ck_material_states_pressure_range` 重建为「单臂合法、双臂要求 min≤max」，即 `(pressure_min_gpa IS NULL OR pressure_max_gpa IS NULL OR pressure_min_gpa <= pressure_max_gpa)`；alembic 迁移 `20260826_0016` 与 `backend/models.py` 约束文本同步，downgrade 恢复原成对约束。
- **FR-002**：`_validate_draft` 对每个材料状态校验：min、max 均非空且 min>max 时返回 400 `invalid_pressure_range`，消息定位到第 N 个材料状态；单臂不报错。
- **FR-003**：`_validate_draft` 增加 `partial` 模式：PUT 草稿路径（partial=True）仅执行结构性检查（`invalid_draft`），跳过全部业务字段校验；submit 路径（partial=False）保持严格全集不变。
- **FR-004**：前端保存/提交失败横幅展示后端 `detail.message`（附 `code`），区分「保存失败/提交失败」；无 detail 或网络错误时回退现有通用文案；409 DOI 重复等专属文案不变。

### 关键实体

- **压强区间**：材料状态的结构化区间事实；单臂合法（≥/≤ 语义），双臂要求 min≤max。
- **草稿校验级别**：partial（保存用，仅结构）与 strict（提交用，全集）两级，同一 `_validate_draft` 参数化实现。

## 成功标准

- **SC-001**：迁移 0016 在 MySQL 8.4 upgrade/downgrade 可逆；(200,NULL)、(NULL,200)、(100,200) 可插入，(300,200) 被拒。
- **SC-002**：原失败任务 `6b5bf07c…` 在镜像重建后不重新解析即可提交成功（待验收）。
- **SC-003**：半成品草稿 PUT 200 落盘、submit 400 定位具体位置。
- **SC-004**：后端 pytest 与前端 vitest 全过，不回归 #51/#52/#53。

## 假设与依赖

- 方案 A（允许单臂入库）由需求方在 Issue #54 讨论中确认；影响面已核查（搜索/详情/聚合均不消费 min/max）。
- 依赖 #46–#53 的上传草稿主链路；不改变其他约束语义。

## 范围外事项

- 单臂区间在搜索、图表、详情页的语义化展示（当前无消费方）。
- 前端直接暴露 min/max 输入（UI 维持单值压强字段，区间来自 AI 提取）。
- dev 栈镜像重建与部署（验收前置运维操作）。

## 澄清记录

### 2026-08-26

- 问：单臂压强区间如何处理？ → 答：方案 A——放宽 CHECK 允许单臂入库（min=200, max=NULL 合法），忠实表达 "above 200 GPa"；影响面核查确认无下游消费（用户确认）。
