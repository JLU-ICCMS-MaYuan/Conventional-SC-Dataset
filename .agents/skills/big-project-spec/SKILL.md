---
name: big-project-spec
description: Manages single or multiple feature specifications through serial review, documentation gates, implementation, and convergence without Spec Kit. Use when creating or maintaining numbered feature directories under docs/specs, reviewing multiple Specs one by one, planning accepted features, analyzing Spec artifacts, or implementing work from tasks.md.
---

# Big Project Spec

直接维护大型项目的 Feature 设计与实施产物，不依赖 Spec Kit CLI、Preset、
`.specify/`、Git 分支命名或本地活动 Feature 状态。

## 开始前

1. 读取仓库根 `AGENTS.md`。
2. 读取与功能相关的 `docs/overview/`，只把已实现事实作为现状依据。
3. 确认对应的 `type:feature` GitHub Issue；Issue 是协作状态权威来源。
4. 使用 `docs/specs/<issue-number>-<feature-slug>/`。编号必须复用 Issue number。
5. 用户给出目录、Issue 或明确 Feature 时直接定位；存在多个候选且无法判定时才询问。

## 选择工作模式

按用户意图执行一种或连续执行多种模式：

- `specify`：创建或更新 `spec.md` 与 `checklists/requirements.md`。
- `clarify`：逐个解决高影响歧义，并把答案立即回写 `spec.md`。
- `plan`：生成 `plan.md`、`research.md`、`quickstart.md`，按需生成
  `data-model.md` 与 `contracts/`。
- `tasks`：生成按用户故事组织、可直接执行的 `tasks.md`。
- `checklist`：生成特定领域的需求质量检查表，不测试实现。
- `analyze`：只读检查 Spec、Plan、Tasks 的一致性、歧义和覆盖率。
- `implement`：按依赖顺序实施 `tasks.md`，验证后将任务标记为 `[x]`。
- `converge`：对照当前代码查找未完成项，只在 `tasks.md` 末尾追加收敛任务。

用户要求完整规划时依次执行 `specify → clarify → plan → tasks → analyze`；遇到必须由
用户决定的范围、安全、体验或合规分歧时暂停在对应阶段。

## 多 Spec 编排

用户要求处理多个 Spec 时，必须将 `grill-me` 的逐项决策方式与文档先行门结合：

1. 在内部建立 Spec 队列，但每次只审查一个 Spec，不一次性展示全部草案。
2. 审查前读取代码、测试、Overview、Issue 和相关 Spec；能从仓库验证的事实不得询问。
3. 围绕当前 Spec 的目标、范围、用户故事、FR、SC、数据、安全、接口、依赖、测试和范围外
   事项逐项决策；一次只问一个高影响问题，并提供推荐答案和理由。
4. 用户确认只表示当前 Spec 的设计已定稿。记录结论后进入下一个，但此阶段不创建文档、
   不修改代码。
5. 所有 Spec 都确认后，先为全部 Spec 创建完整文档，再执行跨 Spec 一致性、依赖环和覆盖
   分析。任一文档门未通过时禁止写代码。
6. 全部文档门通过后，只有用户请求已明确包含实现授权时才按依赖顺序进入 `implement`；
   否则报告文档就绪并等待实施指令。

详细阶段门和跨 Spec 检查见 [`REFERENCE.md`](REFERENCE.md) 的“多 Spec 工作流”。

详细规则、产物集合和质量门见 [`REFERENCE.md`](REFERENCE.md)。创建文档时使用
[`templates/spec-template.md`](templates/spec-template.md)、
[`templates/plan-template.md`](templates/plan-template.md)、
[`templates/tasks-template.md`](templates/tasks-template.md) 和
[`templates/checklist-template.md`](templates/checklist-template.md)。

## 核心规则

- `spec.md` 写 WHAT/WHY，不写技术方案；`plan.md` 写 HOW；`tasks.md` 写可执行步骤。
- `research.md` 记录功能内技术决策、理由和备选方案；不创建 `docs/adr/`。
- 只记录当前 Feature 的设计，不复制项目级稳定事实；新稳定事实落地后由
  `big-project-overview-maintainer` 回写 Overview。
- 所有需求使用 `FR-###`，成功标准使用 `SC-###`，任务使用 `T###`，用户故事使用
  `US#`，并保持跨文档可追踪。
- 所有 `docs/` Markdown 使用简体中文；代码符号、命令和通用专有名词可保留原文。
- 不自动创建或切换 Git 分支，不自动提交，不读取或写入 `.specify/`。
- 不通过本 Skill 创建或关闭 Issue；需要 Issue 操作时使用 `big-project-issue-manager`。
- 多 Spec 模式下不得审完一个就提前实施；必须等待全部 Spec 文档完成并通过共同质量门。

## 完成条件

1. 本阶段要求的产物存在且不含模板占位符或未解释的矛盾。
2. 相对链接有效，Issue 与 `spec.md` 双向关联。
3. FR、SC、用户故事、设计与任务的覆盖关系可以核验。
4. 报告变更文件、未决问题、验证结果和建议的下一模式。
