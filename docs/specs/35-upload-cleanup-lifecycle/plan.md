# 实施计划：上传任务分层清理与待审核快照生命周期

**GitHub Issue**：[#35](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/35)

**日期**：2026-08-21

**Spec**：[spec.md](spec.md)

## 摘要

在现有上传任务仓库内拆分临时数据、未提交文件和 duplicate 候选清理；提交事务成功后保留
精简审核快照并释放 Redis/RQ/分段缓存；审核完成后由 Go 调用幂等清理接口删除快照。新增
Redis 状态契约版本和一次性旧状态迁移，撤销上传任务 GET 的长期 MySQL 兼容。

## 技术上下文

- **语言与版本**：Python 3.12、TypeScript/React、Go 1.25
- **主要依赖**：FastAPI、SQLAlchemy、Redis、RQ、GORM
- **数据存储**：Redis 任务状态与队列、MySQL 正式论文、受管文件目录
- **测试体系**：pytest，Go testing，React/Vitest，Docker Compose 运行时核验
- **目标平台**：Linux Docker Compose
- **性能目标**：任务列表和详情对 Paper 表零查询；清理操作与任务文件数量线性相关
- **约束**：正式文件零误删；MySQL 故障 fail-closed；部署制品可追溯；不扩展 #33 Schema
- **规模范围**：每用户最多 100 个活动任务，每任务一个正文和多个附件

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| #25 | Redis 任务中心，清理前永久认领检查 | GET 纯 Redis，文件清理先查 MySQL | 通过 |
| #28 | duplicate 动作由服务端产生，论文接口最终鉴权 | Worker 写 Redis，点击统一 GET | 通过 |
| #33 | 正式 File/Chunk/Evidence 和审核事件保持永久边界 | 仅清理临时快照和处理中间产物 | 通过 |
| AGENTS.md | 先测后改、范围明确、文档同步 | 专项行为测试和 Overview 回写 | 通过 |

## Feature 文档结构

```text
docs/specs/35-upload-cleanup-lifecycle/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cleanup-lifecycle.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
backend/ingest/upload_contracts.py
backend/ingest/upload_tasks.py
backend/ingest/upload_jobs.py
backend/api/upload_tasks.py
backend/api/rag.py
backend/scripts/migrate_upload_task_states.py
goserver/handlers/admin.go
tests/01_decentralized_uploading/test_issue35_cleanup_lifecycle.py
tests/01_decentralized_uploading/test_issue35_duplicate_contract.py
docs/overview/06-rag-literature-assistant/pdf-ingestion.md
```

**结构选择**：状态规则继续放在纯契约模块；Redis/RQ/文件删除由上传任务仓库集中拥有；正式
提交和审核快照 API 保留在现有 RAG Router；Go 审核 Handler 只负责在事务成功后触发清理。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001–FR-011 / US1–US3 | 三类清理函数、CleanupContext、提交恢复 | 临时目录 + FakeRedis/RQ + SQLite/MySQL 边界测试 |
| FR-004–FR-007 / US2 | ReviewSnapshot 和审核后 DELETE | Python API 与 Go Handler 测试 |
| FR-012–FR-015 / US4 | schema_version、Worker 写入、一次性迁移 | Redis 状态和容器源码契约测试 |
| FR-016 / US1 | upload_task_id 幂等恢复 | 提交响应丢失回归测试 |

## 阶段与依赖

1. 建立清理、幂等提交和 duplicate 契约失败测试。
2. 实现状态契约版本、清理上下文和三类清理原语。
3. 接入提交成功和未提交到期路径。
4. 接入审核快照 revision 校验及审核后删除。
5. 实现并执行旧 duplicate 一次性迁移。
6. 撤销读时 MySQL 补丁，验证部署契约并重建 API/Worker。
7. 回写 Overview 和 Issue，按代码、测试、部署三层验收。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|------------|------------|--------------------------|
| 最小清理上下文 | Redis state 会与 cleanup_at 同时过期 | 到期时再读 state 会漏掉 RQ Job 和候选副本 |
| 审核快照独立保留 | 管理员仍需 AI/用户差异 | 提交后删除会破坏审核，永久入库又扩大 #33 |
| 一次性旧状态迁移 | 运行中已有旧 Worker 快照 | 每次 GET 查 MySQL 会改变任务中心事实来源 |
| 提交幂等恢复 | MySQL commit 与 HTTP 响应之间可能失败 | 只依赖 Redis 会在清理后错误返回 404 |
