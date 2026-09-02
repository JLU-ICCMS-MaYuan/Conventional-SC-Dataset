# 实施任务：论文级 Superconductor type 单选分类

- [x] T001 建立 #80 Issue 与完整 Feature Spec。
- [x] T002 新增迁移、更新 Python/Go ORM，并覆盖历史聚合规则。
- [x] T003 更新草稿归一化、提交校验和科学数据持久化。
- [x] T004 更新 Go 审核快照、详情与管理编辑 API。
- [x] T005 将上传和管理员的 type 控件移至论文级；保持 Tc 编辑规则。
- [x] T006 更新 Python、Go 和 Vitest 回归测试。
- [x] T007 回写 Overview、Issue 验收状态并完成验证。

## 验证边界

- Python 相关模型、归一化、旧契约和持久化专项测试已通过；前端构建与相关 Vitest 已通过。
- 当前环境未安装 Go 工具链，未执行 `gofmt` 或 `go test`；也未对运行中的 MySQL 执行迁移。Issue #80 保持开放，待具备上述环境后完成最终验收。
