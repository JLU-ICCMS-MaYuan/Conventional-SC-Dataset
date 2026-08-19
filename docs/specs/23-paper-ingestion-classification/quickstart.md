# 快速验证

1. 启动 Compose，确认 Nginx、Go、Python API、RQ Worker、Redis AOF、MySQL、Neo4j 和 Qdrant 健康。
2. 上传 PDF，确认返回 `202 + task_id`，并能看到五阶段和真实分段进度。
3. 在宿主机确认 `data/upload_PDFs`、`data/parsed_markdown`、`data/review_artifacts` 产物；重建容器后文件仍存在。
4. 刷新页面恢复任务，等待草稿后修改字段；确认停止输入 5 秒自动保存和立即保存均可恢复。
5. 上传理论主导、实验主导、综述和理论实验同等重要 fixture，检查类型、理论二级类型、理由和证据。
6. 提交草稿，确认 MySQL 原子写入并进入 `pending`；管理员对照证据修改材料类型并执行通过、保持待审核或拒绝。
7. 注入抽取、LLM、Redis、数据库异常，确认失败阶段与原因准确，重试只处理失败/未完成段。
8. 验证重复 DOI、相同/不同哈希、管理员候选附件下载、24 小时清理、公开检索隔离和 PDF/Markdown 不公开。
9. 运行 Python、Go、前端测试和构建，检查日志不再访问 `dev.db`。
