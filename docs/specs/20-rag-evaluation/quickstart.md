# Quickstart：个人电脑验证 RAG 评测骨架

## 前置条件

- 位于分支 `mayuan-RAGtest`。
- 使用项目已有 Python 环境。
- `.env` 可存在但离线骨架测试不得读取或打印其中的密钥。
- PDF Gate 当前未通过，因此只能运行 development/provisional 场景。

## Phase 0 离线验证

```bash
cd /home/mayuan/code/SC-Wiki
python3 -m pytest tests/05_rag_question_answering -q
```

预期：schema、配置、fixture 和确定性指标测试通过；不要求启动 Qdrant、MySQL、Neo4j、LLM、FastAPI 或 Go。

## 后续开发性集成验证

按 `.env.example` 与本地 `.env` 启动项目现有依赖，然后分别验证 FastAPI 8000 与 Go 8080。具体命令在 Phase 2 实现时补充；在命令可执行前不得把任务标记完成。

## 结果限制

原始 PDF 未取得前，任何真实语料运行必须包含 `status=development` 或 `status=provisional`，不得标记为 formal，也不得对外宣称科学质量结论。
