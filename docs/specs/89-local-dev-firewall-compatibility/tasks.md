# 实施任务：固化 WSL mirrored 与宝塔防火墙的本地开发兼容性经验

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[quickstart.md](quickstart.md)

## 阶段 1：事实收敛

**目的**：只使用已经验证的系统状态、日志时间线和连通性结果，避免把推测写成项目事实。

- [x] T001 汇总宝塔启用 UFW、`loopback0` 拦截和恢复后连通性的证据，写入 `docs/specs/89-local-dev-firewall-compatibility/research.md`。

## 阶段 2：Feature 规格与操作路径

**目的**：记录故障边界、恢复策略、验证命令与生产范围外事项。

- [x] T002 [US1] 创建 `docs/specs/89-local-dev-firewall-compatibility/spec.md`，定义 FR-001 至 FR-005 与 SC-001 至 SC-003。
- [x] T003 [US1] 创建 `docs/specs/89-local-dev-firewall-compatibility/quickstart.md`，提供仅限本地 WSL 的检查、恢复和连通性验证步骤。
- [x] T004 [US2] 创建 `docs/specs/89-local-dev-firewall-compatibility/plan.md`，记录不修改应用代码或生产策略的设计边界。

## 阶段 3：运行时文档回写

**目的**：使开发者和维护者从对应入口获得一致、可执行的当前事实。

- [x] T005 [US1] 更新 `docs/local-dev.md`，说明 WSL mirrored 下 UFW 禁用约束与宝塔安装后的检查路径。
- [x] T006 [US2] 更新 `docs/overview/02_Decentralized_Maintenance_and_Verification/deployment-and-runtime.md`，记录当前本地运行时约束并限定其适用范围。

## 最终阶段：文档与协作收尾

- [x] T007 完成 `docs/specs/89-local-dev-firewall-compatibility/checklists/requirements.md`，验证需求完整性、边界和可追溯性。
- [x] T008 核对 Issue #89、Spec、Overview 与本地开发文档的链接及 Documentation Impact，确认关闭条件只依赖已完成文档和验证证据。

## 依赖与执行顺序

- T001 是 T002 至 T006 的事实基础。
- T002 至 T004 完成后才能进行 T007 的需求质量检查。
- T005 与 T006 依赖同一事实，但修改不同文件，可独立完成。
- T008 在全部文档完成后执行。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001 | T001、T002 | 记录触发条件与 `loopback0` 故障机制 |
| FR-002 / FR-004 | T002、T003、T005、T006 | 记录本地禁用 UFW 策略与生产边界 |
| FR-003 | T003、T005 | 记录检查命令、预期状态与连通性信号 |
| FR-005 / SC-003 | T007、T008 | 核验 Issue、Spec 和 Overview 的可追溯性 |

## MVP 与增量策略

本 Feature 的 MVP 即完整记录已恢复的本地开发策略。不存在后续应用代码增量；生产防火墙策略若需
变更，必须作为独立 Issue 评估。
