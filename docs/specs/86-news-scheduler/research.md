# 技术调研：News 自动采集部署

**GitHub Issue**：[ #86](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/86)

## 证据与决策

1. `backend.news.scheduler.schedule_forever` 每分钟调用一次调度检查，默认时区为 `Asia/Shanghai`、小时为 8；无成功记录、过期成功记录、超时运行或失败超过一小时的来源会入队。
2. `backend.news.__main__` 提供 `schedule` 和 `worker` 两个长期运行命令；Worker 只绑定 `scwiki-news`。
3. 当前 Compose 仅有上传 `worker`，命令是 `backend.scripts.run_upload_workers`，不会消费资讯队列。
4. `docker/python.Dockerfile` 已复制 `backend/` 并安装运行依赖，因此新增服务复用 `mayuanmark/scwiki-python:mayuan`，无需制作新镜像。

**决策**：新增独立 `news-scheduler`、`news-worker` 服务；仅注入 News 所需的数据库、Redis 和调度参数。这样队列职责清晰，不将上传任务、LLM 配置或基础设施依赖复制到资讯服务。
