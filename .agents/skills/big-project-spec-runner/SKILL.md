---
name: big-project-spec-runner
description: Manages single or multiple feature specifications through serial review, documentation gates, implementation, and convergence without Spec Kit. Use when creating or maintaining numbered feature directories under docs/specs, reviewing multiple Specs one by one, planning accepted features, analyzing Spec artifacts, or implementing work from tasks.md.
---

# Big Project Spec Runner

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

## 完整追问协议

在 `specify`、`clarify`、`plan`、`tasks`、`implement` 或 `converge` 中，只要存在无法由
代码、测试、配置、Overview、Issue 或已有 Spec 证实，且会影响目标、范围、验收、架构、
接口、数据、安全、依赖或任务拆分的决策，就必须先完成追问。纯只读分析、事实查证和
机械校验不主动提问；可从仓库或权威文档查明的事实必须先调查。

1. 按“目标与边界 → 用户故事与验收 → 数据与接口 → 安全与合规 → 依赖与失败处理 →
   测试与非目标”的决策树，先处理决定后续选项的高影响分支。
2. 每次只问一个问题。说明当前 Feature、问题、推荐答案及理由，以及不同答案对 Spec
   产物和实施的影响。
3. 每次收到答案后，立即回写 `spec.md` 的澄清记录及受影响的 FR、SC、场景、实体或
   任务，再继续下一个依赖分支。
4. 不设问题数量上限。所有高影响分支达成共同理解前，不得创建依赖该结论的产物或实施
   代码；可继续无依赖的只读分析或已确认部分。
5. 多 Spec 审查时，每个 Spec 的结论独立确认。普通 Spec 文档编辑在关键决策已确认且
   用户已明确授权时可直接写入；实现仍须遵守既有实现授权要求。

## 多 Spec 编排

用户要求处理多个 Spec 时，必须将 `grill-me` 的逐项决策方式与文档先行门结合：

1. 在内部建立 Spec 队列，但每次只审查一个 Spec，不一次性展示全部草案。
2. 审查时遵守“完整追问协议”；用户确认只表示当前 Spec 的设计已定稿。记录结论后进入
   下一个，但此阶段不创建文档、不修改代码。
3. 所有 Spec 都确认后，先为全部 Spec 创建完整文档，再执行跨 Spec 一致性、依赖环和覆盖
   分析。任一文档门未通过时禁止写代码。
4. 全部文档门通过后，只有用户请求已明确包含实现授权时才按依赖顺序进入 `implement`；
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
- 进入 `implement` 或 `converge` 前，必须重新读取已确认的 Spec、Plan、Research、数据模型、
  接口契约和 Tasks，并建立“需求 → 设计决策 → 数据事实来源/组件职责 → 任务 → 验证证据”映射。
  复选框不是事实来源；文档之间存在冲突时先回到对应阶段修正文档，不得边实现边猜设计。
- 修复已规划 Feature 中的 Bug 时，先判断问题属于主路径实现缺失、部署版本不一致、历史数据
  兼容还是原设计缺陷。兼容方案不得悄悄改变 Plan 已确认的数据所有权、读取依赖或组件职责；
  确需改变时，先更新 Research/Plan 并取得用户确认。
- 新数据和新请求必须走已确认的主契约。历史兼容应保持有界，并明确选择一次性迁移、定向修复、
  版本化读取或显式降级；不得把只为旧数据服务的查询或分支永久扩散到全部正常请求。
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
4. 只有真实生产路径已经实现，并在能覆盖实际故障边界的测试层通过后，任务才可标记 `[x]`；
   静态源码断言、Mock 掉关键边界的单元测试或“代码已存在”不能单独证明行为完成。
5. 若执行部署，必须核对运行制品与已验证源码的来源；部署未提交工作树时明确报告差异，
   不得把“运行环境已生效”写成“Git 中已完成”或反过来。
6. 报告变更文件、未决问题、验证结果、未满足的验收项和建议的下一模式。
