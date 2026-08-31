# 实施任务：知识图谱节点专用标题

**输入**：[spec.md](spec.md)、[plan.md](plan.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：数据库层 - 添加字段

**目的**：在 MySQL 添加 `papers.knowledge_graph_title` 字段，为后续 AI 生成和展示提供存储基础。

- [x] T001 在 `backend/database/models.py` 的 `Paper` 模型添加 `knowledge_graph_title = Column(String(200))` 字段
- [x] T002 生成 Alembic 迁移脚本：`alembic revision --autogenerate -m "add knowledge_graph_title"`
- [x] T003 手工审查迁移脚本 `alembic/versions/20260831_175226_*.py`，确认 `upgrade()` 和 `downgrade()` 逻辑正确
- [x] T004 在 dev 栈执行迁移：进入 backend 容器 `alembic upgrade head`
- [x] T005 验证字段已添加：`SHOW COLUMNS FROM papers LIKE 'knowledge_graph_title';` 返回 VARCHAR(200)

## 阶段 2：AI 提取层 - 生成标题

**目的**：修改 AI 提示词，让提取服务自动生成 15-30 字的凝练标题。

- [x] T006 [US2] 在 `backend/ai_services/summary.py` 的 `SUMMARY_SYSTEM_PROMPT` 添加标题生成规则
- [x] T007 [US2] 规则包含：15-30 字（中文）或 10-15 词（英文）、突出核心发现、包含材料体系、突出历史地位（"首次"/"高温"/"常压"）
- [x] T008 [US2] 在输出 JSON schema 添加 `knowledge_graph_title` 字段
- [x] T009 [US2] 手工测试：上传一篇测试 PDF，检查生成的标题是否符合规范
- [x] T010 [US2] 质量审查：标题长度适中、包含核心信息、无冗余系列编号

## 阶段 3：展示层 - API 返回新标题

**目的**：修改知识图谱 API，优先返回凝练标题，对已有论文优雅降级。

- [x] T011 [US1] 在 `backend/api/kg_live.py` 的节点构建处修改 `label` 逻辑
- [x] T012 [US1] 使用 `paper.knowledge_graph_title or paper.title` 实现 fallback
- [x] T013 [US1] curl 验证有标题的论文：`curl "http://localhost:8080/api/knowledge-graph/overview" | jq '.nodes[] | select(.id == "paper_9") | .label'` 返回凝练标题
- [x] T014 [US1] curl 验证无标题的论文：确认 fallback 到原始标题，无空值或报错

## 阶段 4：同步层 - 写入 Neo4j

**目的**：修改论文审批后的自动同步逻辑，将 `knowledge_graph_title` 同步到 Neo4j。

- [x] T015 [US2] 在 `backend/rag.py` 的 `publish_paper_to_neo4j()` 添加 `knowledge_graph_title` 字段到节点属性
- [x] T016 [US2] 确认字段名使用 snake_case（`knowledge_graph_title`）而非 camelCase
- [x] T017 [US2] 测试：发布一篇新论文，审批通过后查询 Neo4j：`MATCH (p:Paper {doi: '...'}) RETURN p.knowledge_graph_title`
- [x] T018 [US2] 验证同步成功且值正确

## 阶段 5：端到端验证

**目的**：验证完整流程从上传到展示。

- [x] T019 上传新论文 PDF（如经典超导论文）
- [x] T020 AI 提取完成后，检查提取结果 JSON 的 `knowledge_graph_title` 字段
- [x] T021 管理员审批通过论文
- [x] T022 数据库验证：`SELECT id, title, knowledge_graph_title FROM papers WHERE id = ?;`
- [x] T023 Neo4j 验证：`MATCH (p:Paper) WHERE p.id = ? RETURN p.knowledge_graph_title;`
- [x] T024 API 验证：`curl "http://localhost:8080/api/knowledge-graph/overview" | jq '.nodes[] | select(.id == "paper_?") | .label'`
- [x] T025 前端验证：浏览器访问知识图谱页面，确认节点显示凝练标题
- [x] T026 优雅降级验证：查看已有论文（无 `knowledge_graph_title`）是否正常显示原始标题

## 阶段 6：文档

**目的**：记录实现细节和使用方式，回写到项目文档。

- [x] T027 创建 `docs/knowledge-graph-title-feature.md`，记录字段定义、AI 生成规则、API 使用、手工优化方法
- [x] T028 创建 GitHub Issue [#70](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/70)
- [x] T029 编写 `docs/specs/70-knowledge-graph-title/`（spec、plan、tasks）
- [x] T030 回写 `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/paper-and-property-results.md`，添加"知识图谱标题"章节

## 依赖与执行顺序

- **T001-T005**（数据库字段）：必须最先做，否则 AI 提取和同步无处存储
- **T006-T010**（AI 生成）：依赖 T001；必须在展示层前完成，否则无数据可展示
- **T011-T014**（API 展示）：依赖 T006（有字段可读）
- **T015-T018**（Neo4j 同步）：依赖 T001；可与 T011-T014 并行
- **T019-T026**（端到端验证）：依赖全部实现完成
- **T027-T030**（文档）：依赖验证完成

**关键路径**：T001→T002→T004→T006→T011→T019→T025

## 需求覆盖

| 来源 | 任务 | 验证 |
|------|------|------|
| FR-001（数据库字段） | T001-T005 | T005、T022 |
| FR-002（AI 生成） | T006-T010 | T020、T010 质量审查 |
| FR-003（Neo4j 同步） | T015-T018 | T023 |
| FR-004（API 返回） | T011-T014 | T013、T014 |
| SC-001（知识图谱显示） | T025 | 浏览器验证 |
| SC-002（新论文自动生成） | T019-T021 | T020-T025 完整流程 |
| SC-003（优雅降级） | T012、T026 | 已有论文正常显示 |

## 遗留事项

- **历史论文批量生成**（P2）：当前只对新上传论文生成，已有 50+ 篇历史论文需手工或批量处理。可通过以下方式补充：
  ```sql
  -- 手工为重要论文添加标题
  UPDATE papers SET knowledge_graph_title = '首次发现超导体 Hg' WHERE id = 9;
  
  -- 或使用批量脚本调用 AI
  SELECT id, title, abstract FROM papers WHERE knowledge_graph_title IS NULL;
  ```

- **管理员编辑界面**（P2）：暂无手工优化标题的 UI，管理员需要直接操作数据库。未来可在论文编辑弹窗添加"知识图谱标题"输入框。

- **生成质量评估**（P3）：当前依赖人工审核，无自动化质量检测机制。可考虑：
  - 长度检测（15-30 字）
  - 必要关键词检测（材料名称、温度、压力）
  - 与原始标题的相似度（过高说明未凝练）

- **标题唯一性**（P3）：同一体系多篇论文可能生成相似标题，未做唯一性约束。可在 AI 提示词中添加"区分同类研究"规则。

## 回滚计划

如果上线后发现问题，可按以下顺序回滚：

1. **临时禁用新标题展示**：修改 `kg_live.py`，强制使用 `paper.title`
2. **停止 AI 生成**：修改 `summary.py`，移除 `knowledge_graph_title` 字段
3. **数据库回滚**：执行 `alembic downgrade -1`，删除字段

回滚不影响已有数据，因为 API 有 fallback 机制。
