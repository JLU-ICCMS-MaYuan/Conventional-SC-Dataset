# 功能规格：固化 WSL mirrored 与宝塔防火墙的本地开发兼容性经验

**GitHub Issue**：[#89](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/89)

**创建日期**：2026-09-03

**状态**：已落地

## 背景与目标

SC-Wiki 当前在 WSL 本地开发环境中运行，服务仅监听 `127.0.0.1`。2026-09-03 安装宝塔后，
安装器启用 UFW 并设置默认入站拒绝策略。WSL 使用 `networkingMode=mirrored` 时，localhost TCP
流量经 `loopback0` 传输，而 UFW 默认只放行 `lo`。因此 VS Code Remote WSL 与 Windows 对本地
服务的访问被阻断。

本 Feature 不改动应用代码或系统网络配置。它将已经恢复并验证的本地运行策略写入项目文档，
使后续安装宝塔或排查本地连通性时能区分 WSL 开发环境与生产服务器的防火墙要求。

## 相关当前文档

- [本地开发环境](../../local-dev.md)：开发者执行状态检查、恢复与连通性验证的入口。
- [部署与运行时](../../overview/02_Decentralized_Maintenance_and_Verification/deployment-and-runtime.md)：
  已落地运行时约束的权威总览。

## 用户场景与验收

### 用户故事 1：开发者恢复 WSL 本地访问（优先级：P1）

作为在 Windows 上通过 VS Code Remote WSL 开发 SC-Wiki 的开发者，我希望在安装宝塔后能快速
确认防火墙是否影响本地回环访问，并使用项目记录的策略恢复环境。

**优先级理由**：VS Code Remote WSL 无法连接时，开发工作完全中断。

**独立验收**：按文档检查后，UFW 状态为 `inactive` 且服务为 `disabled`，VS Code Remote WSL
可重新建立连接，本地服务仍可通过 `127.0.0.1` 访问。

**验收场景**：

1. **假如** WSL 使用 `networkingMode=mirrored` 且已安装宝塔，**当** 开发者检查 UFW，
   **那么** 文档能说明 UFW 必须保持停止并禁止开机启动。
2. **假如** VS Code Remote WSL 无法连接而 UFW 已被启用，**当** 开发者按仅限本地 WSL 的恢复
   步骤操作，**那么** 不需要为 VS Code 随机 localhost 端口建立临时白名单。

### 用户故事 2：维护者避免把本地策略误用到生产（优先级：P2）

作为维护者，我希望文档明确此策略只针对当前 WSL 本地开发环境，避免把“禁用 UFW”误解为生产
服务器策略。

**优先级理由**：本地恢复方案若被错误复制到生产环境，会不必要地扩大安全风险。

**独立验收**：Spec、Overview 与本地开发文档都明确说明生产防火墙策略不在本 Feature 范围内。

**验收场景**：

1. **假如** 维护者阅读运行时约束，**当** 看到 UFW 策略，**那么** 能确认它仅适用于 WSL
   mirrored 本地开发，而不是 Docker 生产部署。

### 边界与异常场景

- 本 Feature 只记录 `networkingMode=mirrored` 的已验证行为；NAT 模式不据此推导相同结论。
- 若系统不是当前本地 WSL 开发环境，不应执行文档中的 UFW 重置与禁用命令。
- UFW 的单端口放行不能作为本 Feature 的恢复方案：VS Code Server 会使用动态 localhost 端口，
  且这会继续遗漏其他本地开发链路。

## 需求

### 功能需求

- **FR-001**：项目文档必须记录已确认的故障因果链：宝塔安装器启用 UFW 并设置默认拒绝、
  WSL mirrored 的 localhost TCP 流量经 `loopback0`、UFW 因未放行该接口而拦截流量。
- **FR-002**：项目文档必须将当前本地开发策略写为 UFW 停止并禁止开机启动，且明确该策略仅限
  当前 WSL mirrored 环境。
- **FR-003**：项目文档必须提供可重复执行的状态检查命令及预期结果：`ufw status verbose` 为
  `inactive`，`systemctl is-enabled ufw` 为 `disabled`，`systemctl is-active ufw` 为 `inactive`。
- **FR-004**：项目文档必须提供仅限本地 WSL 的恢复命令，并明确不得将其用于生产服务器。
- **FR-005**：Issue、Spec、Overview 与本地开发操作文档必须相互可追溯。

## 成功标准

- **SC-001**：开发者只阅读 `docs/local-dev.md` 即可确认适用环境、检查 UFW 状态并获得恢复路径。
- **SC-002**：`docs/overview/` 仅记录当前已验证的本地运行时约束，不包含未实施的端口规则或
  对生产环境的推测。
- **SC-003**：Feature 文档中的 Issue、Spec 与 Overview 链接均可解析，Issue 的
  `Documentation Impact` 项与实际变更一致。

## 假设与依赖

- 当前本地 WSL 使用 `networkingMode=mirrored`；此事实来自本次实际运行环境验证。
- 用户选择本地开发环境保持较低防火墙强度，以恢复所有现有 localhost 开发链路。
- 宝塔、UFW、WSL 和 VS Code 均是外部运行环境；本仓库不通过脚本自动修改它们。

## 范围外事项

- 不修改 SC-Wiki 业务代码、服务监听地址、`Makefile`、Docker Compose 或 `.wslconfig`。
- 不更改宝塔安装器，也不维护宝塔防火墙配置。
- 不以单端口 UFW 规则修复 VS Code 或 SC-Wiki 服务。
- 不定义任何生产服务器的防火墙策略。

## 澄清记录

### 2026-09-03

- 问：应通过为 VS Code 放行单个端口恢复连接，还是恢复宝塔安装前的本地防火墙强度？
  答：恢复宝塔安装前的本地策略，即重置并禁用 UFW；不使用临时端口白名单。
- 问：该经验是否需要改变 SC-Wiki 代码？
  答：不需要。故障位于 WSL mirrored 与宝塔修改的 UFW 状态之间，应用代码未修改。
