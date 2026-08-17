# 实施任务：Mentor RAG 分层评测与工具消融

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备

- [x] T001 在 `tests/05_rag_question_answering/README.md` 建立评测入口、状态声明和本机命令。
- [x] T002 [P] 在 `tests/05_rag_question_answering/benchmark/schemas/` 建立版本化配置、问题与 run record schema 骨架；完整 gold evidence schema 随 PDF Gate 实施。
- [x] T003 [P] 在 `tests/05_rag_question_answering/fixtures/` 建立不含真实论文内容的确定性小型 fixture。

## 阶段 2：基础能力

- [ ] T004 在 `tests/05_rag_question_answering/unit/` 先写 Qdrant score 语义回归测试，再修复 `backend/rag/vectordb.py` 与 `backend/rag/search/vector_search.py`。
- [ ] T005 在 `tests/05_rag_question_answering/unit/` 先写四组工具隔离测试，再将 `backend/rag/agent/mentor.py` 改为参数化 graph 构建。
- [ ] T006 [P] 在 `tests/05_rag_question_answering/unit/` 先写属性结果测试，再让 `backend/rag/tools/mysql.py` 与 Agent wrapper 保留范围、单位和条件。
- [ ] T007 [P] 在 `tests/05_rag_question_answering/unit/` 先写方向契约测试，再修复 `backend/rag/tools/neo4j.py` 和 Agent wrapper 的有向路径输出。
- [ ] T008 在 `tests/05_rag_question_answering/benchmark/runners/` 实现不可覆盖 Experiment writer、配置哈希、错误分类和 usage ledger。

## 阶段 3：用户故事 1——本机验证评测骨架（P1，MVP）

**独立验收**：无外部服务时运行 quickstart，schema、fixture、指标和隔离测试全部通过。

- [ ] T009 [P] [US1] 在 `tests/05_rag_question_answering/benchmark/metrics/` 实现 Recall@k、MRR、nDCG@k 与多证据覆盖率测试。
- [ ] T010 [P] [US1] 在同一目录实现 S2 类型化数值/单位/条件指标测试。
- [ ] T011 [P] [US1] 在同一目录实现 S3 节点、边、路径、方向和证据覆盖指标测试。
- [ ] T012 [US1] 验证 `python -m pytest tests/05_rag_question_answering -q` 不依赖外部服务且不泄露 `.env`。

## 阶段 4：用户故事 2——开发性 S1–S5（P2）

**独立验收**：本机四组运行产生唯一 provisional experiment 和完整派生产物。

- [ ] T013 [US2] 在 `tests/05_rag_question_answering/benchmark/runners/mentor.py` 实现四组 MentorBenchmarkRunner。
- [ ] T014 [P] [US2] 在 `tests/05_rag_question_answering/benchmark/runners/sse.py` 实现 8000/8080 SSE 解析、文本 TTFT、错误和一次重试。
- [ ] T015 [P] [US2] 在 `tests/05_rag_question_answering/benchmark/metrics/statistics.py` 实现问题级配对 bootstrap 与 Holm 校正。
- [ ] T016 [US2] 在 `tests/05_rag_question_answering/integration/` 运行本机 development 测试并保存不可覆盖 JSONL、CSV 和错误样例。

## 阶段 5：用户故事 3——PDF Gate 与正式实验（P3）

**独立验收**：任一 gold evidence 均能回查原始PDF且pilot一致性门通过。

- [ ] T017 [US3] 在原始 PDF 到位后建立只读 manifest、SHA-256 与页数清单，禁止重新切块。
- [ ] T018 [US3] 保持现有 chunk 边界，建立页码/段落/bbox 旁路对齐与低置信人工复核队列。
- [ ] T019 [US3] 制作20题双人独立标注pilot并计算一致性；不达0.80则修订规范重跑。
- [ ] T020 [US3] 冻结120/160/200题之一、模型/价格/数据快照和统计协议，执行正式四组配对实验。
- [ ] T021 [US3] 输出全部预注册指标、95% CI、错误样例、延迟、token和成本，并在开发机独立复现。

## 最终阶段：完善与跨故事事项

- [ ] T022 更新 `docs/overview/06-rag-literature-assistant/` 的已实现行为并回写 Issue Documentation Impact。
- [ ] T023 对照 Spec、Plan、Tasks 和 quickstart 执行 converge，记录未完成项且不关闭 Issue。

## 依赖与执行顺序

- T001–T003 是本轮骨架；T004–T008 阻断真实 runner。
- US1 可在 PDF 缺失时完成；US2 只能产生 development/provisional 结果。
- US3 严格依赖 PDF Gate、US1、US2 与双人领域标注资源。
- 不同硬件环境使用独立 experiment ID，不合并延迟。

## 需求覆盖

| 来源 | 任务 | 说明 |
|---|---|---|
| FR-001–FR-005 / US1 | T002–T012 | schema、fixture与确定性组件指标 |
| FR-006–FR-009 / US2 | T005、T008、T013–T016 | 消融、账本、SSE与统计 |
| FR-010–FR-016 / US3 | T017–T021 | PDF证据、pilot与正式实验 |
| FR-017–FR-018 / US1 | T001、T012 | 目录、密钥与本机验证 |

## MVP 与增量策略

1. 本轮完成并提交 T001–T003 的最小骨架。
2. 下一阶段按 T004–T012 完成可人工复算的离线 MVP。
3. 外部服务可用后实施 US2；PDF Gate 通过后才能实施 US3。
