# 实施任务：论文上传科学数据结构化

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备

- [x] T001 创建并确认 GitHub Issue #46，建立完整 Feature 文档与需求检查表。
- [x] T002 在 `backend/tests/test_upload_jobs.py` 和上传集成测试中写入 Li2MgH16 失败回归。

## 阶段 2：基础能力

- [x] T003 [P] 在 Alembic、`backend/models.py`、`goserver/models/models.go` 增加 reported space group 字段和约束。
- [x] T004 [P] 在 `backend/ingest/upload_jobs.py` 定义新提取契约、缓存版本和草稿归一化。
- [x] T005 在 `backend/ingest/scientific_drafts.py` 建立校验、指纹、材料复用和实体图写入服务。

## 阶段 3：用户故事 1——材料状态和压力（P1，MVP）

**独立验收**：旧 condition 压力在新草稿和页面中正确显示。

- [x] T006 [US1] 在 `backend/tests/test_upload_jobs.py` 验证数字、对象和范围压力转换。
- [x] T007 [US1] 在 `backend/ingest/upload_jobs.py` 实现按材料/压力分组和旧草稿一次性转换。
- [x] T008 [US1] 在前端 DTO 与编辑器中展示材料状态和压力并保存新契约。

## 阶段 4：用户故事 2——空间群与计算参数（P1）

**独立验收**：Li2MgH16 显示 Fd-3m/227、λ=3.35、空 ωlog。

- [x] T009 [US2] 在后端验证空间群号/映射和 λ、ωlog 非负规则。
- [x] T010 [US2] 在 `UploadTaskEditor.tsx` 增加空间群、λ 和 ωlog 编辑字段。
- [x] T011 [US2] 在上传 UI 测试中验证显示、编辑和 PUT 请求体。

## 阶段 5：用户故事 3——新模型提交（P1）

**独立验收**：完整草稿生成正确科学实体图，失败时全部回滚。

- [x] T012 [US3] 在 `backend/api/rag.py` 用新服务替换旧 KeyProperty 写入并调整 Evidence 顺序。
- [x] T013 [US3] 增加提交实体图、Evidence、错误语义和事务回滚测试。
- [x] T014 [US3] 在隔离 MySQL 执行 Alembic upgrade 与实际插入验收。

## 最终阶段：完善与跨故事事项

- [x] T015 更新三个相关 `docs/overview/` 当前功能文档。
- [x] T016 运行后端、前端、Go、MySQL 和生产构建测试，并执行 quickstart 对照。
- [x] T017 对照 FR/SC/任务执行 converge，确认无未完成差距后自动 Git 提交。

## 依赖与执行顺序

- T002 先建立失败信号；T003–T004 可并行但本实现串行修改共享契约。
- T005 依赖 T003–T004；US1/US2 依赖新草稿 DTO；US3 依赖全部基础能力。
- T015–T017 依赖三个用户故事通过独立验收。

## 需求覆盖

| 来源 | 任务 |
|---|---|
| FR-001–FR-002 / US1 / SC-001 | T002、T006–T008 |
| FR-003–FR-004 / US2 / SC-002–SC-003 | T003–T004、T009–T011 |
| FR-005–FR-009 / US3 / SC-004–SC-005 | T005、T012–T014 |
| FR-010–FR-012 | T004、T008、T010–T011 |
| FR-013 | T003、T014 |
| FR-014 | T012–T013 |
| SC-006 | T016 |

## MVP 与增量策略

1. 完成材料状态 DTO 和压力显示。
2. 加入空间群、λ、ωlog。
3. 切换提交事务并完成隔离 MySQL 验收。
