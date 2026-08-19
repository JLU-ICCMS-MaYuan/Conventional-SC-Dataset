# 实施任务：论文全文解析与 LLM 自动分类

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)

## 阶段 1：准备

- [ ] T001 [ ] 对照 #19/#22、Overview 和现有测试确定兼容字段与错误码，记录在 `docs/specs/23-paper-ingestion-classification/research.md`

## 阶段 2：基础能力

- [x] T002 [P] 修复 `backend/scripts/rebuild_from_clean_results.py` 的缺失导出和参数契约
- [x] T003 [P] 修复 `backend/ingest/extractor.py`、`backend/ingest/enrich_papers.py` 中 `paper_is_experimental` 与 `infer_sc_type` 的导入和兼容映射
- [ ] T004 [P] 在 `docker/nginx.conf` 与上传 API 统一体积限制和 413 错误响应
- [ ] T005 统一 `backend/ingest/store_papers.py` 的异常传播，禁止解析/数据库失败返回假成功

## 阶段 3：用户故事 1——可靠上传与解析状态（P1，MVP）

- [ ] T006 [P] [US1] 为上传成功、413、解析失败、数据库失败编写后端回归测试 `tests/`
- [ ] T007 [US1] 实现上传状态/错误响应并接入 `frontend/src/pages/AdminPage.tsx` 或对应上传组件

## 阶段 4：用户故事 2——全文分类与解释（P1，MVP）

- [ ] T008 [P] [US2] 编写全文分段、理论/实验/综述和二级类型 fixture 测试 `tests/`
- [ ] T009 [US2] 实现分段读取、证据汇总和 LLM 分类契约 `backend/ingest/`
- [ ] T010 [US2] 实现分类理由/证据返回并在 `frontend/src/components/PaperEditView.tsx` 展示
- [ ] T011 [US2] 确保 `Paper.paper_type` 与 `KeyProperty.article_type` 独立写入和读取

## 阶段 5：用户故事 3——材料类型建议与审核（P2）

- [ ] T012 [P] [US3] 编写已有类型、AI 新类型、用户自定义和待审核状态测试 `tests/`
- [ ] T013 [US3] 实现可扩展材料类型建议及审核状态写入 `backend/models.py`、`backend/ingest/store_papers.py`
- [ ] T014 [US3] 实现管理员接受、修改、合并、拒绝新类型操作 `backend/` 与 `frontend/src/pages/AdminPage.tsx`

## 最终阶段：完善与跨故事事项

- [ ] T015 [P] 更新 `docs/overview/06-rag-literature-assistant/pdf-ingestion.md` 并补充接口契约 `contracts/`
- [ ] T016 [P] 在 Docker 临时源码环境运行端到端上传、Neo4j/数据库和前端验证，记录结果
- [ ] T017 运行完整测试、检查日志、更新本文件任务状态并提交文档门结果

## 依赖与执行顺序

T001 → T002–T005 → T006–T007 → T008–T011 → T012–T014 → T015–T017。

## 需求覆盖

| 来源 | 任务 | 说明 |
|---|---|---|
| FR-001/002/011、US1 | T002–T007 | 错误契约、工具恢复、上传状态 |
| FR-003–006、US2 | T008–T011 | 全文分类、证据和层次分离 |
| FR-007–009、US3 | T012–T014 | 类型扩展和管理员审核 |
| SC-001–005 | T006–T017 | 回归、端到端和文档验收 |

## MVP 与增量策略

1. 先完成 T001–T007，确保上传链路不再假成功。
2. 完成 T008–T011，交付全文分类 MVP。
3. 完成 T012–T014，加入材料类型审核。
4. 以 T015–T017 收尾并更新文档。
