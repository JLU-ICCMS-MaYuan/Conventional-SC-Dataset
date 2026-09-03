# 实施计划：固化 WSL mirrored 与宝塔防火墙的本地开发兼容性经验

**GitHub Issue**：[#89](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/89)

**日期**：2026-09-03

**Spec**：[spec.md](spec.md)

## 摘要

本 Feature 是已完成运行环境修复的文档化收敛，不修改 SC-Wiki 代码。通过新增规格文档并更新
本地开发说明与运行时 Overview，固定本地 WSL mirrored 环境的 UFW 约束、恢复路径和验证标准。

## 技术上下文

- **语言与版本**：Markdown；无应用代码变更。
- **主要依赖**：WSL 2 mirrored 网络、UFW、systemd、VS Code Remote WSL、宝塔安装器。
- **数据存储**：不适用；不读取或修改项目数据库。
- **测试体系**：文档链接检查与已完成的运行环境连通性验证。
- **目标平台**：当前 Windows + WSL 本地开发环境。
- **性能目标**：不适用。
- **约束**：只记录已验证事实；本地禁用 UFW 不得泛化为生产策略；不执行系统配置写入。
- **规模范围**：一个 Feature Spec、两个现有本地开发文档与一个 GitHub Issue。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| AGENTS.md | 文档使用简体中文 | 所有新增与更新 Markdown 均使用简体中文 | 通过 |
| AGENTS.md | 不修改无关用户变更 | 仅暂存本 Feature 的新 Spec 与两份相关文档 | 通过 |
| Overview 规则 | 只记录已落地事实 | 使用已验证的 UFW 状态与连通性结果，不写未来方案 | 通过 |
| Spec 规则 | Issue 与 Spec 双向链接 | Issue #89 链接目录，`spec.md` 链接 Issue | 通过 |
| Issue #89 | 不扩大到生产防火墙 | 每份文档均标注仅适用于 WSL mirrored 本地开发 | 通过 |

## Feature 文档结构

```text
docs/specs/89-local-dev-firewall-compatibility/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── tasks.md
└── checklists/
    └── requirements.md
```

不创建数据模型或接口契约：本 Feature 没有持久化实体、外部 API、CLI 或应用接口变更。

## 源代码结构

```text
docs/
├── local-dev.md
├── overview/02_Decentralized_Maintenance_and_Verification/
│   └── deployment-and-runtime.md
└── specs/89-local-dev-firewall-compatibility/
```

**结构选择**：运行时稳定事实放入现有 Overview；供开发者直接执行的检查与恢复步骤放入
`docs/local-dev.md`；本次诊断过程、决策理由和验收证据保留在 Feature Spec，避免重复或让
Overview 承担排障日志。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001 | `research.md` 与 `spec.md` 的问题事实 | 对照 Issue #89 与已验证日志时间线 |
| FR-002 / FR-004 | `docs/local-dev.md` 的 WSL mirrored 与 UFW 小节 | 检查适用范围、恢复命令和生产边界 |
| FR-003 | `quickstart.md` 与 `docs/local-dev.md` 的验证命令 | 检查命令、预期状态和连通性信号 |
| FR-005 / SC-003 | Issue、Spec、Overview 的相对与外部链接 | Markdown 链接与 Issue 状态核验 |

## 阶段与依赖

1. 收集已验证的故障机制、恢复操作和连通性证据。
2. 新建完整 Spec 产物，明确本地与生产边界。
3. 回写 `docs/local-dev.md` 与运行时 Overview。
4. 验证链接、文档范围与 Issue 的 Documentation Impact，提交文档并关闭 Issue。
