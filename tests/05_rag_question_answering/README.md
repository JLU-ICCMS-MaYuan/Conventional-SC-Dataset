# RAG 问答与评测测试

本目录承载 Issue #20 的 Mentor RAG 分层评测。当前只包含 Phase 0 离线骨架，不调用 LLM、Qdrant、MySQL、Neo4j、FastAPI 或 Go，也不读取 `.env`。

## 状态边界

- 当前状态：`development`。
- 原始 PDF 尚未取得，PDF Gate 未通过。
- 本目录中的合成 fixture 只验证数据契约和工具隔离配置，不产生科学质量结论。

## 本机运行

```bash
cd /home/mayuan/code/SC-Wiki
python3 -m pytest tests/05_rag_question_answering/unit/test_benchmark_scaffold.py -q
```

预期结果：全部测试通过，且无需启动任何外部服务。

## 目录

```text
benchmark/
├── configs/       # 四组固定消融配置
├── metrics/       # 后续 S1–S4 指标实现
├── runners/       # 后续实验与 SSE runner
└── schemas/       # 版本化 JSON Schema
fixtures/          # 不含真实论文内容的确定性 fixture
integration/       # 后续真实服务测试
unit/              # 离线单元测试
```

完整需求、计划和任务见 `docs/specs/20-rag-evaluation/`。
