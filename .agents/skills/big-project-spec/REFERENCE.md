# Big Project Spec 参考规则

## 目录

- [产物契约](#产物契约)
- [Feature 定位](#feature-定位)
- [多 Spec 工作流](#多-spec-工作流)
- [Specify](#specify)
- [Clarify](#clarify)
- [Plan](#plan)
- [Tasks](#tasks)
- [Checklist](#checklist)
- [Analyze](#analyze)
- [Implement](#implement)
- [Converge](#converge)
- [职责边界](#职责边界)

## 产物契约

```text
docs/specs/<issue-number>-<feature-slug>/
├── spec.md
├── plan.md
├── research.md
├── data-model.md              # 涉及持久数据、状态或实体时创建
├── quickstart.md
├── contracts/                 # 存在外部接口、CLI、事件或 UI 契约时创建
├── tasks.md
└── checklists/
    ├── requirements.md
    └── <domain>.md            # 按需，例如 security.md、api.md、ux.md
```

`spec.md`、`plan.md`、`research.md`、`quickstart.md`、`tasks.md` 和
`checklists/requirements.md` 是完整 Feature 规划的标准产物。条件产物不适用时不要创建
空文件，也不要写 `N/A` 占位。

## Feature 定位

- 优先使用用户给出的绝对路径、相对路径或 Issue number。
- 目录名格式为 `<issue-number>-<feature-slug>`；slug 使用 2–4 个小写英文关键词。
- 新建目录前确认 Issue 确实代表已采纳 Feature；没有 Issue 时先调用
  `big-project-issue-manager`。
- 不使用时间戳、扫描得出的顺序号、当前分支或隐藏状态文件选择 Feature。

## 多 Spec 工作流

### 阶段一：逐个审查

- 建立内部候选队列，确定每个 Spec 对应的 `type:feature` Issue 和预期目录。
- 每次只呈现一个 Spec；沿决策树逐项解决需求、边界、风险、接口、数据、测试和依赖。
- 一次只问一个会改变实现或验收的问题，并给出推荐答案；可从代码或文档查明的事实直接
  调查，不询问用户。
- 用户确认当前 Spec 后只记录已确认结论并进入下一个；不得创建部分 Spec 文档，也不得
  写业务代码、测试、迁移或配置。
- 用户可暂停、跳过、重排或终止队列；未确认的 Spec 不得进入文档阶段。

### 阶段二：建立全部文档

所有 Spec 都确认后，按 Feature 逐一生成本文件定义的完整产物。完成后执行跨 Spec 检查：

1. 识别重复、冲突或可合并的 FR、SC、实体、接口和任务。
2. 统一领域术语、状态枚举、权限规则、错误语义和共享数据模型。
3. 建立 Spec 间依赖图，检测循环依赖并确定实施顺序。
4. 检查多个 Spec 是否并发修改同一文件、迁移、接口或共享组件；冲突触点必须串行。
5. 验证每个 Spec 的 FR、SC 和验收场景都映射到设计、任务与测试。
6. 检查跨 Spec 集成、回归、数据迁移、兼容、回滚、安全和端到端测试是否有明确任务。

文档门通过要求：全部必需产物存在、Requirements Checklist 完成、没有未解释占位符、
没有 CRITICAL/HIGH 一致性问题、依赖图无环、任务覆盖完整。未通过时只修文档，不写代码。

### 阶段三：按依赖实施

- 仅当用户原始请求或后续指令明确授权实现代码时进入本阶段。
- 按跨 Spec 依赖图和每个 `tasks.md` 的内部依赖排序；共享文件和数据库迁移保持串行。
- 每个 Spec 均按测试任务 → 实现任务 → 本地验证 → quickstart → converge 的顺序完成。
- 下游 Spec 开始前，验证其依赖 Spec 已满足所需契约；不得仅凭任务被勾选推定契约成立。
- 代码实现不能反向修改已确认需求；如发现设计缺陷，暂停实施并回到对应 Spec 审查。

## Specify

1. 从 Issue、用户描述、代码现状和 Overview 提取参与者、目标、行为、数据和边界。
2. 使用 Spec 模板写用户故事、Given/When/Then 验收场景、边界情况、FR、实体、SC、
   假设和范围外事项。
3. 用户故事按 P1、P2、P3 排序，每个故事都应能独立交付和验收。
4. FR 必须原子、明确、可测试；SC 必须可度量、面向结果且不绑定实现技术。
5. 最多保留 3 个高影响 `[需要澄清：...]`，其余采用合理默认并写入假设。
6. 创建 `checklists/requirements.md`，检查实现细节泄漏、完整性、可测性、边界、依赖、
   假设和可追踪性；最多自修订 3 轮。

## Clarify

按范围、数据、安全/隐私、用户体验、外部依赖、异常恢复、非功能要求、术语、完成信号
扫描 `spec.md`。只询问会改变架构、验收或任务拆分的事项，最多 5 个问题且一次只问一个。
每次接受答案后立即：

1. 在 `## 澄清记录` 的当日小节记录问题与答案；
2. 修改真正受影响的需求、场景、实体或成功标准；
3. 删除已经失效的矛盾表述；
4. 重新核对 `checklists/requirements.md`。

## Plan

1. 读取代码、测试、配置和依赖，填写真实技术上下文与源代码结构。
2. 依据 `AGENTS.md`、Overview 稳定约束和 Spec 建立质量门；有未解决阻断项时停止。
3. 在 `research.md` 中按“决策 / 理由 / 备选方案 / 证据”记录 Feature 内技术决策。
4. 涉及数据时创建 `data-model.md`：实体、字段、关系、校验、唯一性、生命周期和状态转换。
5. 涉及边界接口时在 `contracts/` 中记录输入、输出、错误、权限、版本和兼容性约束。
6. `quickstart.md` 写可运行的端到端验证路径、前置条件、命令和预期结果，不复制实现代码。
7. 设计完成后重新检查质量门，并在 `plan.md` 中解释必要复杂度。

## Tasks

- 阶段顺序：Setup → Foundational → 按优先级排列的用户故事 → Polish。
- 每行严格使用：`- [ ] T001 [P?] [US1?] 动作描述，包含准确文件路径`。
- `[P]` 仅用于修改不同文件且没有未完成依赖的任务；用户故事阶段必须带 `[US#]`。
- 测试任务仅在 Spec 要求或用户要求 TDD 时创建，并排在对应实现之前。
- 每个 FR、需要建设工作的 SC 和验收场景必须至少映射到一个任务；不得存在无来源任务。
- 写出阶段依赖、故事依赖、并行机会、MVP 范围和每个故事的独立验收方式。

## Checklist

Checklist 是“需求文本的单元测试”，检查需求是否完整、清晰、一致、可度量且覆盖边界，
不是实现测试。项目格式为：

```markdown
- [ ] CHK001 是否定义了外部依赖超时后的恢复要求？[缺口，FR-004]
```

至少 80% 的条目引用 FR、SC、用户故事、Spec 小节，或标注“缺口 / 歧义 / 冲突 /
假设”。同名 Checklist 已存在时保留原条目并从最大 CHK 编号继续追加。

## Analyze

`analyze` 严格只读，对 `spec.md`、`plan.md`、`tasks.md` 执行：重复、歧义、描述不足、
稳定约束冲突、覆盖缺口、术语漂移、数据模型差异和任务顺序检查。输出含位置、严重级别、
建议、FR/SC 到任务的覆盖表及统计。严重级别：

- CRITICAL：违反强制约束、缺少核心产物或 P1 基线要求无任务覆盖。
- HIGH：冲突需求、关键安全/性能歧义、不可验收标准。
- MEDIUM：术语漂移、次要非功能覆盖缺口、边界不足。
- LOW：不影响执行的表达和轻微重复。

未经用户明确要求，不在 analyze 模式修文档。

## Implement

1. 检查全部 Checklist；未完成时展示统计并取得继续实施的明确答复。
2. 读取全部现有 Feature 产物，按任务依赖和阶段实施；同一文件上的任务保持串行。
3. 每项任务完成后执行相称验证，成功后才将对应复选框改为 `[x]`。
4. 非并行任务失败时停止；并行任务失败时保留成功结果并明确失败项。
5. 完成后对照 FR、SC、验收场景、Plan 和 quickstart 做最终验证。

## Converge

仅比较当前代码与 Spec、Plan、Tasks 描述的意图，不依据 Git 历史。将差距分类为 missing、
partial、contradicts 或 unrequested。若存在差距，只在 `tasks.md` 末尾新增下一编号的
`## Phase N: Convergence`，从当前最大 T 编号继续追加并标注来源和差距类型；不得修改、
删除、重排或重新编号旧任务。没有差距时保持 `tasks.md` 字节不变。

## 职责边界

- 项目当前事实与稳定跨功能约束：`docs/overview/`。
- 未完成工作的协作状态、类型和父子关系：GitHub Issues。
- 单个 Feature 的需求、决策、设计、任务与验收：`docs/specs/<feature>/`。
- 不维护 Spec Kit constitution；项目规则以 `AGENTS.md` 为准。
- 不把 `tasks.md` 的每个技术步骤自动转换成 Issue；需要独立领取的工作由
  `big-project-issue-manager` 创建子 Issue。
