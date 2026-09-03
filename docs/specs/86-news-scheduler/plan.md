# 实施计划：News 自动采集 scheduler 与 worker 部署

**GitHub Issue**：[ #86](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/86)

**Spec**：[spec.md](spec.md)

## 实施方案

在 `docker/compose.yaml` 的上传 Worker 后新增两个 Python 镜像服务；在 `scripts/dev.sh` 中将已有 News 启动函数加入默认服务列表。两个运行入口分别使用 scheduler 和 `scwiki-news` Worker。新增轻量配置测试以文本提取 Compose 服务块，并以 Shell 语法和静态断言验证本地启动编排；最终通过 `docker compose config` 验证渲染结果。

## 需求映射

| 来源 | 实现 | 验证 |
| --- | --- | --- |
| FR-001–FR-004 | `docker/compose.yaml` | 配置测试、`docker compose config` |
| FR-005–FR-006 | `tests/07_researcher_community_forum/test_news_compose.py`、`scripts/dev.sh`、既有 scheduler 测试 | pytest、`bash -n` |

## 质量门

| 约束 | 方案 |
| --- | --- |
| 不修改上传 Worker | 测试锁定原命令，新增独立 News 服务 |
| 不执行部署 | 只执行 Compose 配置渲染，不调用 `up` |
| 当前事实才进入 Overview | 实现和验证后更新 `docs/overview/news.md` |
