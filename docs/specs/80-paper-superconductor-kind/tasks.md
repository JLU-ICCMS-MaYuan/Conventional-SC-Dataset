# 实施任务：论文级 Superconductor type 单选分类

- [x] T001 建立 #80 Issue 与完整 Feature Spec。
- [x] T002 新增迁移、更新 Python/Go ORM，并覆盖历史聚合规则。
- [x] T003 更新草稿归一化、提交校验和科学数据持久化。
- [x] T004 更新 Go 审核快照、详情与管理编辑 API。
- [x] T005 将上传和管理员的 type 控件移至论文级；保持 Tc 编辑规则。
- [x] T006 更新 Python、Go 和 Vitest 回归测试。
- [x] T007 回写 Overview、Issue 验收状态并完成验证。

## 最终验证（2026-09-04）

- Python 分类专项 20 项、Go 全量测试和 #79/#80 相关前端测试 49 项通过；前端生产构建通过。
- 本地真实 MySQL 已升级到最新 Alembic revision；`papers.superconductor_kind` 存在，
  `material_states.superconductor_kind` 已移除，且现有论文级值全部满足三值约束。
- 前端测试中的唯一失败是 #85 已改变空态文案后遗留的旧断言，与论文级
  `superconductor_kind` 所有权及 Tc 编辑规则无关。
