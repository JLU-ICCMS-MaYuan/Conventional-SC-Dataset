# 实施任务：News 自动采集 scheduler 与 worker 部署

- [x] T001 在 `tests/07_researcher_community_forum/test_news_compose.py` 编写 Compose 服务命令、环境、依赖、重启策略和上传 Worker 隔离测试。
- [x] T002 修改 `docker/compose.yaml`，新增 `news-scheduler` 与 `news-worker` 服务并配置最小运行依赖。
- [x] T003 运行 `PYTHONPATH=/home/mayuan/code/SC-Wiki /home/mayuan/miniconda3/envs/sc-wiki/bin/pytest -s -q tests/07_researcher_community_forum/test_news_scheduler.py tests/07_researcher_community_forum/test_news_compose.py` 和 `docker compose -f docker/compose.yaml config`。
- [x] T004 实现验证后更新 `docs/overview/news.md` 与 Issue #86 Documentation Impact。
