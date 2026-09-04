# 功能规格：论文级 Superconductor type 单选分类

**GitHub Issue**：[ #80](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/80)

**状态**：已完成（2026-09-04 完成 Go、MySQL 与前端最终验收）

## 目标

将 `superconductor_kind` 从材料状态移动到论文当前 revision。每篇论文只选择一个 Superconductor type：`conventional`、`unconventional` 或 `unknown`。

## 用户故事

### US1：论文级编辑（P1）

上传者和管理员在论文基本信息区选择一次 Superconductor type，不再在每个材料状态重复选择。

**独立验收**：一篇含多个材料状态的论文只有一个 type 控件；保存、重新打开和管理员编辑均回填同一值。

### US2：统一的 Tc 编辑规则（P1）

论文的 type 决定全部材料状态的 Tc 编辑字段。`conventional` 显示计算上下文字段，`unconventional` 与 `unknown` 仅显示 Tc 数值。

**独立验收**：切换论文级 type 后，全部材料状态的新增 Tc 编辑器同步改变，已有数据不被删除。

### US3：无损且保守的历史迁移（P1）

系统按论文 revision 汇总旧状态级 type，并在无法得出唯一结论时写入 `unknown`。

**独立验收**：唯一非 unknown 值被保留；全 unknown 保持 unknown；常规与非常规冲突转换为 unknown；状态表字段被删除。

## 功能需求

- **FR-001**：`papers.superconductor_kind` 必须为 `conventional`、`unconventional` 或 `unknown`，默认 `unknown`。
- **FR-002**：`material_states` 不再保存、接收或返回 `superconductor_kind`。
- **FR-003**：草稿、提交、科学数据编辑、审核批准、审核快照和公开/管理详情均在论文顶层使用该字段。
- **FR-004**：所有 Paper type 可设置论文级 Superconductor type；不改变 Paper type、理论子分类或论文级多选 Material family。
- **FR-005**：材料状态继续独立保存 More type labels、材料维度、压强、晶系、空间群、Tc、计算上下文和结构。
- **FR-006**：`conventional` 时全部材料状态的新增 Tc 编辑器显示 λ、ωlog、μ* 与方法；其余两类仅显示 Tc 数值。
- **FR-007**：历史迁移按 `(paper_id, paper_revision)` 聚合：唯一非 unknown 类型保留；无非 unknown 值为 unknown；同时含 conventional 与 unconventional 为 unknown。
- **FR-008**：新客户端状态级写入必须被拒绝为旧契约，避免长期双写。

## 成功标准

- **SC-001**：自动化测试证明多材料状态论文只有一个 type 值且可完整读写。
- **SC-002**：自动化测试证明论文级 type 控制全部材料状态的 Tc 编辑规则。
- **SC-003**：迁移测试覆盖唯一值、全 unknown 和冲突值三种历史数据。
- **SC-004**：详情响应顶层返回 type，任一状态对象均不返回该字段。

## 非目标

- 不将 Superconductor type 改成多选。
- 不修改 Material family、More type labels 或 Paper type 的归属。
- 不修改既有 Tc、计算上下文或材料状态的科学数据模型。

## 澄清记录

- 2026-09-02：用户确认论文级字段为单选；历史冲突迁移为 `unknown`。
