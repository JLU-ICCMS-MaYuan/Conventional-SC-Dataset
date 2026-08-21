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

## 完整追问协议

当初始化、结构变更或增量维护存在无法由代码、测试、配置、可信验证结果或既有 Overview
确定，且会影响功能边界、目录分类、用户可见行为或写入内容的决策时，必须先完成追问。
纯只读分析、事实同步和机械校验不主动提问；能自行查证的事实必须先查证。

1. 按“目标与边界 → 当前事实与分类 → 依赖与关系 → 验收与非目标”的决策树，先处理会
   决定后续选项的高影响分支。
2. 每次只问一个问题。说明当前功能或目录、问题、推荐答案及理由，以及不同答案对
   Overview 内容或结构的影响。
3. 每次收到答案后，先将结论反映到目录方案或拟更新内容，再继续下一个依赖分支。
4. 所有高影响分支达成共同理解前，不得执行依赖该结论的写入；可继续无依赖的只读分析。
5. 初始化、目录重组、移动、重命名或删除前，展示最终方案并获得用户对当前变更的确认。
   普通增量更新在关键决策已确认且用户已明确授权维护时可直接写入。

## 选择模式

### 初始化模式

1. 依次使用 `explore`、`understand`、`understand-explain`。
2. `understand-explain` 必须覆盖识别出的每一个功能分组。
3. 生成拟创建的递归功能目录树及证据摘要，并说明每层目录存在的必要性。
4. 获得用户确认后，创建 `docs/overview/`。

### 增量更新模式

1. 使用 `explore` 检查本次 Feature、Debug、Git diff 和相关测试代码。
2. 使用 `understand-explain` 分析受影响功能。
3. 只更新行为确实发生变化的功能文档及其各级导航 `README.md`。

### 全局结构变化模式

1. 依次使用 `explore`、`understand`、`understand-explain`。
2. 提交新增功能层级或子目录、重新分类、移动、重命名或删除建议及依据。
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
