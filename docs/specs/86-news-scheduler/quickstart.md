# 验证指南：News 自动采集部署

```bash
pytest -q tests/07_researcher_community_forum/test_news_scheduler.py tests/07_researcher_community_forum/test_news_compose.py
docker compose -f docker/compose.yaml config
```

预期：测试确认两个 News 服务与上传 Worker 隔离；Compose 成功渲染。部署时执行现有 `docker compose up -d` 即会启动新增服务，无需手工运行资讯命令。
