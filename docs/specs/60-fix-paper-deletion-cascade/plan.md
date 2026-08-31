# 实施计划：修复超级管理员删除文献操作的级联删除

**GitHub Issue**：[#60](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/60)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

当前删除论文的实现（`DeletePaper` 和 `BatchDelete`）只删除 `key_properties` 和 `papers` 表，导致大量孤儿数据。本计划重构删除逻辑，在应用层实现完整的级联删除，覆盖 MySQL 的 9 张关联表，并同步清理 Qdrant 向量库和 Neo4j 图数据库。

**技术方案**：
1. 在 Go 后端创建新的删除服务函数 `CascadeDeletePaper`，使用事务保证原子性
2. 调用 Python FastAPI 的内部端点清理 Qdrant 和 Neo4j
3. 重构 `DeletePaper` 和 `BatchDelete` 函数调用新服务
4. 添加集成测试验证级联删除完整性

## 技术上下文

- **语言与版本**：Go 1.21+（后端）、Python 3.10+（FastAPI）
- **主要依赖**：
  - Go：GORM（ORM）、Gin（HTTP 框架）
  - Python：FastAPI、SQLAlchemy、qdrant-client、neo4j-driver
- **数据存储**：
  - MySQL（主业务数据）
  - Qdrant（向量库）
  - Neo4j（知识图谱）
  - Redis（缓存）
- **测试体系**：
  - Go 单元测试：`go test ./goserver/...`
  - Go 集成测试：`go test ./goserver/handlers/... -tags=integration`
  - Python 测试：`pytest backend/tests/`
- **目标平台**：Docker Compose 部署环境（Nginx + Go + Python + MySQL + Qdrant + Neo4j）
- **性能目标**：
  - 单个删除操作 < 5 秒（包含外部清理）
  - 批量删除 10 篇论文 < 30 秒
  - 事务回滚 < 1 秒
- **约束**：
  - 必须使用数据库事务保证 MySQL 删除的原子性
  - Qdrant/Neo4j 清理失败时不应回滚 MySQL 事务（已删除数据无法恢复）
  - 向后兼容现有 API 契约（路径、请求/响应格式不变）
- **规模范围**：
  - 预期单次批量删除 < 100 篇论文
  - 单篇论文关联数据：材料状态 1-10 个，Tc 结果 1-50 个，结构 0-10 个

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| AGENTS.md | 修改完成后自动执行 git commit | 实现完成并通过测试后提交 | 待验证 |
| Spec FR-006 | 使用事务保证 MySQL 删除原子性 | 使用 `db.Transaction()` 包裹所有 MySQL 删除操作 | 设计满足 |
| Spec SC-001 | 删除后所有关联记录不存在 | 集成测试验证 9 张表的记录数为 0 | 待实现 |
| Spec SC-002/SC-003 | 删除后 Qdrant 和 Neo4j 数据不存在 | 调用 Python 内部端点，集成测试验证 | 待实现 |
| Overview | 保持 Go 和 Python 服务边界清晰 | Go 负责 MySQL 删除，Python 提供 Qdrant/Neo4j 清理端点 | 设计满足 |

## Feature 文档结构

```text
docs/specs/60-fix-paper-deletion-cascade/
├── spec.md          ✅ 已完成
├── plan.md          ✅ 当前文档
├── research.md      （下一步）
├── tasks.md         （下一步）
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
goserver/
├── handlers/
│   ├── admin.go                    [重构] DeletePaper 调用新服务
│   ├── stats.go                    [重构] BatchDelete 调用新服务
│   └── paper_deletion.go           [新增] CascadeDeletePaper 服务函数
├── models/
│   └── models.go                   [无需修改] 数据模型已完整
└── main_test.go 或 handlers/*_test.go [新增] 集成测试

backend/
├── api/
│   └── admin_internal.py           [新增] 内部管理端点
└── rag/
    ├── vectordb.py                 [已存在] delete_paper_chunks
    └── tools/
        └── neo4j.py                [新增] delete_paper_from_graph 函数
```

**结构选择**：
- **新文件 `paper_deletion.go`**：集中删除逻辑，避免 `admin.go` 和 `stats.go` 过大
- **Python 内部端点**：Go 通过 HTTP 调用 Python，保持服务边界清晰
- **事务边界**：只在 MySQL 删除中使用事务，外部清理在事务外异步执行

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001（级联删除 9 张表） | `CascadeDeletePaper()` 函数，按依赖顺序删除 | 集成测试：删除后查询各表记录数 = 0 |
| FR-002（清理 Qdrant） | `DELETE /internal/papers/{id}/vectors` Python 端点 | 集成测试：调用 Qdrant API 查询 paper_id 返回空 |
| FR-003（清理 Neo4j） | `DELETE /internal/papers/{id}/graph` Python 端点 | 集成测试：Cypher 查询 `Paper {paper_id}` 返回空 |
| FR-004（保留 upload_tasks） | `UPDATE upload_tasks SET paper_id = NULL` | 单元测试：验证 `upload_tasks` 记录存在且 `paper_id` 为 NULL |
| FR-005（保留 superconductors） | 不删除 `superconductors` 表，只删除 `material_states` | 单元测试：验证 `superconductors` 记录仍存在 |
| FR-006（事务保证） | `db.Transaction(func(tx *gorm.DB) error {...})` | 单元测试：模拟中途失败，验证回滚 |
| FR-007（清理缓存） | 删除成功后调用 `cache.FlushPattern()` | 手动测试：验证统计数据更新 |
| FR-008（批量删除独立处理） | `BatchDelete` 循环调用 `CascadeDeletePaper`，捕获单个错误 | 集成测试：部分失败时其他论文仍被删除 |
| FR-009（明确错误信息） | 返回不同错误码：404（论文不存在）、500（数据库错误）、502（外部服务错误） | 单元测试：验证错误响应格式 |
| US1（单个删除） | `DeletePaper` → `CascadeDeletePaper` | E2E 测试：前端删除后刷新列表，论文消失 |
| US2（批量删除） | `BatchDelete` → 循环 `CascadeDeletePaper` | E2E 测试：批量删除后统计数据更新 |

## 阶段与依赖

### 阶段 1：研究与设计（1 小时）
- 确认所有关联表的外键关系（查看 GORM 模型和数据库 Schema）
- 设计删除顺序（避免外键约束冲突）
- 设计 Python 内部端点契约

### 阶段 2：实现 MySQL 级联删除（2 小时）
- 创建 `goserver/handlers/paper_deletion.go`
- 实现 `CascadeDeletePaper(tx *gorm.DB, paperID uint) error`
- 实现 `cleanUploadTasks(tx *gorm.DB, paperID uint) error`
- 编写单元测试验证删除顺序和事务回滚

### 阶段 3：实现外部服务清理（2 小时）
- 在 `backend/api/admin_internal.py` 创建内部端点
- 实现 Qdrant 清理（复用 `delete_paper_chunks`）
- 实现 Neo4j 清理（新增 `delete_paper_from_graph`）
- 在 `CascadeDeletePaper` 中调用 Python 端点

### 阶段 4：重构现有删除函数（1 小时）
- 修改 `DeletePaper` 调用 `CascadeDeletePaper`
- 修改 `BatchDelete` 调用 `CascadeDeletePaper`
- 保持 API 契约不变

### 阶段 5：集成测试与验证（2 小时）
- 编写集成测试：创建论文 → 删除 → 验证所有表为空
- 编写集成测试：批量删除 → 验证统计数据更新
- 编写集成测试：中途失败 → 验证事务回滚
- 手动测试：前端删除操作，验证用户体验

### 阶段 6：文档与提交（30 分钟）
- 更新 `docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md`
- 记录删除行为变更
- 执行 git commit

**依赖关系**：
- 阶段 2 和阶段 3 可并行进行
- 阶段 4 依赖阶段 2 和阶段 3 完成
- 阶段 5 依赖阶段 4 完成

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|------------|------------|--------------------------|
| 应用层级联删除而非数据库外键 CASCADE | 需要调用外部服务（Qdrant/Neo4j）清理，数据库外键无法触发应用逻辑；需要保留 `upload_tasks` 而非删除；需要记录审计日志 | 使用 `ON DELETE CASCADE`：无法执行自定义清理逻辑，无法区分保留和删除的表 |
| 分两阶段提交（MySQL 事务 + 外部清理） | Qdrant/Neo4j 清理失败时，MySQL 数据已不可恢复，强制回滚会导致数据不一致；外部服务清理失败应记录日志而非阻塞删除 | 全部放入一个分布式事务：Go 缺乏分布式事务支持，Qdrant/Neo4j 不支持事务；失败率高且难以调试 |
| 循环调用而非批量 SQL | 每篇论文需要独立清理外部服务，无法通过单个 SQL 批量处理；单个失败不应影响其他论文 | 单个批量 DELETE：无法为每篇论文独立清理 Qdrant/Neo4j；一个失败导致全部回滚 |

## 外部服务清理契约

### Python 内部端点：删除论文向量

**请求**：
```http
DELETE /internal/papers/{paper_id}/vectors
Authorization: Bearer <jwt_token>
```

**响应**：
```json
{
  "deleted_chunks": 15,
  "message": "向量已删除"
}
```

**错误**：
- 404：论文不存在（可忽略，认为已删除）
- 503：Qdrant 服务不可用

### Python 内部端点：删除论文图节点

**请求**：
```http
DELETE /internal/papers/{paper_id}/graph
Authorization: Bearer <jwt_token>
```

**响应**：
```json
{
  "deleted_nodes": 1,
  "deleted_relationships": 8,
  "message": "图节点已删除"
}
```

**错误**：
- 404：论文不存在（可忽略）
- 503：Neo4j 服务不可用

## 删除顺序设计

基于外键依赖关系，删除顺序如下：

```text
1. paper_evidences        (依赖 paper_id)
2. paper_chunks           (依赖 paper_id)
3. paper_review_events    (依赖 paper_id)
4. tc_results             (依赖 material_state_id，间接依赖 paper_id)
5. calculation_contexts   (依赖 material_state_id)
6. experimental_contexts  (依赖 material_state_id)
7. structures             (依赖 material_state_id)
8. material_states        (依赖 paper_id)
9. key_properties         (依赖 paper_id)
10. UPDATE upload_tasks SET paper_id = NULL WHERE paper_id = ?
11. DELETE FROM papers WHERE id = ?
```

**事务保证**：
- 步骤 1-11 在一个 MySQL 事务中执行
- 外部清理（Qdrant/Neo4j）在事务提交后执行
- 外部清理失败时记录日志但不回滚 MySQL 事务

## 测试策略

### 单元测试（Go）
1. 测试 `CascadeDeletePaper` 删除顺序
2. 测试事务回滚（模拟中途失败）
3. 测试 `cleanUploadTasks` 保留任务记录
4. 测试 `superconductors` 未被删除

### 集成测试（Go + MySQL）
1. 创建完整论文数据 → 删除 → 验证 9 张表为空
2. 创建共享超导材料的两篇论文 → 删除一篇 → 验证 `superconductors` 仍存在
3. 批量删除 → 验证统计数据更新

### 集成测试（Go + Python + Qdrant + Neo4j）
1. 创建论文并发布到向量库和图数据库 → 删除 → 验证外部数据清理
2. 模拟 Qdrant 不可用 → 删除论文 → 验证 MySQL 已删除但返回警告

### E2E 测试（手动）
1. 前端删除单篇论文 → 刷新列表 → 验证论文消失
2. 前端批量删除 → 验证统计卡片数据更新
3. 删除有记录的论文 → 验证记录数清零且论文消失

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 外部服务清理失败导致数据不一致 | Qdrant/Neo4j 存在孤儿数据 | 中 | 记录日志，提供手动清理脚本；考虑后台异步重试机制 |
| 删除顺序错误导致外键约束冲突 | 删除失败，事务回滚 | 低 | 单元测试验证删除顺序；手动检查数据库外键约束 |
| 大批量删除超时 | 用户体验差，可能触发超时 | 低 | 限制单次批量删除数量（前端 UI 提示）；考虑异步任务 |
| 并发删除导致数据竞争 | 同一论文被删除两次 | 极低 | 事务隔离级别 + 404 错误处理 |

## 回滚计划

如果上线后发现严重问题，回滚步骤：

1. 恢复旧版 `DeletePaper` 和 `BatchDelete` 函数（仅删除 `papers` 和 `key_properties`）
2. 部署回滚代码
3. 如果有论文被错误删除，从数据库备份恢复

**预防措施**：
- 上线前完整执行集成测试
- 第一周监控删除操作的错误日志
- 确保数据库备份策略到位
