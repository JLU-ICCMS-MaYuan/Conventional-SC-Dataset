# 快速验证

1. 在 SC-Wiki 仓库启动 Docker Compose，确认 Nginx、Go、Python、数据库和 Neo4j 健康。
2. 上传一个超过 1 MB 的 PDF，确认请求成功或显示明确体积错误。
3. 上传理论主导、实验主导、综述和理论实验同等重要的 fixture，检查整体类型、理论二级类型、理由和证据。
4. 上传包含未知材料体系的 PDF，选择 AI 建议或手动新类型，确认论文可提交且显示待审核。
5. 以管理员审核该类型，验证接受、修改、合并、拒绝四条路径。
6. 注入抽取、LLM、数据库异常，确认前端显示失败原因且不显示成功。
7. 运行后端 pytest、前端测试，并查看容器日志确认无 `paper_is_experimental`、`infer_sc_type` 或 `rebuild_from_clean_results` 导入错误。
