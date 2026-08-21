# Big Project Contractor 参考规则

## 1. 权威来源与职责

```text
docs/plan/<plan-slug>.md
  -> 已确认的总体目标、范围、能力、架构方向和阶段约束

GitHub Epic / Feature Issues
  -> 初始交付的范围、父子关系、依赖和协作状态

docs/specs/<issue-number>-<feature-slug>/
  -> 单个 Feature 的需求、设计、任务和验收

docs/overview/
  -> 实施完成后可由代码、配置或测试证明的当前事实
```

Contractor 是流程编排器，不是第五个文档权威来源。不得创建 `contractor-state.md`、本地进度
JSON 或另一套任务台账。中断后从 Epic、Issue 状态、Spec 产物和 `tasks.md` 复原进度。

## 2. 输入检查

开始前确认：

- 用户明确指定一个 `docs/plan/<plan-slug>.md`，或仓库中只有一个可用的已确认规划。
- 规划状态已确认，不含未解释占位符，目标、范围、能力、阶段和关键风险可识别。
- 规划中的事实与当前代码、Overview 或配置没有未经解释的冲突。
- 目标仓库、Issue 仓库和实现仓库可以明确对应。

规划未确认时停止并使用 `big-project-planer` 完成访谈。规划已过时但目标未改变时，先更新并
重新确认规划；不要在拆分时私自采用新假设。

## 3. 覆盖清单

为规划中的可交付内容建立内部唯一编号：

- `PC-###`：业务能力或关键用户流程。
- `PQ-###`：跨功能质量、合规、兼容或运营约束。
- `PR-###`：必须处理的风险、迁移或研究结论。

每项必须落入一种状态：`mapped`、`shared`、`excluded-confirmed`。不得使用“以后再说”隐藏
未覆盖项；后续阶段内容仍需映射为明确的 Feature 或 `type:idea`，只是不进入本次实现队列。

覆盖关系最终写入 Epic 正文，而不是新增本地状态文件：

| 规划项 | 来源章节 | Feature Issue | Spec | 本次状态 |
| --- | --- | --- | --- | --- |
| PC-001 | 能力地图 / 账户管理 | #101 | `docs/specs/101-account-management/` | 本次交付 |
| PQ-001 | 质量要求 / 审计 | #101、#104 | 对应 Spec | 共享约束 |
| PC-009 | 后续路线 / 企业 SSO | #110 | 无 | 已确认后续 Idea |

## 4. Feature 拆分规则

优先使用纵向价值切片：一个 Feature 应让某类用户完成一个可独立验收的结果，并包含实现该
结果所需的 UI、API、数据和测试。不要默认按前端、后端、数据库拆成三个无法独立验收的 Issue。

例如，同一个“用户可以用邮箱注册并登录”的规划项：

- 推荐：一个“邮箱注册与登录”Feature，内部任务覆盖页面、API、账户数据和测试。
- 不推荐：分别创建“做登录页面”“写认证 API”“建用户表”三个 Feature；任何一个单独完成
  都没有用户价值，也会制造跨 Issue 协调成本。

可以单列共享基础 Feature 的条件：它被多个纵向 Feature 依赖、可独立验证、边界稳定，而且
不单列会造成真实重复或无法安全排序。纯粹为了“架构看起来整齐”不得拆分。

每个候选 Feature 必须说明：用户价值、范围、非目标、来源规划项、验收结果、依赖、共享触点、
Documentation Impact 和建议顺序。拆分确认是对 Feature 地图的确认，不等于允许跳过后续 Spec
澄清，也不自动授权实现。

## 5. Issue 建立顺序

1. 先使用 `big-project-issue-manager` 创建一个 `type:epic`，链接总体规划并保存覆盖表。
2. 按 Feature 地图逐项创建 `type:feature`，每个 Issue 只带一个 `type:*` 标签。
3. 每创建一个 Feature，立即建立父子关系、记录依赖，并回写 Epic 覆盖表。
4. 规划中的明确后续项按用户决策创建 `type:idea`；不属于本次实现队列。
5. 全部创建后核对 Issue 数量、规划项覆盖、父子关系和依赖图。

连接器或 GitHub 不可用时停止写入。不得用临时编号创建 `docs/specs/`，因为 Spec 目录编号必须
复用真实 Issue number。

## 6. 全量 Spec 工作流

对全部本次交付 Feature 使用 `big-project-spec-runner` 的多 Spec 流程：

1. 逐个审查 Feature，只有规划未决的新问题才询问用户。
2. 所有 Feature 审查完成后，统一生成每个 Feature 的标准 Spec 产物。
3. 检查每个规划项能追溯到 FR、SC、验收场景、设计、任务和验证。
4. 执行跨 Spec 检查，解决重复需求、术语漂移、共享状态冲突、数据所有权冲突、接口不一致、
   迁移顺序、兼容策略和并发文件触点。
5. 建立无环依赖图和唯一实施顺序；同一共享文件、迁移或契约的修改必须串行。

“全部文档化”是硬门：即使第一个 Feature 很清楚，也不能在最后一个 Feature 文档完成前开始
编码。这样可以在代码成本产生前暴露跨功能冲突和遗漏。

## 7. 完整交付执行

按依赖顺序为每个 Feature 执行：

```text
检查上游契约已成立
  -> implement tasks.md
  -> 任务级验证
  -> quickstart 与 Feature 验收
  -> converge 检查遗漏
  -> 回归共享能力
  -> 同步 docs/overview/
  -> Documentation Impact 与关闭检查
  -> 开始下一个 Feature
```

一次只实施一个 Feature。可以在单个 Feature 内并行执行确实修改不同文件且无依赖的任务，
但主 Agent 必须汇总、验证和收尾；不得让多个 Feature 同时修改共享代码或数据结构。

每个下游 Feature 开始前重新验证它依赖的契约，不以“上游 Issue 已关闭”代替接口、迁移、数据
或行为的真实检查。自动提交、分支和推送遵守目标仓库 `AGENTS.md`，本 Skill 不另行覆盖。

## 8. 变更控制

实施中发现问题时分三类：

- **实现细节**：不改变 FR、SC、边界或架构方向，直接在当前 Spec 约束内解决并记录验证。
- **Feature 级设计缺口**：暂停当前 Feature，回到对应 Spec 澄清和分析；修复文档门后继续。
- **总体范围或架构变化**：停止受影响 Feature 及下游，回到 `big-project-planer` 更新并重新确认
  规划，再重新计算覆盖清单、Issue、Spec 和依赖图。

不得为了维持连续执行而把新增范围塞进当前任务。稳定期出现的小需求或 Bug 不重开 Contractor，
直接走 Issue Manager + Spec Runner；只有目标、能力地图或跨功能架构发生整体变化时才重新规划。

## 9. 失败、暂停与恢复

- 文档阶段暂停：保留已确认 Issue 和 Spec，恢复时先重新核对总体覆盖，不跳过未完成 Feature。
- 实施阶段失败：保留通过验证的提交和已完成任务，当前 Feature 保持开放；阻止依赖它的下游。
- 外部依赖阻塞：在对应 Issue 记录事实、影响和解除条件，不把阻塞项标记完成。
- 用户缩减范围：明确哪些规划项转为 `excluded-confirmed` 或 `type:idea`，同步 Epic 覆盖表和依赖图。

恢复时先读当前代码、Issue、Spec、Tasks 和验证结果，不能仅凭旧对话记忆推断进度。

## 10. 最终验收

- [ ] 总体规划中的全部本次能力和共享约束都有可追溯覆盖。
- [ ] 全部 Feature Spec、Plan、Tasks、Checklist 和条件产物完整。
- [ ] 跨 Spec 分析无 CRITICAL/HIGH 问题，依赖图无环。
- [ ] 所有本次 Feature 已实现并通过独立验收、回归和端到端验证。
- [ ] `docs/overview/` 已同步当前事实，README 等使用文档已按影响更新。
- [ ] Feature Issues 满足关闭检查，Epic 覆盖表与最终状态一致。
- [ ] 后续 Idea、未纳入项、阻塞和残余风险均有明确权威入口。
- [ ] 项目已进入常规维护期，后续小需求和 Bug 改用 Issue Manager + Spec Runner。
