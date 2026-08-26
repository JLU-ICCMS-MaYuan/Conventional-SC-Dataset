# 实施任务：校对表单迭代

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/draft-and-api.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：基础能力（后端）

**目的**：晶系映射、迁移、规范化推导，阻断前端晶系联动。

- [x] T001 [P] 改 `backend/services/space_groups.py`：追加晶系静态范围表、`crystal_system_for_number(n)`、`numbers_for_crystal_system(system)`；在 `backend/tests/test_space_groups.py` 追加（227→cubic、139→tetragonal、194→hexagonal、167→trigonal、1→triclinic、边界 2/3、15/16、非法 0/231→None；cubic 范围 195–230）
- [x] T002 新建迁移 `alembic/versions/20260826_0015_crystal_system.py`（接 0014，裸 op 模式）：material_states 加 `crystal_system` 列 + CHECK（8 值）；同步 `backend/models.py`（MaterialState 列 + `ck_material_states_crystal_system`）；dev MySQL 验证 upgrade/downgrade
- [x] T003 改 `backend/ingest/upload_jobs.py`：① `crystal_system` 白名单规范化 + 群号权威推导（D2）；② `_apply_methodology_inference`（FR-002~004，含 Allen-Dynes 优先、唯一方法才补、不建条目）并在 `_normalize_draft` 调用；③ SUMMARY prompt 加 `crystal_system`；在 `backend/tests/test_upload_jobs.py` 追加：晶系推导（群号 227→cubic 覆盖错误值）、研究方法单方法补类型+补方法、多方法只补类型、无判别词条不动、experimental Tc 不受影响
- [x] T004 改 `backend/ingest/scientific_drafts.py`：`crystal_system` 入库（白名单兜底 unknown）；`backend/tests/test_scientific_drafts.py` 追加入库用例
- [x] T005 [P] 改 `goserver/models/models.go`（MaterialState.CrystalSystem）、`goserver/handlers/papers.go`（输出）、`goserver/handlers/classifications.go`（快照）；`go build ./... && go test ./...`

## 阶段 2：用户故事 1——AI 建议单行（P2）

- [x] T006 [US1] 改 `frontend/src/components/UploadTaskEditor.tsx` 的 `EvidenceNotes`（:92 起）：AI 建议默认单行截断（CSS line-clamp/ellipsis），溢出时显示展开/收起切换
- [x] T007 [US1] 在 `tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx` 追加：长建议默认单行、展开/收起切换

## 阶段 3：用户故事 3——晶系三方联动（P1）

**独立验收**：quickstart 场景 3。

- [x] T008 [US3] 改 `frontend/src/lib/paperProcessing.ts`：`DraftMaterialState.crystal_system` 类型
- [x] T009 [US3] 改 `frontend/src/components/UploadTaskEditor.tsx`：材料状态新增「晶系」Select（8 值中文标签）；空间群符号 Autocomplete 按晶系范围过滤（静态范围表与后端一致）；选符号→群号+晶系；输群号→符号+晶系；自由输入不联动
- [x] T010 [US3] 在 `tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx` 追加：四方过滤、I4/mmm→139+四方、227→Fd-3m+立方

## 阶段 4：用户故事 4——结构家族改名与移除主项（P2）

- [x] T011 [US4] 改 `frontend/src/components/UploadTaskEditor.tsx`：删除主结构家族 Select 与相关状态/说明；「结构家族」标签改「更多类型标签（可以填写不止一个类型）」；编辑器不再写 is_primary
- [x] T012 [US4] 适配 `tests/01_decentralized_uploading/upload-task-editor-classification.test.tsx` 与 layout 测试：无主结构家族字段、新标签名、多标签无 is_primary

## 阶段 5：用户故事 5——超导类型全称两项（P2）

- [x] T013 [US5] 改 `frontend/src/components/UploadTaskEditor.tsx`：超导类型 Select 仅 conventional/unconventional 两项，label 全称「常规超导体（BCS超导体）」「非常规超导体」，unknown 显示占位
- [x] T014 [US5] 在 `tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx` 追加：仅两项、占位显示

## 最终阶段：完善与跨故事事项

- [x] T015 运行后端 pytest（排除 test_concurrency.py）、前端 `npm run test:upload-ui`、`npx tsc --noEmit`、`go build ./... && go test ./...`，全部通过
- [ ] T016 按 quickstart.md 场景 1–5 手工验证并记录结果
- [ ] T017 用 `gh issue edit 53 --body` 回写 Spec 链接；按 AGENTS.md 规范 git commit（仅暂存本 Feature 文件）

## 依赖与执行顺序

- T001、T005 可并行；T002 独立；T003 依赖 T001；T004 依赖 T003 的草稿契约。
- 前端任务（T006–T014）同一文件 `UploadTaskEditor.tsx` 串行；T008 先行。
- T015–T017 串行收尾。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001 / US1 | T006、T007 | EvidenceNotes 单行 |
| FR-002~004 / US2 | T003 | 研究方法推导（后端规范化） |
| FR-005~007 / US3 | T001–T005、T008–T010 | 晶系全链路 |
| FR-008 / US4 | T011、T012 | 结构家族 |
| FR-009 / US5 | T013、T014 | 超导类型文案 |
| SC-006 | T015、T016 | 全量回归 |

## MVP 与增量策略

1. 后端基础能力（T001–T005）。
2. US3 晶系联动（T008–T010）与 US1/US4/US5 均为独立增量，任一完成即可提交可用状态。
