# 实施计划：Mentor RAG 分层评测与工具消融

**GitHub Issue**：[\#20](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/20)

**日期**：2026-08-17

**Spec**：[spec.md](spec.md)

## 摘要

在现有 Mentor、Qdrant、MySQL、Neo4j 和 SSE 链路之外建立独立 benchmark 层。先用 schema 与确定性 fixture 在个人电脑验证指标和工具隔离，再接入真实服务；PDF 到位并通过证据门后才制作 pilot 与正式集。

## 技术上下文

- **语言与版本**：Python 3.10/3.12；现有 Go 与前端不在首批骨架修改范围。
- **主要依赖**：pytest、LangGraph、Qdrant client、SQLAlchemy、Neo4j driver、现有 OpenAI 兼容模型客户端。
- **数据存储**：不可变 JSONL 原始记录、CSV 派生结果、外部数据库快照与 PDF manifest。
- **测试体系**：pytest；目录 `tests/05_rag_question_answering/`。
- **目标平台**：个人电脑先验证；后续开发机独立重跑。
- **性能目标**：报告可用率、SSE完整率、文本TTFT和总延迟 p50/p95；绝对 SLO 在 pilot 后冻结。
- **约束**：PDF 缺失；密钥仅在被忽略的 `.env`；正式结果不可覆盖；不混入 Inspiration Agent。
- **规模范围**：20题 pilot，正式候选 120/160/200 题，四个消融组，最多一次固定重试。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| AGENTS.md | Feature 关联 Issue 与编号 Spec | Issue #20、双向链接 | 通过 |
| Overview | 区分检索、SSE、PDF 摄入与能力依赖 | S1–S5 分层且不改写当前事实 | 通过 |
| Spec | PDF Gate | formal runner 前置检查 | 阻断正式实验，不阻断骨架 |
| Spec | 工具物理隔离 | 参数化 graph/runner | 待实施 |
| 安全 | 密钥不得入库 | `.env` 与日志脱敏测试 | 待实施 |
| 统计 | 预注册比较与配对单位 | 配置冻结、Holm、配对 bootstrap | 待实施 |

## Feature 文档结构

```text
docs/specs/20-rag-evaluation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/benchmark-records.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
backend/rag/agent/mentor.py
backend/rag/agent/tools.py
backend/rag/search/vector_search.py
backend/rag/tools/mysql.py
backend/rag/tools/neo4j.py
tests/05_rag_question_answering/
├── benchmark/
│   ├── configs/
│   ├── metrics/
│   ├── runners/
│   └── schemas/
├── fixtures/
├── integration/
├── unit/
└── README.md
```

**结构选择**：运行时代码只做必要的依赖注入和结构化输出修复；所有评测专用逻辑置于用户指定的测试目录，避免污染生产服务。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001–FR-005 / US1 | schema、S1–S3 metrics、fixture | 离线 pytest 与人工算例 |
| FR-002、FR-006 / US2 | 参数化 Mentor graph 与 runner | 四组工具隔离测试 |
| FR-007 / US2 | SSE smoke runner | 8000/8080 分层集成测试 |
| FR-008–FR-009 / US2 | Experiment writer、usage ledger | 不可覆盖与字段完整性测试 |
| FR-010–FR-016 / US3 | dataset schema、PDF Gate | schema 校验与 gate 测试 |
| FR-017–FR-018 / US1 | 配置加载与目录骨架 | secret 扫描、quickstart |

## 阶段与依赖

1. **Phase 0：计划与离线骨架**。建立文档、schema、fixture 和最小测试入口；个人电脑可执行。
2. **Phase 1：评测有效性修复**。先写回归测试，再修 Qdrant score、工具注入、MySQL 条件输出、Neo4j方向契约和稳定标识。
3. **Phase 2：S1–S5开发性运行**。冻结本机配置与快照，输出 provisional JSONL/CSV；不得作为正式科学结论。
4. **PDF Gate**。取得全部原始PDF，建立manifest与chunk旁路对齐，低置信证据人工复核。
5. **Phase 3：20题pilot**。双人独立标注、裁决、judge校准、重复运行和样本量精度分析。
6. **Phase 4：正式实验**。冻结协议和120/160/200样本量之一，执行四组配对实验、统计和错误分析。
7. **Phase 5：开发机复现**。以独立 experiment ID 重跑S5和正式任务，不合并不同硬件延迟。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|---|---|---|
| 独立 runner/evaluator | 避免 Mentor 自评与组名偏差 | 在 Mentor 内直接打分会混合职责 |
| 不可变原始记录 | 支持审计、失败保留和统计复算 | 覆盖 CSV 会丢失轨迹 |
| PDF Gate | 科研证据必须回查原文 | 数据库自证无法验证科学正确性 |
