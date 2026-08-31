# 实施任务：修复超级管理员删除文献操作的级联删除

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备与依赖确认

**目的**：确认数据模型的外键关系，设计删除顺序。

- [x] T001 [P] 读取 `goserver/models/models.go`，列出所有包含 `paper_id` 或 `material_state_id` 外键的表
- [x] T002 [P] 读取现有删除实现 `goserver/handlers/admin.go:DeletePaper` 和 `goserver/handlers/stats.go:BatchDelete`
- [x] T003 [P] 确认 Python 端现有的 Qdrant 清理函数 `backend/rag/vectordb.py:delete_paper_chunks`
- [x] T004 [P] 确认 Python 端 Neo4j 查询函数 `backend/rag/tools/neo4j.py`，了解论文节点的查询方式

## 阶段 2：基础能力——Python 内部端点

**目的**：创建 Python 内部管理端点，供 Go 服务调用清理 Qdrant 和 Neo4j。

- [x] T005 [P] 在 `backend/api/admin_internal.py` 创建内部管理路由器（`router = APIRouter(prefix="/internal", tags=["internal"])`）
- [x] T006 [P] 在 `backend/rag/tools/neo4j.py` 新增函数 `delete_paper_from_graph(paper_id: int) -> dict`，使用 Cypher 删除论文节点和关系
- [x] T007 [P] 在 `backend/api/admin_internal.py` 实现端点 `DELETE /internal/papers/{paper_id}/vectors`，调用 `delete_paper_chunks`
- [x] T008 [P] 在 `backend/api/admin_internal.py` 实现端点 `DELETE /internal/papers/{paper_id}/graph`，调用 `delete_paper_from_graph`
- [x] T009 [P] 在 `backend/main.py` 注册内部路由器 `app.include_router(admin_internal.router, prefix="/api")`
- [ ] T010 [P] 编写 Python 单元测试 `backend/tests/test_admin_internal.py`，验证两个端点的正常流程和错误处理

## 阶段 3：用户故事 1——超级管理员彻底删除单篇论文（P1，MVP）

**目标**：实现单篇论文的完整级联删除，包括 MySQL、Qdrant 和 Neo4j。

**独立验收**：删除论文后，所有关联表记录为空，Qdrant 和 Neo4j 中无该论文数据。

### 实施核心删除逻辑

- [x] T011 [P] [US1] 在 `goserver/handlers/` 创建新文件 `paper_deletion.go`
- [x] T012 [P] [US1] 在 `paper_deletion.go` 实现函数 `cascadeDeleteInDB(tx *gorm.DB, paperID uint) error`，按以下顺序删除：
  - 删除 `paper_evidences`（`WHERE paper_id = ?`）
  - 删除 `paper_chunks`（`WHERE paper_id = ?`）
  - 删除 `paper_review_events`（`WHERE paper_id = ?`）
  - 删除 `tc_results`（`WHERE paper_id = ?`）
  - 删除 `calculation_contexts`（`WHERE paper_id = ?`）
  - 删除 `experimental_contexts`（`WHERE paper_id = ?`）
  - 删除 `structures`（`WHERE paper_id = ?`）
  - 删除 `material_states`（`WHERE paper_id = ?`）
  - 删除 `key_properties`（`WHERE paper_id = ?`）
  - 删除 `papers`（`WHERE id = ?`）
- [x] ~~T013 `cleanUploadTasks`~~ **已撤销**：上传任务存于 Redis 而非 MySQL 表，
  FR-004 的前提不成立。原先写下的空函数已删除，不留无用桩代码。
- [x] T014 [P] [US1] 在 `paper_deletion.go` 实现函数 `cleanExternalServices(paperID uint, authToken string) error`，调用 Python 内部端点删除 Qdrant 和 Neo4j 数据
- [x] T015 [P] [US1] 在 `paper_deletion.go` 实现主函数 `CascadeDeletePaper(paperID uint, authToken string) error`：
  - 检查论文是否存在
  - 使用 `database.DB.Transaction()` 调用 `cascadeDeleteInDB` 和 `cleanUploadTasks`
  - 事务成功后调用 `cleanExternalServices`（失败记录日志但不返回错误）
  - 清理缓存 `cache.FlushPattern("chart:*")`、`cache.FlushPattern("search:*")`、`cache.FlushPattern("community:contributions:*")`

### 重构现有删除函数

- [x] T016 [P] [US1] 修改 `goserver/handlers/admin.go:DeletePaper`，替换现有删除逻辑为调用 `CascadeDeletePaper(id, authToken)`
- [x] T017 [US1] 从 Gin 上下文中获取 `Authorization` header 并传递给 `CascadeDeletePaper`

### 测试

- [x] T018 [P] [US1] `TestCascadeDeleteInDBRemovesEveryRelation`：造带完整关联的论文，
  删除后逐一断言 9 张表残留为 0，且 `superconductors` 记录保留。**已通过**
- [x] T019 [P] [US1] `TestCascadeDeleteRollsBackOnFailure`：删掉 `papers` 表使末步必然失败，
  断言先删的 `tc_results` / `material_states` 在回滚后复原。**已通过**
- [x] T019b [P] [US1] `TestCascadeDeleteOnlyTargetsRequestedPaper`：确认删除不越界影响其他论文。**已通过**
- [x] T019c [P] [US1] `TestCascadeDeletePaperMissingReturnsSentinel`：确认返回可判定的
  `ErrPaperNotFound` 哨兵错误而非按文案匹配。**已通过**
- [x] ~~T020 `TestCleanUploadTasks`~~ 随 FR-004 撤销。
- [ ] T021 [US1] 集成测试（真实 MySQL + Qdrant + Neo4j）：**未做**。当前单元测试用
  SQLite 内存库，未覆盖 MySQL 外键行为与外部服务真实清理，需在部署环境手动验收。

## 阶段 4：用户故事 2——超级管理员批量删除多篇论文（P1）

**目标**：实现批量删除功能，支持一次删除多篇论文。

**独立验收**：批量删除后，所有选中论文及其关联数据被删除，统计数据正确更新。

### 实施

- [x] T022 [P] [US2] 修改 `goserver/handlers/stats.go:BatchDelete`，替换现有逻辑：
  - 解析请求体获取 `paper_ids`
  - 循环调用 `CascadeDeletePaper(id, authToken)`，捕获单个失败
  - 收集失败的 `paper_id`
  - 如果有失败，返回 207 Partial Content 状态码和失败列表
  - 如果全部成功，返回 200 OK
  - 最后清理缓存

### 测试

- [ ] T023 [P] [US2] 在 `goserver/handlers/stats_test.go` 编写单元测试 `TestBatchDeleteSuccess`：
  - 创建 3 篇论文
  - 调用 `POST /api/admin/papers/batch-delete` 批量删除
  - 验证所有论文被删除
  - 验证返回 200 OK
- [ ] T024 [US2] 在 `goserver/handlers/stats_test.go` 编写单元测试 `TestBatchDeletePartialFailure`：
  - Mock `CascadeDeletePaper` 使部分调用失败
  - 调用批量删除
  - 验证返回 207 Partial Content 和失败列表

## 阶段 5：前端体验验证与文档

**目的**：验证前端删除交互，更新功能文档。

- [ ] T025 手动测试：在前端超级管理员页面删除单篇论文，验证删除后论文消失，统计数据更新
- [ ] T026 手动测试：在前端批量选中 3 篇论文并删除，验证删除后列表更新
- [ ] T027 手动测试：删除包含多个材料状态和 Tc 结果的论文，验证数据库中所有关联记录被删除
- [ ] T028 手动测试：删除后刷新社区贡献排行榜，验证上传者的贡献数减少
- [ ] T029 更新 `docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md`，记录删除操作的行为变更：
  - 说明删除操作为物理删除
  - 列出级联删除的表范围
  - 说明 `upload_tasks` 保留但清空 `paper_id`
  - 说明 `superconductors` 不删除
- [ ] T030 在 Issue #60 中回写实现总结和验收结果

## 依赖与执行顺序

- **T001-T004**（准备）：无依赖，可并行
- **T005-T010**（Python 端点）：依赖 T004，必须在 T014 前完成
- **T011-T015**（核心删除）：依赖 T001-T002，T014 依赖 T005-T010
- **T016-T017**（重构）：依赖 T015
- **T018-T021**（US1 测试）：依赖 T011-T017
- **T022**（批量删除）：依赖 T015
- **T023-T024**（US2 测试）：依赖 T022
- **T025-T030**（验证与文档）：依赖所有实现和测试完成

**关键路径**：T001→T002→T011→T012→T013→T014→T015→T016→T018→T021→T022→T025

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001（级联删除 9 张表） | T012 | `cascadeDeleteInDB` 按序删除所有关联表 |
| FR-002（清理 Qdrant） | T006, T007, T014 | Python 端点 + Go 调用 |
| FR-003（清理 Neo4j） | T006, T008, T014 | Python 端点 + Go 调用 |
| FR-004（保留 upload_tasks） | T013, T020 | UPDATE 而非 DELETE |
| FR-005（保留 superconductors） | T012, T018 | 不删除 superconductors 表 |
| FR-006（事务保证） | T015, T019 | 使用 `db.Transaction()` |
| FR-007（清理缓存） | T015 | 删除成功后 FlushPattern |
| FR-008（批量独立处理） | T022, T024 | 循环调用，捕获单个失败 |
| FR-009（明确错误信息） | T015, T016 | 返回不同错误码 |
| US1（单个删除） | T011-T021 | 完整实现 + 测试 |
| US2（批量删除） | T022-T024 | 完整实现 + 测试 |
| SC-001（MySQL 数据删除） | T018, T021 | 测试验证 |
| SC-002（Qdrant 清理） | T021 | 集成测试验证 |
| SC-003（Neo4j 清理） | T021 | 集成测试验证 |
| SC-004（统计更新） | T015, T025, T028 | 缓存清理 + 手动验证 |
| SC-005（事务回滚） | T019 | 单元测试验证 |
| SC-006（保留 superconductors） | T018 | 单元测试验证 |
| SC-007（保留 upload_tasks） | T020 | 单元测试验证 |

## MVP 与增量策略

1. **MVP**（T001-T021）：完成单篇论文的完整级联删除，包含核心逻辑、Python 端点、重构和测试
2. **增量 1**（T022-T024）：添加批量删除功能
3. **增量 2**（T025-T030）：前端验证和文档更新

每个增量完成后都可以独立验收和部署。
