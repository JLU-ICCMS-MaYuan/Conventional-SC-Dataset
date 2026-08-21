---
name: big-project-contractor
description: 将 big-project-planer 已确认的总体规划完整拆分为可落地的 Feature，先建立全部 Issue 与 Spec 文档，再通过全局质量门并按依赖顺序逐项实现、验证和收尾。Use when 用户要从 docs/plan/ 启动一个新项目或大型版本的完整交付，希望先看到全部详细需求和实施蓝图，再让 AI 连续完成所有功能；不用于稳定期的单个小需求或 Bug。
---

# Big Project Contractor

作为大型项目的初始交付编排器，把已确认总体规划变成完整 Spec 集合，并在全部文档通过质量门
后依次实现。执行前先读取目标仓库的 `AGENTS.md`；仓库规则优先于本 Skill。

## 适用边界

- 输入必须是 `big-project-planer` 已确认的 `docs/plan/<plan-slug>.md`。
- 适用于新项目、大型重构或大型版本的“一次看清、连续交付”。
- 项目进入常规维护期后，单个需求或 Bug 分别使用 `big-project-issue-manager` 和
  `big-project-spec-runner`，不要再次启动 Contractor。
- 不发明新的 Issue、Spec、Tasks 或 Overview 格式；必须调用现有 Skill 的契约。
- 不修改已确认规划来掩盖覆盖缺口。规划本身有冲突或缺少上游决策时，暂停并回到
  `big-project-planer`。

## 两种模式

- **文档模式**：建立全部 Issue 和 Spec，通过全局文档质量门后停止。
- **完整交付模式**：完成文档模式后，按依赖顺序实现全部已纳入范围的 Feature。

只有用户明确要求“全部实现、完整交付、从规划做到落地”等结果时，才进入完整交付模式；
否则默认文档模式。模式只决定是否写代码，不降低文档完整性。

## 阶段一：接收与拆分

1. 读取总体规划、现有 Overview、代码、测试、配置和开放 Issue，区分新建与既有能力。
2. 提取规划中的目标、能力、流程、数据、质量要求、阶段、风险和交接项，建立内部覆盖清单。
3. 按可独立验收的纵向价值切片拆成 Feature；共享基础只在确有独立交付价值时单列。
4. 展示完整 Feature 地图、规划覆盖关系、依赖图、实施顺序及明确排除项，请用户确认拆分。
5. 拆分确认后，使用 `big-project-issue-manager` 创建一个 `type:epic` 和全部
   `type:feature` 子 Issue，并维护父子关系和规划来源链接。

不得一边拆分一边实现。详细拆分和覆盖规则见 [`REFERENCE.md`](REFERENCE.md)。

## 阶段二：全部文档化

1. 按依赖顺序逐个使用 `big-project-spec-runner` 的 `specify → clarify → plan → tasks`。
2. 复用总体规划已确认的决策，不重复询问；只追问规划无法回答且会改变 Feature 验收或实现的
   新决策。
3. 每个 Feature 都完成完整文档，但此阶段不得修改业务代码、测试、迁移或部署配置。
4. 全部 Spec 完成后统一运行 `analyze`，检查规划覆盖、跨 Spec 契约、数据、依赖和任务覆盖。

在最后一个 Spec 完成前，禁止提前实现任何 Feature。

## 全局文档质量门

只有同时满足以下条件才允许实现：

- 规划中的每项必须能力和跨功能约束均映射到至少一个 Feature，或有用户确认的排除理由。
- 全部标准 Spec 产物存在，Requirements Checklist 完成，没有模板占位符。
- Feature 边界无重复或遗漏，共享术语、权限、状态、数据和接口契约一致。
- 依赖图无环；每项 FR、SC 和验收场景均有设计、任务和验证覆盖。
- 没有 CRITICAL/HIGH 分析问题，且用户已授权完整交付模式。

任一条件失败时只修复 Issue 或文档，不写代码。

## 阶段三：依次实现

1. 按跨 Spec 依赖图一次只实施一个 Feature，使用 `big-project-spec-runner implement`。
2. 每个任务经相称验证后才能标记完成；Feature 完成后执行 quickstart、回归和 `converge`。
3. 验收通过后使用 `big-project-overview-maintainer` 同步已落地事实，再由
   `big-project-issue-manager` 完成 Documentation Impact 和关闭检查。
4. 当前 Feature 完整收尾后才开始下一个；失败时停止依赖它的下游，保留已验证成果并报告。
5. 全部 Feature 完成后执行端到端验收、规划覆盖复核和 Epic 关闭检查。

不得用“任务已勾选”代替实际验证，也不得因实现困难暗中缩减 Spec。发现范围变化时按
[`REFERENCE.md`](REFERENCE.md) 的变更控制处理。

## 完成条件

报告总体规划、Epic、全部 Feature/Spec、实施顺序、验证结果、Overview 更新、关闭状态、
未纳入项和残余风险。只有全部纳入范围的 Feature 已验收、文档已同步且 Epic 关闭条件满足，
才能声明完整交付完成。
