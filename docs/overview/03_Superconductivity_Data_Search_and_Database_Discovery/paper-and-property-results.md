# 论文与物性结果

## 功能说明

把材料检索命中项组织为论文、超导体和物性记录结果，供详情展示、统计与审核功能复用。

## 当前行为

- 新上传提交链路写入条件化目标模型：`material_states` 保存压力与论文报告的空间群，`calculation_contexts` 保存 λ/ωlog，`tc_results` 保存理论或实验 Tc，`superconductor_properties` 只保存 Tc 之外的普通物性。
- 材料状态不再保存含义不清的 `phase_label`；空间群是结构事实，未来结构家族分类另行建模。
- 结果主链路为 `papers` 与条件化科学实体：论文保存 DOI、标题、作者、年份、摘要、审核状态和 LLM 富化字段；普通物性保存材料原文名、规范物性名、数值（原文值与解析值）、单位与条件说明。压强与温度属材料状态、结构文本属 `structure_models`，都不在物性上重复承载。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- Go API `GET /api/papers/:id` 返回论文详情、普通物性，以及按材料状态嵌套的 `tc_results`、`calculation_contexts` 与 `structures`；`tc_max` 由 `tc_results` 聚合。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- Go API `POST /api/papers/search/records` 返回扁平列表行，包含 `record_id`、`paper_id`、`year`、`formula`、`type`、`pressure`、`tc`、`space_group`、`source`、`status`、`doi` 等字段。
- `/search` 页面单击或选择记录后可显示详情；如果记录有 `paper_id`，会请求论文详情；结构预览的数据源是材料状态下的 `structures`。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）**#57 确立的是 API 契约，前端直到 Issue #65 才真正照此读取**——在此之前探索页与社区页仍读 `key_properties[].structure_text`，该字段在 Go 侧标记 `gorm:"-"` 从不落库，结构预览恒显示「暂无结构数据」。
- 探索页与社区页的关键物性表覆盖三类来源，顺序为 Tc（`tc_results`）→ 计算参数（`calculation_contexts` 的 λ/ωlog/μ*）→ 普通物性（`superconductor_properties`）。Tc 排最前是因为它是超导论文的核心结论，而非按存储顺序排列。此前两页只读 `key_properties`，只报告 Tc 的实验论文（超导领域最常见的一类）整块显示「该论文暂无结构化物性数据」，用户上传的核心数据完全不可见。计算参数中数值为 NULL 的项不产生表格行——后端返回全部记录是为了不擅自判定有效性，展示侧渲染空行则对读者无意义。物性与结构的提取逻辑收敛到 `frontend/src/lib/paperDetailView.ts`：同一读取错误此前在详情页、探索页、社区页各存一份，Issue #59 只修了详情页那份。社区页另新增结构预览区块（此前完全没有）。（[Issue #65](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/65)）
- 探索页默认不预选任何元素，Formula 输入框默认为空；仅当 URL 显式带 `elements` 参数时才预选。此前无参时兜底为 `La,H`，会把检索静默限定在氢化物体系，用户未必察觉自己并非在做全库检索。论文总结以 `pre-wrap` 渲染，保留库中原有换行，与详情页行为一致。（[Issue #65](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/65)）

## 工作流程

材料检索先确定候选超导体；Go API 以 `tc_results` 为主体关联材料状态与论文并生成扁平结果；前端把本地与外部来源适配为统一视图。详情阶段再按论文 ID 加载完整论文、普通物性与按材料状态嵌套的科学数据，供详情卡片、结构预览、审核编辑和图表点击抽屉复用。

## 约束

- Go 搜索与详情的读取投影已切换到条件化表，与上传写入契约对齐；新旧契约并存阶段结束。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- 结果准确性取决于 `tc_results`、`material_states`、`superconductors`、`papers` 的关联关系和审核状态。
- `superconductor_records` 模型仍存在，但当前 Go 搜索主链路使用 `tc_results` 与 `material_states`。
- 外部来源详情字段不与本地论文字段完全等价，前端会按来源差异兜底显示缺失字段。

## 代码与测试

- `goserver/handlers/papers.go`
- `goserver/models/models.go`
- `backend/models.py`
- `frontend/src/pages/SearchPage.tsx`
- `frontend/src/components/StructureViewer3D.tsx`
- `tests/03_data_search_and_database_discovery/`

## 相关变更记录

- [Feature #46：论文上传科学数据结构化](../../specs/46-upload-scientific-data-pipeline/spec.md)
- [Issue #57：详情与搜索读取投影切换到条件化表，消除恒零值字段](../../specs/57-paper-detail-data-parity/spec.md)
- [Issue #65：修复探索页与社区页默认选中、总结换行、Tc 与结构读废弃字段致恒空](../../specs/65-search-detail-source-fixes/spec.md)

## 已知问题

- 本地列表行的空间群字段当前为占位值，完整结构字段需要从详情或结构接口继续读取。
- 结果表格行的 Tc 列（`SearchPage` 结果聚合链路）仍按 `key_properties` 展开临界温度，与详情读取是不同路径，其正确性尚未核实。（[Issue #65](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/65) 遗留）
- 详情页 `PaperEditView` 未改用 `lib/paperDetailView.ts`，仍保留自己的一份提取实现（Issue #59 已修为正确来源，本次不动以免影响其验收判据）。
