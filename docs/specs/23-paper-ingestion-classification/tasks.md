# 实施任务：论文全文解析与 LLM 自动分类

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)

## 阶段 1：准备

- [x] T001 对照 #19/#22、Overview 和现有测试确定兼容字段与错误码，记录在 `docs/specs/23-paper-ingestion-classification/research.md`

## 阶段 2：基础能力

- [x] T002 [P] 修复 `backend/scripts/rebuild_from_clean_results.py` 的缺失导出和参数契约
- [x] T003 [P] 修复 `backend/ingest/extractor.py`、`backend/ingest/enrich_papers.py` 中 `paper_is_experimental` 与 `infer_sc_type` 的导入和兼容映射
- [x] T004 [P] 在 `docker/nginx.conf` 与上传 API 统一 50 MB 限制和 413 错误响应
- [x] T005 [P] 新增 Alembic 迁移并同步 Python/Go 的 `papers.theoretical_subtype`
- [x] T006 在新上传提交端点内使用单一事务写入论文、物性和文本块，不改造旧摄入模块

## 阶段 3：用户故事 1——可靠上传与解析状态（P1，MVP）

- [x] T007 [P] [US1] 在 `docker/requirements.txt`、Compose 中加入 RQ Worker、Redis AOF和三个持久目录
- [x] T008 [P] [US1] 在 `backend/ingest/upload_tasks.py` 实现 Redis 状态、草稿、24 小时过期和权限数据
- [x] T009 [US1] 重构 `backend/api/rag.py`：鉴权上传、202 响应、任务查询、保存、重试和提交端点
- [x] T010 [P] [US1] 为上传、鉴权、413、阶段失败和 24 小时清理编写后端测试 `tests/`
- [x] T011 [US1] 在 `frontend/src/pages/UploadPage.tsx` 实现五阶段轮询、刷新恢复、错误和重新解析

## 阶段 4：用户故事 2——全文分类与解释（P1，MVP）

- [x] T012 [P] [US2] 在 `backend/rag/llm.py` 统一多供应商 OpenAI 兼容 LLM 客户端
- [x] T013 [P] [US2] 编写全文分段、证据、三类论文和理论二级类型 fixture 测试 `tests/`
- [x] T014 [US2] 在 `backend/ingest/upload_jobs.py` 实现 Markdown 持久化、分段提取、汇总和断点恢复
- [x] T015 [US2] 停用新上传对 `backend/ingest/enrich_papers.py` 中 SQLite `dev.db` 的依赖
- [x] T016 [US2] 确保论文整体分类与每条物性 `article_type` 独立生成

## 阶段 5：用户故事 3——材料类型建议与审核（P2）

- [x] T017 [P] [US3] 定义共享草稿/物性/证据 TypeScript 类型与统一标准化入口
- [x] T018 [US3] 实现停止输入 5 秒自动保存、立即保存、提交前 flush 和最低校验
- [x] T019 [US3] 在用户表单显示 AI 建议、用户值、章节/页码和原文证据
- [x] T020 [US3] 支持已有建议、AI 自由文本和用户自由文本材料类型

## 阶段 6：用户故事 4——原子提交与审核（P1）

- [x] T021 [P] [US4] 为原子提交、重复 DOI/哈希、公开边界和审核状态编写测试
- [x] T022 [US4] 实现相同 DOI 打开已有论文、不同哈希候选附件及管理员鉴权下载
- [x] T023 [US4] 在 Go 审核 API 中校验三状态、记录审核人并禁止上传者自审
- [x] T024 [US4] 在 `frontend/src/pages/AdminPage.tsx` 显示 AI/用户/证据对比、确认材料类型并使用专用审核动作
- [x] T025 [US4] 审核通过后发布正式 Qdrant 数据并清理 AI 临时产物

## 最终阶段：完善与跨故事事项

- [x] T026 [P] 更新 `docs/overview/06-rag-literature-assistant/pdf-ingestion.md`、部署 README 和接口契约
- [x] T027 [P] 在 Docker 临时源码环境运行 PDF 持久化、Worker、Redis、MySQL、Qdrant 和前端端到端验证
- [x] T028 运行目标测试、构建、浏览器回归、检查日志并更新本文件任务状态

## 2026-08-19 验证记录

- Python 上传、草稿、分类、公开隔离、候选附件和发布测试：18 项通过。
- Go 全仓测试通过；前端 TypeScript 与 Vite 生产构建通过；`git diff --check` 通过。
- `compose.dev.yaml` 重建 `python/worker/goserver/frontend` 成功，Alembic 当前版本为 `20260819_0003`。
- 浏览器确认上传页、655 篇 MySQL 数据、管理员审核对话框和最终材料类型编辑正常；服务日志无新的上传链路错误。

## 依赖与执行顺序

T001 → T002–T010 → T011–T016 → T017–T020 → T021–T025 → T026–T028。

## 需求覆盖

| 来源 | 任务 | 说明 |
|---|---|---|
| FR-001/002/011–016、US1 | T002–T011 | 上传、持久化、Worker、任务与草稿 |
| FR-003–006/019/020、US2 | T012–T016 | 全文分段、证据、分类和兼容 |
| FR-007–010/016、US3 | T017–T020 | 校对、自动保存和自由类型 |
| FR-017/018/021、US4 | T021–T025 | 原子提交、审核、隐私和发布 |
| SC-001–008 | T010–T028 | 单元、集成、端到端和文档验收 |

## MVP 与增量策略

1. 先完成 T001–T007，确保上传链路不再假成功。
2. 完成 T008–T011，交付全文分类 MVP。
3. 完成 T012–T014，加入材料类型审核。
4. 以 T015–T017 收尾并更新文档。
