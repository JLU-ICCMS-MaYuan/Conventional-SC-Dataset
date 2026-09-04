# 实施任务：论文级 Material family 多选分类

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备

- [x] T001 建立 Issue #79 完整 Feature 文档与需求质量门，路径 `docs/specs/79-paper-material-families/`

## 阶段 2：基础能力

- [x] T002 [P] 新增迁移和迁移测试，在 `alembic/versions/`、`tests/02_maintenance_and_verification/` 建立论文级多对多关系并无损汇总旧数据；本地真实 MySQL 已升级到包含该迁移的最新 revision
- [x] T003 [P] 更新 Python/Go ORM，在 `backend/models.py`、`goserver/models/models.go` 改变 family 所有权；Go 全量测试通过
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

- [x] T009 [P] [US2] 更新 Python 提交、Go 审核和详情测试，路径 `tests/01_decentralized_uploading/`、`tests/02_identity_governance/`，Python 与 Go 测试通过

### 实施

- [x] T010 [US2] 修改 `backend/ingest/scientific_drafts.py`、`backend/api/rag.py`，校验、解析并持久化论文级列表
- [x] T011 [US2] 修改 `goserver/handlers/classifications.go`、`admin.go`、`papers.go`，整体替换关联、快照和详情序列化
- [x] T012 [US2] 修改 `frontend/src/components/PaperEditView.tsx` 及相关消费方，在论文级展示/读取 family
- [x] T013 [US2] 修改 `goserver/handlers/stats.go` 及社区统计测试，以论文级 `EXISTS` 标签筛选并保证未筛选总计不重复

## 阶段 5：用户故事 3——历史数据无损迁移（P1）

**目标**：全部旧 family 去重提升且审核状态不变。

**独立验收**：迁移 fixture 的相同项去重、不同项全保留，多 family downgrade 被拒绝。

- [x] T014 [US3] 验证 Alembic upgrade 与 downgrade 契约：真实 MySQL 已处于升级后的最新 revision，旧状态列已移除且论文级关联有数据；自动化测试锁定去重升级和多 family 时拒绝有损降级

## 最终阶段：完善与跨故事事项

- [x] T015 更新 `docs/overview/` 中领域模型、上传、审核编辑和论文详情当前事实
- [x] T016 运行 pytest、Go test、Vitest 和前端 build，逐项核对 FR/SC 与 quickstart；Python 分类专项 20 项、Go 全量、前端相关 49 项及生产构建通过，另有 1 项与本 Issue 无关的 #85 空态旧文案断言失败
- [x] T017 更新 Issue #79 Documentation Impact、验收清单并关闭 Issue

## 最终验证（2026-09-04）

- 本地真实 MySQL 的 Alembic revision 为最新 `head`；存在 `paper_material_families`，且
  `material_states.material_family_id` 已移除。
- `bash scripts/run-tests.sh go` 全量通过；分类相关 Python 测试 20 项通过。
- #79/#80 相关前端测试 49 项通过，前端生产构建通过。唯一未通过用例是 #85 已改变空态文案后
  遗留的旧断言，不涉及 Material family 数据所有权或交互。

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
