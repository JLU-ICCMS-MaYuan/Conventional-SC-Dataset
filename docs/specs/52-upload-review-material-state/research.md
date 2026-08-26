# 技术决策记录：上传校对页布局重构与材料状态卡片完善

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## D1：空间群标准表来源于 spglib 运行时构建

- **决策**：新增 `backend/services/space_groups.py`，模块加载时遍历 `spglib.get_spacegroup_type(hall_number)`（hall 1–530）去重生成 230 条「国际符号 ↔ 群号」只读映射；替换 `upload_jobs.py:690` 的 2 条硬编码 `SPACE_GROUP_NUMBERS`；通过 `GET /api/rag/space-groups` 向前端提供完整列表。
- **理由**：spglib 是晶体对称性权威数据源，已随 pymatgen 传递安装；运行时构建避免提交生成物、随 spglib 升级自动更新。
- **备选**：提交静态 JSON 快照（多一份需维护的生成物，拒绝）；pymatgen `SpacegroupOperations`（引入更重对象模型，拒绝）。
- **证据**：`backend/ingest/upload_jobs.py:690-693, 918-924`；`requirements.txt:40-42`。

## D2：元素种类数「锁定」语义

- **决策**：草稿材料状态新增 `element_count_locked`（布尔，默认 false）。`_normalize_material_states` 规则：锁定 → 不动；未锁定 → 先严格 `normalize_formula`，失败再用宽松元素提取（见 D3），仍失败 → 保留已有非空值（AI 提取），不得置空。前端手动编辑即置锁定；服务端/AI 填充不置锁定。提交入库 `scientific_drafts.py:204` 改为：草稿值非空用草稿值，否则 `count_formula_elements(material)`。
- **理由**：满足「手动值不被覆盖」（spec FR-004），同时用户改化学式后未锁定值可自动更正；比「非空即不重算」更不容易滞留错误。
- **备选**：非空即不重算（用户改化学式后残留旧值，拒绝）；无锁定全靠服务端（违背 FR-004，拒绝）。
- **证据**：`backend/ingest/upload_jobs.py:862-867`、`backend/ingest/scientific_drafts.py:204`、`backend/api/rag.py:753-759`（PUT/GET 均走规范化）。

## D3：宽松元素提取处理变量化学式

- **决策**：`backend/db_helpers.py` 新增 `extract_formula_elements_loose(formula) -> list[str]`：剔除括号及其内容、空白与常见单位后缀后，按 `[A-Z][a-z]?` 扫描并校验为合法元素符号，去重返回（`LaHx (x = 1–12) 150 GPa` → `[La, H]`）。仅在严格 `normalize_formula` 抛 `ValueError` 时作为回退使用。
- **理由**：变量计量比（x）不影响「元素种类数」语义；回退策略不改动严格路径的既有行为与测试。
- **备选**：改造 `parse_formula_composition` 支持变量（影响面大、化学计量语义被稀释，拒绝）；交给 AI（不确定，仅作最终回退）。
- **证据**：`backend/db_helpers.py:45-100`；`backend/ingest/upload_jobs.py:696-714`（`_formula_from_material` token 回退对 `LaHx` 同样失败）。

## D4：Tc 方法 = 受控枚举 + `tc_method_custom` 自由文本列

- **决策**：`tc_method` CHECK 约束扩展为 `('experimental','mcmillan','allen_dynes','isotropic_eliashberg','anisotropic_eliashberg','scdft','other','unknown')`；新增 `tc_results.tc_method_custom VARCHAR(128) NULL` 保存「其他」的自由文本。前端下拉 5 预设 + 其他；AI 契约（summary prompt）同步加入 scdft/other；AI 不知道填 `unknown`。
- **理由**：保留枚举完整性；自定义方法可持久化、可修改。
- **备选**：自定义文本直接写 tc_method 并删约束（弱化完整性，拒绝）。
- **证据**：`backend/models.py:1279-1288`；`backend/ingest/upload_jobs.py:138`。

## D5：常规 Tc 逐条 CalculationContext，非常规回退状态级共享

- **决策**：草稿 `DraftTcResult` 新增可选 `calculation_context`（λ、ωlog、μ\*、evidence）。提交时：Tc 条目带专属 context（三值至少一个非空）→ 逐条创建 CalculationContext 并关联；否则沿用现状（状态级 context 存在则共享关联）。`ck_tc_results_context_kind`（theoretical 必挂 context）自然满足。材料状态级 λ/ωlog 输入框从前端移除；旧草稿状态级值仅在前端「添加常规 Tc」时预填一次，不做后端数据迁移。
- **理由**：DB 外键与约束已支持；预填方案避免对 24h 临时草稿写迁移逻辑。
- **备选**：后端 GET 时自动把状态级值并入首条 Tc（多一条永久兼容分支，拒绝）。
- **证据**：`backend/models.py:1253-1263, 1289-1305`；`backend/ingest/scientific_drafts.py:315-385`。

## D6：超导类型存 material_states.superconductor_kind

- **决策**：新增 `superconductor_kind VARCHAR(32) NOT NULL DEFAULT 'unknown'`，CHECK `IN ('conventional','unconventional','unknown')`；goserver `MaterialState` 结构体与 `materialStatesToDict` 同步；管理员审核页展示可改、不阻塞批准。UI 标签「常规 (BCS) / 非常规 / 未知」。
- **理由**：属于材料状态级科学维度，与材料家族正交（spec 关键实体）；默认值兼容历史行。
- **备选**：并入材料家族目录（混淆维度、需目录治理，拒绝）；仅存草稿不入库（审核与查询不可用，拒绝）。
- **证据**：`backend/models.py:790-923`；`goserver/models/models.go:259-291`。

## D7：research_materials 提交时自动汇总

- **决策**：`_create_pending_paper` 构造 Paper 前，用材料状态化学式去重汇总覆盖 `research_materials`（汇总为空时保留草稿原值）；`_validate_draft` 的非综述必填校验改为「草稿值或汇总值任一非空即通过」。前端删除该输入框及其 AI 建议块。
- **理由**：用户确认的方向；材料状态已是化学式权威来源，消除重复录入。
- **证据**：`backend/api/rag.py:208-308, 928-996`。

## D8：折叠为前端会话状态，默认「≤2 张全展开，否则仅首张展开」

- **决策**：`UploadTaskEditor` 内维护 `collapsed: Record<number, boolean>`（不入草稿）；卡片头整行可点击切换；组头「全部折叠/全部展开」按钮；默认规则见标题。
- **理由**：spec 边界场景明确折叠为视觉状态；默认规则兼顾少量卡片无打扰与大量卡片可控。
- **备选**：持久化到草稿（污染自动保存契约，拒绝）。

## D9：空间群符号前端控件复用 MUI Autocomplete（freeSolo）

- **决策**：在 `UploadTaskEditor.tsx` 内用 MUI `Autocomplete freeSolo` 实现空间群符号输入（选项来自 D1 接口，选中自动带群号），不新建独立组件文件——结构与现有结构家族 Autocomplete 几乎一致，内联即可。
- **理由**：KISS；`ClassificationAutocomplete` 绑定分类目录 API 形状，不适配空间群 DTO，复用成本高。
- **证据**：`frontend/src/components/UploadTaskEditor.tsx:709-734`；`frontend/src/components/ClassificationAutocomplete.tsx`（props 为分类目录形状）。

## D10：AI 提取扩展只动 SUMMARY prompt，不升 CHUNK 契约版本

- **决策**：超导类型判断与 energy above hull 提取加入 `SUMMARY_SYSTEM_PROMPT`（含 thermodynamically stable → 0 规则与 tc_method 新枚举）；`CHUNK_SYSTEM_PROMPT` 与 `CHUNK_RESULT_SCHEMA_VERSION=5` 不变。
- **理由**：两者均可由全文汇总直接判断，无需分段证据新字段；避免版本升级触发的全量重读。
- **备选**：分段级提取（需 bump 版本、缓存失效成本高，拒绝）。
- **证据**：`backend/ingest/upload_jobs.py:83, 91-146`；Overview「分段分类结果带内部契约版本」。
