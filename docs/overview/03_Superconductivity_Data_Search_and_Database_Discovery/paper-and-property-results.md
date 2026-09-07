# 论文与物性结果

## 功能说明

把材料检索命中项组织为论文、超导体和物性记录结果，供详情展示、统计与审核功能复用。

## 当前行为

- 详情 API 同时返回材料状态下的 `property_modules[].records[]`。检索投影优先读取统一记录的固定核心列，
  并将记录内 Conditions、参数和定义版本原样提供给详情和导出；迁移窗口内旧 `tc_results`、
  `superconductor_properties` 仍作为兼容回退。
- `GET /api/papers/{paper_id}/material-states/{state_key}/export` 返回同一 revision 的离线 JSON 包，
  包含材料、状态、结构、模块记录和定义快照，不暴露管理员审计字段。

- 新上传提交链路写入条件化目标模型：`material_states` 保存压力与论文报告的空间群，`calculation_contexts` 保存 λ/ωlog，`tc_results` 保存理论或实验 Tc，`superconductor_properties` 只保存 Tc 之外的普通物性。
- 材料状态不再保存含义不清的 `phase_label`、Material family 或 `superconductor_kind`；论文顶层保存单选 Superconductor type，空间群是结构事实，`More type labels` 继续由状态级结构家族关联表达。
- 结果主链路为 `papers` 与条件化科学实体：论文保存 DOI、标题、作者、年份、摘要、审核状态和 LLM 富化字段；普通物性保存材料原文名、规范物性名、数值（原文值与解析值）、单位与条件说明。压强与温度属材料状态、结构文本属 `structure_models`，都不在物性上重复承载。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- Go API `GET /api/papers/:id` 在论文顶层返回全部 `material_families[]` 与 `superconductor_kind`，并返回普通物性以及按材料状态嵌套的 `structure_families[]`、`tc_results`、`calculation_contexts` 与 `structures`；状态对象不再返回 `material_family` 或 `superconductor_kind`，`tc_max` 由 `tc_results` 聚合。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)、[Issue #79](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/79)、[Issue #80](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/80)）
- Go API `POST /api/papers/search/records` 返回扁平列表行，包含 `record_id`、`paper_id`、`year`、`formula`、`type`、`pressure`、`tc`、`space_group`、`source`、`status`、`doi` 等字段。
- `/search` 页面单击或选择记录后可显示详情；如果记录有 `paper_id`，会请求论文详情；结构预览的数据源是材料状态下的 `structures`。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）**#57 确立的是 API 契约，前端直到 Issue #65 才真正照此读取**——在此之前探索页与社区页仍读 `key_properties[].structure_text`，该字段在 Go 侧标记 `gorm:"-"` 从不落库，结构预览恒显示「暂无结构数据」。
- 探索页与社区页的关键物性表覆盖三类来源，顺序为 Tc（`tc_results`）→ 计算参数（`calculation_contexts` 的 λ/ωlog/μ*）→ 普通物性（`superconductor_properties`）。Tc 排最前是因为它是超导论文的核心结论，而非按存储顺序排列。此前两页只读 `key_properties`，只报告 Tc 的实验论文（超导领域最常见的一类）整块显示「该论文暂无结构化物性数据」，用户上传的核心数据完全不可见。计算参数中数值为 NULL 的项不产生表格行——后端返回全部记录是为了不擅自判定有效性，展示侧渲染空行则对读者无意义。物性与结构的提取逻辑收敛到 `frontend/src/lib/paperDetailView.ts`：同一读取错误此前在详情页、探索页、社区页各存一份，Issue #59 只修了详情页那份。社区页另新增结构预览区块（此前完全没有）。（[Issue #65](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/65)）
- 探索页默认不预选任何元素，Formula 输入框默认为空；仅当 URL 显式带 `elements` 参数时才预选。此前无参时兜底为 `La,H`，会把检索静默限定在氢化物体系，用户未必察觉自己并非在做全库检索。（[Issue #65](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/65)）
- 论文总结（`summary`）与核心发现（`key_finding`）在探索页、社区页均以 `pre-wrap` 渲染，保留用户按「一个要点一行」录入的换行。这两个字段的换行是内容结构而非排版噪声：库中以真实 `\n` 存储、API 原样透传，缺失 `pre-wrap` 时 HTML 折叠空白符，分条要点被挤成一段连续文本，编号还在但结构不可读。展示侧只负责不折叠换行，不对内容做 trim 或改写。详情页 `PaperEditView` 对 `abstract`、`summary`、`key_finding`、`research_motivation` 四个字段一直设了 `pre-wrap`，两个检索页此前都没有，同一份数据三个页面呈现不一致。`tests/03_.../multiline-text-preserved.test.tsx` 断言 computed `white-space` 而非 DOM 文本——后者在未修复时也含 `\n`（是 CSS 折叠了它），属恒真断言抓不到缺陷；该用例经反向验证，移除样式后即失败。（[Issue #68](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/68)）
- 不对这两个字段做 Markdown 渲染：保留换行已满足可读性，而 Markdown 会改变内容语义（`1.` 被重排为有序列表、下划线与星号被吃掉）。用户录入的是纯文本分条，展示侧不重新解释它。（[Issue #68](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/68)）
- 详情区块内标签与正文的层级约定：标签用 `caption`（12px/600），长文本正文（论文总结、核心发现）用 `body2` 并显式覆盖为 12px 且不加粗，短值字段（DOI、年份、期刊、标题）保持 `body1`（14px）加粗。长文本与短值的呈现差异是按内容长度分的两类——短值加粗帮助快速定位，大段文字加粗则妨碍阅读。此前核心发现的 `Typography` 漏写 `variant` 落到默认 `body1`（14px）又显式加粗，比自己的标签大 2px、同字重，视觉层级颠倒。字号字重的回归测试须在 `ThemeProvider` 下测量——MUI 默认 `body2` 是 14px，不套主题会量到默认值而得出错误结论，`vitest.config.ts` 因此补了 `@mui/material` 别名。（[Issue #69](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/69)）
- 知识图谱节点使用专用标题（`knowledge_graph_title`），限 15-30 字，高度凝练论文核心贡献和历史地位，取代冗长的原始标题（如 "Further experiments with liquid helium. V. The disappearance of the resistance of mercury" → "首次发现超导体 Hg"）。MySQL `papers` 表添加 `knowledge_graph_title` VARCHAR(200) 字段，AI 提取时自动生成（修改 `backend/ai_services/summary.py` 的 `SUMMARY_SYSTEM_PROMPT`，要求突出核心发现、材料体系、历史地位），审批通过后同步到 Neo4j（修改 `backend/rag.py` 的 `publish_paper_to_neo4j()`）。知识图谱 API（`backend/api/kg_live.py`）优先返回 `knowledge_graph_title`，对已有论文优雅降级到 `title`（使用 `paper.knowledge_graph_title or paper.title`）。前端无需修改，API 契约保持向后兼容（只是 `nodes[].label` 字段的值改变）。数据库迁移脚本为 `alembic/versions/20260831_175226_add_knowledge_graph_title.py`。已有论文可手工优化：`UPDATE papers SET knowledge_graph_title = '首次发现超导体 Hg' WHERE id = 9;`（P2）。详细实现见 `docs/knowledge-graph-title-feature.md`。（[Issue #70](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/70)）

## 工作流程

材料检索先确定候选超导体；Go API 以 `tc_results` 为主体关联材料状态与论文并生成扁平结果；前端把本地与外部来源适配为统一视图。详情阶段再按论文 ID 加载完整论文、普通物性与按材料状态嵌套的科学数据，供详情卡片、结构预览、审核编辑和图表点击抽屉复用。

## 约束

- Go 搜索与详情的读取投影已切换到条件化表，与上传写入契约对齐；新旧契约并存阶段结束。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- 结果准确性取决于 `tc_results`、`material_states`、`superconductors`、`papers` 的关联关系和审核状态。
- `superconductor_records` 仅在 `backend/models.py` 中保留模型定义，运行数据库已无该表（`alembic/versions/20260821_0008_add_superconducting_data_model.py` 已 `drop_table`）。任何读取路径都不得再查该表：曾有图表接口继续查它而未检查查询错误，导致接口长期静默返回空数组。（[Issue #72](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/72)）
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
- [Issue #68：修复探索页与社区页核心发现、论文总结丢失用户录入的换行](../../specs/68-preserve-multiline-text/spec.md)
- [Issue #69：修复长文本正文字号字重压过标签导致视觉层级颠倒](../../specs/69-detail-text-hierarchy/spec.md)
- [Issue #70：知识图谱节点专用标题 - 高度凝练论文核心贡献](../../specs/70-knowledge-graph-title/spec.md)
- [Feature #79：论文级 Material family 多选分类](../../specs/79-paper-material-families/spec.md)
- [Feature #80：论文级 Superconductor type 单选分类](../../specs/80-paper-superconductor-kind/spec.md)

## 已知问题

- 本地列表行的空间群字段当前为占位值，完整结构字段需要从详情或结构接口继续读取。
- 结果表格行的 Tc 列（`SearchPage` 结果聚合链路）仍按 `key_properties` 展开临界温度，与详情读取是不同路径，其正确性尚未核实。（[Issue #65](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/65) 遗留）
- 详情页 `PaperEditView` 未改用 `lib/paperDetailView.ts`，仍保留自己的一份提取实现（Issue #59 已修为正确来源，本次不动以免影响其验收判据）。
