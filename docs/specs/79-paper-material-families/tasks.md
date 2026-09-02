# 实施任务：论文级 Material family 多选分类

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备

- [x] T001 建立 Issue #79 完整 Feature 文档与需求质量门，路径 `docs/specs/79-paper-material-families/`

## 阶段 2：基础能力

- [ ] T002 [P] 新增迁移和迁移测试，在 `alembic/versions/`、`tests/02_maintenance_and_verification/` 建立论文级多对多关系并无损汇总旧数据（迁移源码与契约测试已完成；待真实 MySQL 执行）
- [ ] T003 [P] 更新 Python/Go ORM，在 `backend/models.py`、`goserver/models/models.go` 改变 family 所有权（代码完成；待 Go 工具链编译验证）
- [x] T004 更新共享草稿类型和契约归一化，在 `frontend/src/lib/paperProcessing.ts`、`backend/api/rag.py` 拒绝状态级新写入

## 阶段 3：用户故事 1——论文级多选编辑（P1，MVP）

**目标**：上传者和管理员只在论文级编辑多个 family，状态级 More type labels 不变。

**独立验收**：两个 family 保存回填，材料卡片无 family 控件，More type labels 仍可编辑。

### 测试

- [x] T005 [P] [US1] 更新上传和管理编辑前端测试，路径 `tests/01_decentralized_uploading/`、`tests/02_identity_governance/`

### 实施

- [x] T006 [US1] 修改 `frontend/src/components/UploadTaskEditor.tsx` 与 i18n，在 Paper type 区域增加论文级多选和校验定位
- [x] T007 [US1] 修改 `frontend/src/components/MaterialStatesEditor.tsx`，删除状态 family 与复制逻辑，保留 `structure_families[]`
- [x] T008 [US1] 修改 `frontend/src/pages/AdminPaperEditPage.tsx`，回填并提交论文级列表

## 阶段 4：用户故事 2——审核与详情一致（P1）

**目标**：Python 持久化、Go 批准和两类详情统一论文级契约。

**独立验收**：多 family 批准后在管理和公开详情完整展示，空列表无法批准。

### 测试

- [ ] T009 [P] [US2] 更新 Python 提交、Go 审核和详情测试，路径 `tests/01_decentralized_uploading/`、`tests/02_identity_governance/`（测试代码已更新；待 Go 工具链执行）

### 实施

- [x] T010 [US2] 修改 `backend/ingest/scientific_drafts.py`、`backend/api/rag.py`，校验、解析并持久化论文级列表
- [ ] T011 [US2] 修改 `goserver/handlers/classifications.go`、`admin.go`、`papers.go`，整体替换关联、快照和详情序列化（代码完成；待 Go 工具链执行）
- [x] T012 [US2] 修改 `frontend/src/components/PaperEditView.tsx` 及相关消费方，在论文级展示/读取 family
- [ ] T013 [US2] 修改 `goserver/handlers/stats.go` 及社区统计测试，以论文级 `EXISTS` 标签筛选并保证未筛选总计不重复（代码与前端契约测试完成；待 Go 工具链执行）

## 阶段 5：用户故事 3——历史数据无损迁移（P1）

**目标**：全部旧 family 去重提升且审核状态不变。

**独立验收**：迁移 fixture 的相同项去重、不同项全保留，多 family downgrade 被拒绝。

- [ ] T014 [US3] 执行并验证 Alembic upgrade/downgrade 测试，确认迁移数据和审核状态

## 最终阶段：完善与跨故事事项

- [x] T015 更新 `docs/overview/` 中领域模型、上传、审核编辑和论文详情当前事实
- [ ] T016 运行 pytest、Go test、Vitest 和前端 build，逐项核对 FR/SC 与 quickstart（Python、前端专项测试和 build 已通过；缺 Go/MySQL 环境）
- [ ] T017 更新 Issue #79 Documentation Impact、验收清单并关闭 Issue（Issue 已更新验收进度；待 T002、T003、T009、T011、T013、T014、T016 完成后关闭）

## 依赖与执行顺序

- T001 已确认需求，阻断全部实现。
- T002–T004 建立共同数据契约，阻断三个用户故事。
- US1、US2 修改共享载荷，按 T006–T012 串行集成；测试文件可并行准备。
- US3 依赖 T002、T003、T010、T011 的最终 schema 与写入语义。
- Overview 只在代码与测试证明行为落地后更新。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001–FR-008 / US1 | T004–T008 | 草稿、多选 UI、状态字段移除与 More type labels 保留 |
| FR-009–FR-011 / US3 | T002、T003、T013 | 版本化关联、无损升级和安全降级 |
| FR-012–FR-015 / US2 | T009–T013 | 批准事务、AI/持久化、详情展示和论文级统计筛选 |
| SC-001–SC-006 | T005、T009、T013、T014、T016 | 多层自动化与生产构建验证 |

## MVP 与增量策略

1. 完成数据模型和统一契约。
2. 完成上传与管理编辑的论文级多选。
3. 接通批准和详情后执行全链路验收。
4. 迁移与 Overview 一并收尾，不保留双写长期兼容。
