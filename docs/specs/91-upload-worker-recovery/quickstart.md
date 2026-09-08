# 快速验收：上传 Worker 版本漂移恢复

## 前置条件

- 本地 Redis 在 `127.0.0.1:6379` 运行。
- Python 环境为 `/home/mayuan/miniconda3/envs/sc-wiki`。
- 使用独立 Redis DB 15 执行边界测试，且该 DB 为空。

## 场景 1：RQ 导入失败收敛为可重试状态

```bash
UPLOAD_TEST_REDIS_URL=redis://127.0.0.1:6379/15 \
  /home/mayuan/miniconda3/envs/sc-wiki/bin/python -m pytest -q \
  tests/01_decentralized_uploading/test_issue91_upload_worker_recovery.py
```

预期：真实 RQ Worker 消费一个导入失败的入口，测试观察到 `status=failed`、稳定错误码和
原失败阶段；终态保护测试同时通过。

## 场景 2：本地 Worker 使用源码监视器

```bash
bash scripts/dev.sh restart worker
bash scripts/dev.sh status
```

预期：`worker` 为运行中，进程树包含 `watchfiles` 和其管理的
`backend.scripts.run_upload_workers`。修改任一 `backend/**/*.py` 后，后者 PID 在 10 秒内
变化，监督进程 PID 保持不变。

## 场景 3：当前解析入口可导入

```bash
set -a
source .env
set +a
/home/mayuan/miniconda3/envs/sc-wiki/bin/python -c \
  'from rq.utils import import_attribute; import_attribute("backend.ingest.upload_jobs.process_upload_task")'
```

预期：命令退出码为 0。

## 场景 4：恢复两条已知任务

定向恢复后检查：

- 两条任务的 `job_id` 均不同于旧失败 job；
- Worker 日志或分段总数证明状态曾进入 `extracting` 和 `reading`，而不是停留在 `queued`；
- `.data/upload_PDFs/<task_id>/` 中的原始文件仍存在；
- Worker 日志出现两个新 job 的实际消费记录。

## 回归

```bash
set -a
source .env
set +a
/home/mayuan/miniconda3/envs/sc-wiki/bin/python -m pytest -q \
  tests/01_decentralized_uploading/test_issue24_api_routes.py \
  tests/07_researcher_community_forum/test_news_compose.py \
  tests/07_researcher_community_forum/test_news_scheduler.py \
  backend/tests/test_upload_workflow.py \
  backend/tests/test_upload_jobs.py
```

预期：全部通过，上传主流程、共享 RQ 生命周期和 Docker Worker 命令契约没有回归。
