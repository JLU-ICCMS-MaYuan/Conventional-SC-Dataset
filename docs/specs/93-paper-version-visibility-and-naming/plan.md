# 实施计划：papervision 论文版本可见性与命名

关联 [Spec](spec.md)、[技术决策](research.md)、[数据模型](data-model.md)、[接口与界面契约](contracts/history-view.md)、[验收](quickstart.md)。

## 技术上下文

Go 1.25 / Gin / GORM 提供历史 API；React 19 / TypeScript 5.6 / MUI 渲染工作台，Vitest 验证界面。历史数据保存在 MySQL，测试使用 SQLite；本次仅改展示和测试，不增加请求、依赖、表或列。

## 实施阶段

1. 核对 Go 管理员路由与 `AdminRequired` 权限，补充 admin/superadmin/user 回归测试。
2. 复用历史事件已有时间、版本、操作者和审核意见字段，在 React 历史弹窗集中生成版本名称。
3. 增加中英文占位文案，更新 Overview，执行 Go 与前端定向验证。

## 质量门与职责

- 权限复用：Go 路由组和前端 RoleRoute 保持唯一角色判定入口（FR-001）。
- 数据复用：API 字段均已存在，只在 AdminPage 的纯格式化函数组合名称，国际化字典提供缺失值文案（FR-002～005）。
- 文档先行：Spec、Plan、Research、数据模型、契约、Tasks 和验收文档齐全，无高影响歧义。
- KISS / DRY / YAGNI：不新增服务或持久化展示名称，不重复实现权限链。

## 可核验映射

| 需求与成功标准 | 事实来源与组件 | 任务 | 验证 |
| --- | --- | --- | --- |
| FR-001 / US1、US3 / SC-001 | main.go 管理员路由、RoleRoute | T001、T002、T007 | Go 真实认证与角色矩阵、前端深链测试 |
| FR-002、003 / US2 / SC-002 | history API 快照 → AdminPage 格式化 | T003、T006 | 弹窗实际输出完整名字 |
| FR-004、005 / US2 / SC-002 | 同一事件的 review / actor，双语字典 | T004、T006 | 空值、换行、长评论、原事件类型 |
| SC-003 | 文档与测试结果 | T005、T008 | 编译、链接与变更检查 |

具体文件见 Tasks；先完成文档和接口事实核对，再固定测试、收敛展示、执行验证与总览回写。
