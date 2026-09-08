# 实施任务：上传 Worker 版本漂移恢复

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：建立已确认需求、设计和可追踪任务。

- [x] T001 创建 `docs/specs/91-upload-worker-recovery/` 完整规格产物并通过需求质量检查

## 阶段 2：基础能力

**目的**：先建立能复现真实故障边界的自动化信号。

- [x] T002 [US1] 在 `tests/01_decentralized_uploading/test_issue91_upload_worker_recovery.py` 增加 RQ 导入失败与终态保护测试

## 阶段 3：用户故事 1——失败可见且可重试（P1，MVP）

**目标**：任何发生在解析入口外的 RQ 失败都不会让上传任务永久卡住。

**独立验收**：隔离 Redis 中的真实坏入口 job 消费后，上传状态变为可重试失败。

### 实施

- [x] T003 [US1] 在 `backend/ingest/upload_tasks.py` 实现合法任务识别、运行态保护和安全失败收敛
- [x] T004 [US1] 在 `backend/scripts/run_upload_workers.py` 为全部上传 Worker 注册队列级异常回调

## 阶段 4：用户故事 2——本地 Worker 自动刷新（P1）

**目标**：本地后端源码变化后自动加载全新 Python 进程。

**独立验收**：启动脚本的监督进程存活，修改 Python 文件后实际 Worker PID 被替换。

### 实施

- [x] T005 [US2] 在 `backend/rq_runtime.py` 正确识别 RQ 温和关闭，并在 `scripts/dev.sh` 用既有 `watchfiles` 监督本地上传 Worker 命令；更新对应生命周期与启动契约测试

## 阶段 5：用户故事 3——恢复已知任务（P2）

**目标**：保留原始文件并让两条任务在当前 Worker 上开始解析。

**独立验收**：两条任务获得新 job ID 且进入 `extracting` 或后续阶段。

### 实施

- [x] T006 [US3] 重启本地 Worker 后定向恢复 Issue #91 记录的两个 task ID，并核验文件、job 与状态

## 最终阶段：完善与跨故事事项

- [x] T007 运行 `docs/specs/91-upload-worker-recovery/quickstart.md` 中的定向与回归测试
- [x] T008 使用 `big-project-overview-maintainer` 更新 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/pdf-parsing-pipeline.md`
- [ ] T009 回写 Issue #91 的 Spec、验证与 Documentation Impact，满足关闭门槛后关闭 Issue

## 依赖与执行顺序

- T001 已完成，是后续实施基线。
- T002 必须先复现失败，再执行 T003、T004。
- T005 与 T003/T004 修改不同文件，但本次按单 Feature 串行完成。
- T006 依赖 T003～T005 和当前 Worker 重启。
- T007～T009 依赖全部用户故事完成。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001～FR-004 / US1 / SC-001～SC-002 | T002～T004、T007 | 真实 RQ 边界、状态收敛和终态保护 |
| FR-005～FR-006 / US2 / SC-003、SC-005 | T005、T007 | 本地热重载与生产命令回归 |
| FR-007 / US3 / SC-004 | T006、T007 | 两条任务定向恢复与运行证据 |
| Documentation Impact | T008～T009 | Overview、Spec 与 Issue 收敛 |

## MVP 与增量策略

1. T002～T004 先交付任务不再卡死的 P1 能力。
2. T005 消除本地复发条件。
3. T006 恢复本次用户数据，最后完成文档与 Issue 收敛。
