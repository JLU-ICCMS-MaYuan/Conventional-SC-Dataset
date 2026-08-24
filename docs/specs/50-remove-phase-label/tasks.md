# 实施任务：删除 phase_label 并明确空间群与分类边界

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/upload-draft.md](contracts/upload-draft.md)

## 阶段 1：准备

- [ ] T001 核对 Issue #50、Spec、Overview 和并发工作树，建立本次修改文件清单。
- [ ] T002 [P] 为上传草稿、旧草稿兼容、双空间群状态和禁止模糊迁移补充失败测试。

## 阶段 2：主契约清理

- [ ] T003 [P] 从 `frontend/src/components/UploadTaskEditor.tsx` 和 `frontend/src/lib/paperProcessing.ts` 删除物相字段及相关类型/提交行为。
- [ ] T004 [P] 从 `backend/ingest/upload_jobs.py`、`backend/api/rag.py` 和 `backend/ingest/scientific_drafts.py` 删除新契约生成、归一化和持久化中的 `phase_label`，保留有界旧草稿兼容。
- [ ] T005 [P] 从 `backend/models.py`、`goserver/models/models.go` 和 `alembic/versions/` 删除字段与相关索引/Schema 契约。

## 阶段 3：用户故事 1——空间群状态清晰可审查（P1，MVP）

**目标**：上传编辑、保存、提交和入库只使用空间群与状态来源字段；不同空间群不合并。

**独立验收**：同材料同压力下的不同空间群形成独立状态，`state_kind` 保持可区分。

### 测试与实施

- [ ] T006 [US1] 更新归一化/聚合键和测试，使材料、压力、`state_kind`、空间群能够区分状态，缺少空间群时不静默合并结构候选。
- [ ] T007 [US1] 验证 `state_kind` 理论/实验语义保持不变，并覆盖空间群证据与结构候选关联。

## 阶段 4：用户故事 2——旧任务平滑完成（P1）

**目标**：含旧 `phase_label` 的草稿仍可读取、保存、提交，且新输出不再生成该字段。

**独立验收**：兼容回归通过，旧值不迁移到空间群。

- [ ] T008 [US2] 增加旧草稿 GET/PUT/submit 兼容回归，并确保旧值不迁移到空间群。
- [ ] T009 [US2] 更新上传草稿契约、AI 模板和相关接口白名单。

## 最终阶段：完善与跨故事事项

- [ ] T010 更新 `docs/overview/01-material-search-and-discovery/`、`02-data-model-and-maintenance/`、`06-rag-literature-assistant/` 和相关 Specs。
- [ ] T011 运行前端、Python、Go、fresh Schema 和迁移验证，检查 FR/SC 覆盖并更新本文件证据。
- [ ] T012 向 Issue #50 回写实施证据；按仓库规则只提交本次文件，保留其他并发修改。

## 依赖与执行顺序

- T001–T002 完成后才能修改主契约。
- T002 阻断 T003–T005；测试先行。
- T003–T005 可并行修改不同层，但数据库迁移验证必须在模型清理后执行。
- T006–T009 依赖主契约清理；同一文件上的任务串行。
- T010–T012 依赖实现和测试通过。

## 需求覆盖

| 来源 | 任务 | 说明 |
|---|---|---|
| FR-001/SC-001 | T002–T004、T009 | 删除前端、AI、归一化、保存和提交字段 |
| FR-002/SC-001 | T002、T005、T011 | 双 ORM、迁移与 Schema 契约 |
| FR-003–005/SC-003 | T002、T006–T007 | 空间群、状态来源和多结构保留 |
| FR-006–007/SC-004 | T002、T004、T008–T009 | 有界兼容与禁止模糊迁移 |
| FR-008/SC-005 | T010–T011 | 分类边界和文档事实 |

## MVP 与增量策略

1. 先完成失败测试和字段清理。
2. 完成空间群状态区分及旧任务兼容。
3. 完成迁移、文档、回归和 Issue 证据。
4. 未来分类词典另建 Feature，不阻塞本 MVP。
