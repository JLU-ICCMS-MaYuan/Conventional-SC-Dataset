# 实施任务：全网超导文献、科研新闻与产业资讯定时发现

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备

- [ ] T001 [US1] 为 #88 建立隔离测试样本和迁移基线，更新 `tests/07_researcher_community_forum/`。

## 阶段 2：基础能力

- [x] T002 [P] 扩展 `backend/news/domain.py`、`backend/news/models.py` 和 Go 模型，加入内容语义、展示栏位、发现来源、原文来源与命中依据。
- [x] T003 [P] 新增 `alembic/versions/` 中的 #88 资讯字段迁移，并覆盖 SQLite/MySQL 契约。
- [x] T004 修复 `backend/news/scheduler.py`、`backend/news/__main__.py` 的 Redis 长连接读超时和 Worker 自动恢复。

## 阶段 3：用户故事 1——发现最新超导文献（P1，MVP）

### 测试

- [x] T005 [P] [US1] 为 `backend/news/sources.py` 增加 OpenAlex、官方来源注册和 Crossref/OpenAlex 补充发现的失败测试。

### 实施

- [x] T006 [P] [US1] 实现 `backend/news/sources.py` 的 OpenAlex 和可配置出版社适配器，固定主题为 `superconduct`/`超导`。
- [x] T007 [US1] 更新 `backend/news/service.py` 的身份去重和多来源链接合并，保留原文来源。

## 阶段 4：用户故事 2——科研与社会资讯（P1）

- [x] T008 [P] [US2] 实现科研报道、社会/产业资讯适配器边界，并将 Phys.org 设置为期刊论文展示栏位。
- [x] T009 [US2] 更新 `goserver/handlers/news_feed.go`、`frontend/src/components/NewsFeed.tsx` 和中英文资讯文案，展示内容语义与来源标签。

## 阶段 5：用户故事 4——追溯与验证（P2）

- [x] T010 [P] [US4] 扩展 Go API、Python/Go/Vitest 测试，验证新字段、来源状态和安全外链。
- [ ] T011 [US3] 更新 `docker/compose.yaml`、`scripts/dev.sh` 和运行文档，确保 Worker 退出后自动恢复。

## 最终阶段：完善与跨故事事项

- [ ] T012 [US1] 运行 `quickstart.md` 全部定向和隔离集成验证，更新 `docs/overview/news.md` 与根 `README.md`。

## 当前收敛差距

- T011/T012 保持未完成：本轮尚未修改本地 `scripts/dev.sh` 守护循环，也未把尚未落地的联网来源写入当前 Overview；出版社官方 API 和合规网页新闻服务仍需在后续技术方案中确认。

## 依赖与执行顺序

T001 → T002/T003/T004 → T005/T006/T007 → T008/T009 → T010/T011 → T012。

## 需求覆盖

| 来源 | 任务 | 说明 |
|---|---|---|
| FR-001/002/003 | T005-T007 | 多来源固定主题发现与补充 |
| FR-004/005/006 | T008-T009 | 相关性、内容语义与展示栏位 |
| FR-007/008 | T002/T003/T007/T010 | 溯源、去重和数据边界 |
| FR-009 | T004/T011 | Worker 恢复与运行环境 |
| FR-010/011 | T001/T005/T010/T012 | 安全、限流与测试 |

## MVP 与增量策略

先完成数据契约、OpenAlex/Crossref 发现和 Worker 恢复，再接入出版社和社会资讯适配器；每一阶段保持 #63 旧接口可读。
