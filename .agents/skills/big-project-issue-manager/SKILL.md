---
name: big-project-issue-manager
description: Manages requirements and work across GitHub Issues for large projects, including serial review of multi-Issue requests and automatic creation of missing type labels. Use when creating, classifying, splitting, linking, updating, migrating, or closing project ideas, epics, features, bugs, documentation work, or maintenance work; when connecting accepted features to docs/specs artifacts; or when enforcing documentation impact before issue closure.
---

# Big Project Issue Manager

将 GitHub Issues 作为大型项目全部未完成需求与行动的唯一协作状态来源。执行前先读取
目标仓库的 `AGENTS.md`；仓库规则可以覆盖本 Skill 的默认值。

## 默认分类

每个 Issue 必须且只能有一个 `type:*` 标签：

- `type:epic`：功能域或跨多个交付项的 umbrella Issue。
- `type:idea`：尚未承诺的候选想法。
- `type:feature`：已经采纳、准备或正在实施的功能。
- `type:bug`：当前行为与预期不符。
- `type:documentation`：纯文档工作。
- `type:maintenance`：依赖、构建、迁移、重构或其他维护工作。

不得使用多个类型标签表达状态。优先使用 GitHub 原生状态、父子关系、负责人、里程碑
或 Project 字段表达其他维度。

### 类型标签保障

- 创建**新** Issue 时，优先一次性调用 GitHub 连接器的创建 Issue 操作，并在请求中直接
  传入唯一的目标 `type:*` 标签（例如 `labels: ["type:epic"]`）。不要为了预先创建标签而
  优先打开 GitHub 网页或中断 Issue 创建流程。
- 创建响应是此操作的权威验证：确认返回的 Issue 已附带且仅附带目标 `type:*` 标签。若此
  方式同时使缺失标签可用，则视为标签保障已完成。
- 只有当连接器创建请求被拒绝、或创建成功但未附带目标类型标签时，才检查并补救标签；先用
  GitHub 连接器的标签操作，连接器确实不支持时使用 `gh label create`。两者都不可用时停止
  写入并报告阻塞，不创建无类型 Issue。
- Issue 没有 `type:*` 标签时，先按本 Skill 判断类型，再补上对应标签。
- Issue 已有多个 `type:*` 标签时，先确认正确类型；移除多余标签仍按破坏性修改规则确认。
- 不得用 `enhancement`、`question` 等默认标签代替 `type:idea` 或 `type:feature`。

## 状态与写入策略

- 用户只要求分析、整理或查看时，保持只读。
- 用户明确要求创建或更新单个 Issue 时，在没有未决高影响决策时直接进入当前 Issue 的
  最终草案确认，不要求额外的设计确认。
- 用户要求处理多个 Issue 时，必须使用下述“多 Issue 串行审查”，不得一次性展示全部
  Issue 后取得笼统批量确认，也不得并行创建。
- 关闭 Issue 前，完成本 Skill 的关闭检查。
- 删除标签、破坏父子关系或执行其他难以恢复的操作前，单独确认。
- 优先使用已连接的 GitHub 工具；新建 Issue 必须优先使用连接器并在同一请求附带类型标签。
  连接器不覆盖所需操作时再使用 `gh`；不得因标签预检而优先使用浏览器自动化。

## 完整追问协议

在创建、更新、拆分、迁移或关闭单个或多个 Issue 时，只要存在无法由代码、测试、配置、
Overview、Spec、已有 Issue 或原始需求证实，且会影响目标、范围、类型、验收、依赖、
父子关系、Documentation Impact 或关闭条件的决策，就必须先完成追问。纯只读查询、查重和
机械校验不主动提问；可从仓库或权威协作记录查明的事实必须先调查。

1. 按“目标与边界 → 类型与用户价值 → 验收与范围外事项 → 依赖与父子关系 →
   Documentation Impact → 关闭条件”的决策树，先处理决定后续选项的高影响分支。
2. 每次只问一个问题。说明当前 Issue、问题、推荐答案及理由，以及不同答案对 Issue
   内容、关系或协作状态的影响。
3. 每次收到答案后，先更新当前 Issue 草案，再继续下一个依赖分支。
4. 所有高影响分支达成共同理解前，不得创建、更新、迁移或关闭依赖该结论的 Issue；可继续
   无依赖的只读分析。
5. 创建、更新、迁移或关闭前，展示当前 Issue 的最终草案并获得用户确认；确认仅授权当前
   Issue，不授权尚未审查的其他 Issue。

## 多 Issue 串行审查

将 `grill-me` 的逐项决策方式内置到所有多 Issue 创建、拆分和迁移请求中：

1. 在内部建立候选队列，但不要一次性向用户倾倒全部候选 Issue。
2. 每次只处理队首一个 Issue，并遵守“完整追问协议”。
3. 展示当前 Issue 的推荐标题、唯一 `type:*`、目标、范围、范围外事项、依赖、验收标准、
   Documentation Impact 和父子关系。
4. 达成共同理解后，展示当前 Issue 的最终草案并请求确认。
5. 用户确认后，创建新 Issue 时立即用 GitHub 连接器提交标题、正文和唯一 `type:*` 标签；
   更新 Issue 时用连接器更新。随后验证标题、正文、唯一类型标签和关系，并报告 Issue
   number 与链接。仅在连接器结果未满足类型标签约束时执行标签补救。
6. 当前 Issue 创建成功后才进入下一个。用户可以随时暂停、跳过、重排或终止队列。

若当前 Issue 是 Epic，先创建 Epic，再逐个审查其子 Issue；每个子 Issue 确认并创建后，
立即回写父子关系。优先使用原生 sub-issue，不可用时维护双向 Markdown 链接。

## 需求入口

1. 确认目标仓库和用户意图。
2. 搜索重复或高度重叠的开放 Issue。
3. 判断类型、范围、验收结果和依赖。
4. 缺少关键决策时逐项澄清；能从代码、Spec 或仓库规则验证的事实不要询问用户。
5. 创建或更新 Issue，并记录明确的成功标准。

未承诺内容保持 `type:idea`。只有确认实施后才转为 `type:feature`。

## Epic 与子 Issue

- 使用 `type:epic` 保存功能域目标、范围、共同约束和子 Issue 导航。
- 将工作拆成可以独立领取、实现和验收的纵向子 Issue。
- 优先使用 GitHub 原生 sub-issue 关系；不可用时使用双向 Markdown 链接。
- Epic 不承载详细实现任务，也不创建 Feature Spec。
- 不把大型规划文档原样粘贴到单个 Issue；迁移时维护“原内容 → Issue”映射并核对遗漏。

## Feature 与 Spec

被采纳的 Feature 默认使用：

```text
docs/specs/<issue-number>-<feature-slug>/
```

- 目录编号必须复用 GitHub Issue number，避免多人并行编号冲突。
- Issue 链接 Spec，`spec.md` 也链接 Issue。
- Issue 的 open/closed 状态是协作状态权威来源。
- `tasks.md` 只保存技术拆解；需要多人独立领取的任务转成子 Issue。
- Spec、Plan 和 Tasks 的内容由 `big-project-spec-runner` 维护，本 Skill 不重复编写其工作流。

默认生命周期：

```text
type:idea
  → 评审采纳
type:feature + docs/specs/<issue-number>-<feature-slug>/
  → 实现与验收
更新当前功能总览 + 关闭 Issue
```

## Documentation Impact

每个 Issue 必须包含：

```markdown
## Documentation Impact

- [ ] 不影响当前功能文档：<理由>
- [ ] 更新 docs/overview/<path>
- [ ] 新增或更新 docs/specs/<issue-number>-<feature-slug>/
- [ ] 更新根 README.md 使用说明
```

按实际影响保留或勾选适用项，不得用空白的“无影响”绕过说明。

## 关闭检查

关闭 Issue 前逐项验证：

1. 验收条件已经满足，或关闭原因明确记录为不实施、重复或失效。
2. 父子关系、依赖和关联 Issue 已同步。
3. Feature 的 Issue 与 Spec 双向链接有效。
4. 已实现行为发生变化时，使用 `big-project-overview-maintainer` 更新对应 Overview。
5. 尚未实现的设计没有进入 Overview。
6. 安装、启动或用户操作方式发生变化时，更新根 README 使用说明。
7. `Documentation Impact` 已完成并说明依据。

文档回写未完成时不得关闭 Issue。

## 边界

- 不创建本地 Issue 状态副本或独立 Issue 治理文档。
- 不把 GitHub Issue 当作稳定项目事实正文。
- 不替代 `big-project-spec-runner` 编写详细 Spec、Plan 或 Tasks。
- 不替代实现、测试或代码审查流程。
- 不把未落地需求写入当前功能 Overview。
