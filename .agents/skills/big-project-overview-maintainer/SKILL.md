---
name: big-project-overview-maintainer
description: Maintains a large codebase's authoritative current-function overview through read-only analysis and writes only to docs/overview/. Use when initializing or updating project overview documentation, recording implemented behavior, syncing overview, or writing back final behavior after a completed feature or bug fix.
---

# Big Project Overview Maintainer

维护项目当前功能的权威总览。只分析已经落地的事实，只创建或更新
`docs/overview/`。

## 触发场景

- 整理项目文档、初始化总体文档。
- 更新总体文档、同步 overview。
- 记录这个功能、生成功能文档。
- 将本次修复同步到项目文档。
- 将修复后的设计回写到总体文档。
- 同步修复后的功能事实、更新对应功能文档。

## 绝对边界

- 允许读取代码、测试、配置、Git diff、已完成的 Feature 和 Debug 记录。
- 只允许写入 `docs/overview/`。
- 不修改业务代码、测试、配置、Feature、Debug、Issue 或其他文档。
- 不发起 Spec Kit 或 Debug 流程，不运行测试，不执行 Git 提交。
- 未经明确确认，不删除、移动或重命名现有 Overview 文件。

## 选择模式

### 初始化模式

1. 依次使用 `explore`、`understand`、`understand-explain`。
2. `understand-explain` 必须覆盖识别出的每一个大功能。
3. 生成拟创建的大功能、小功能目录树及证据摘要。
4. 获得用户确认后，创建 `docs/overview/`。

### 增量更新模式

1. 使用 `explore` 检查本次 Feature、Debug、Git diff 和相关测试代码。
2. 使用 `understand-explain` 分析受影响功能。
3. 只更新行为确实发生变化的小功能文档及关联 `README.md`。

### 全局结构变化模式

1. 依次使用 `explore`、`understand`、`understand-explain`。
2. 提交新增大功能、重新分类、移动、重命名或删除建议及依据。
3. 获得用户确认后才能实施结构变化。

如果所需分析 Skill 不可用，使用代码搜索和文件读取完成同等只读分析，并明确报告
降级情况。

## 事实规则

- 只同步已经由当前代码、配置或可信验证结果证明的行为。
- Spec、Plan 或 Debug 假设尚未落地时，不写入当前事实。
- 部分实现只记录已存在部分，并明确当前边界。
- Feature 和 Debug 记录只用于理解与链接，不复制过程内容。
- 无法验证的内容标记为“待核验”，不得表述为已实现能力。

证据优先级、目录规范、文档模板和验证清单见
[`REFERENCE.md`](REFERENCE.md)。

## 完成前检查

1. 确认所有写入均位于 `docs/overview/`。
2. 检查导航、相对链接和功能关系是否同步。
3. 检查语言符合仓库规则或既有文档语言。
4. 检查没有把计划、假设或未完成任务写成当前事实。
5. 报告新增、更新、建议迁移及待核验内容；不要提交 Git。
