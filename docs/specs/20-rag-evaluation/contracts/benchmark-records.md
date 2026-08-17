# Benchmark 数据契约

## 版本

所有 JSONL 顶层记录必须包含 `schema_version`。不兼容变更提升主版本；读取器必须拒绝未知主版本。

## 消融组

- `llm_only`：无工具、无检索上下文、独立新会话。
- `qdrant_only`：仅 `search_literature`。
- `qdrant_mysql`：增加 `query_properties`。
- `qdrant_mysql_neo4j`：再增加五个 Neo4j 工具。

## 原始记录

每行是一条 RunRecord，至少含 experiment/question/group/repetition 标识、配置与数据快照哈希、输入、答案、引用、工具事件、状态、错误、重试、usage 和 latency。写入采用排他创建；目标 experiment 目录存在即失败。

## 错误语义

区分 `configuration_error`、`dependency_unavailable`、`timeout`、`tool_error`、`stream_interrupted`、`invalid_event`、`empty_answer` 与 `evaluation_error`。首次失败不得因重试成功而删除。

## PDF Gate

`formal` 记录必须引用已冻结数据集，且每个 gold evidence 含完整 PDF locator 与哈希；否则 runner 返回 `pdf_gate_failed`。
