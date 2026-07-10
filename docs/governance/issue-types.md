# GitHub Issue 类型规范

GitHub Issues 是项目中所有可追踪想法与行动的唯一入口，也是未完成行动的唯一
状态来源。创建、更新或关闭 Issue 前，必须先选择一个且仅一个 `type:*` 标签。

## 类型

### `type:feature`

新增或改变用户、管理员或外部调用方可感知能力的工作。

- 示例：支持 Wiki 页面版本回滚。
- 必须关联一个完整的 Spec Kit Feature Spec。

### `type:idea`

尚未承诺实施的候选想法、假设或探索方向。

- 示例：评估是否在材料详情页提供相似材料推荐。
- 不创建 Spec，也不进入开发任务；Issue 正文记录问题、价值、假设与未知点。
- 被采纳时保留原 Issue 编号，将标签改为 `type:feature`，然后创建完整的 Spec。
- 被拒绝时关闭 Issue，并记录拒绝原因。

### `type:bug`

当前实际行为与预期行为不符的修复工作。

- 示例：并发编辑时偶尔丢失内容。
- 必须关联一个完整的 Spec Kit Bugfix Spec，包括根因、修复方案、回归证据和
  `Documentation Impact`。

### `type:doc-debt`

代码、配置或运行行为已经存在，但其设计、约束、所有权或操作方式尚未被可靠地
记录下来。

- 示例：认证刷新机制已经投入使用，但没有领域设计文档。
- 完成条件是补齐或更正权威文档；不因为文档债创建虚构的功能需求。

### `type:decision-followup`

已定案的 ADR 或 Decision Note 留下了明确、可关闭的后续行动或复审条件。

- 示例：当前采用本地缓存；当日活达到既定阈值时评估迁移 Redis。
- 必须链接来源决策文档，并在完成后更新或替代该决策记录。

## 共同规则

- 每个 Issue 都必须链接其来源 Spec、ADR/Decision Note 或权威设计文档。
- `type:idea` 在采纳前不要求关联 Spec；其余类型必须链接来源 Spec、ADR/Decision
  Note 或权威设计文档。
- Feature 和 Bug 的 Spec 中必须反向链接对应 Issue。
- Issue 的 `open/closed` 状态是唯一事实；`tasks.md` 的勾选状态只是从 Issue
  派生的镜像。
- 关闭 Issue 前必须完成 `Documentation Impact` 中要求的回写，并链接结果。

## 推荐辅助标签

- `domain:<name>`：受影响的业务域，例如 `domain:wiki`。
- `risk:security`、`risk:data`、`risk:breaking`：仅在相应风险真实存在时使用。
