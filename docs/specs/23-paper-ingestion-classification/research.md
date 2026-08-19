# 技术研究：论文全文解析与 LLM 自动分类

## 决策

1. 论文分类使用“核心贡献与服务关系”，不使用实验关键词计数。
2. 文本按段/章节读取，分段提取证据后再汇总，避免上下文长度限制。
3. 论文整体 `paper_type` 与物性 `article_type` 独立。
4. 材料类型保留常用建议但允许自定义；新类型先待审核。
5. 失败返回明确错误，不写失败历史垃圾记录，也不显示假成功。
6. 使用 RQ 复用现有 Redis；不引入 Celery，也不手写 Redis Streams。
7. 任务状态和草稿存 Redis，审核证据存临时 JSON，正式候选数据仅在用户提交时写入 MySQL。
8. 原始 PDF、Markdown 和审核产物使用三个独立挂载目录；新上传流程停用 SQLite `dev.db`。
9. Python API 与 Worker 共用镜像；Redis 开启 AOF；前端每 2 秒轮询真实进度。
10. LLM 通过统一 OpenAI 兼容客户端调用，供应商、地址和模型均来自环境配置。

## 理由与备选

- 只读摘要：实现简单但无法判断理论/实验谁为主，拒绝。
- 仅按化学式判材料：无法覆盖掺杂、复合、界面和特殊体系，拒绝。
- 固定材料枚举：会阻塞新体系，拒绝。
- 自动永久加入新类型：会造成同义词污染，拒绝。
- 把处理状态和 AI 证据写入 MySQL：审核完成后无长期业务价值，拒绝。
- 在 FastAPI 进程内 `asyncio.create_task`：容器重启丢任务且无法断点恢复，拒绝。
- 为材料类型新增全局目录和别名表：超出当前明确需求，推迟到后续 Spec。

## 已验证事实

现有 `extractor.py` 使用 `theoretical/experimental/review/unknown`，`enrich_papers.py` 使用另一套 `calculate/method/experiment/review`；`KeyProperty.article_type` 使用 `e/t`。实现时必须保留边界含义并建立兼容映射。

现有上传路径写入 `/app/data/uploads` 并在处理结束删除，而 Compose 只挂载 `/data/uploads`；`clean_results` 也存在同类错位。现有 `PaperChunk` 模型未被新上传链路写入，富化却读取容器内不存在的 SQLite `dev.db`。
