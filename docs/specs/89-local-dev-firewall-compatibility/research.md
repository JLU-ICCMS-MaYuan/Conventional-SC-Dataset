# 研究记录：WSL mirrored 与宝塔防火墙的本地开发兼容性

**GitHub Issue**：[#89](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/89)

**Spec**：[spec.md](spec.md)

## 已验证事实

| 事实 | 证据 | 对本 Feature 的影响 |
| --- | --- | --- |
| WSL 当前使用 `networkingMode=mirrored` | 本次运行环境配置检查 | 文档只为 mirrored 记录约束，不延伸到 NAT |
| SC-Wiki 本地服务监听 `127.0.0.1` | `docs/local-dev.md` 与本地服务验证 | Windows 与 VS Code Remote WSL 都依赖 localhost 连通 |
| 宝塔安装器会启用 UFW 并设置默认拒绝策略 | 已核对安装器 `Set_Firewall()` | 安装宝塔是本次状态改变的明确触发点 |
| 首次 UFW 拦截发生在宝塔安装后 | 系统日志时间线：安装开始于 14:41:57，首次 `UFW BLOCK` 于 14:44:38 | 排除 SC-Wiki 服务自身作为首个触发因素 |
| 被拦截流量为 `loopback0` 上的 `127.0.0.1` TCP | UFW 日志 | 说明 mirrored 的回环流量不等同于传统 `lo` |
| UFW 默认只放行 `lo` | 当前 UFW 规则行为 | 解释为什么 VS Code 的 localhost 随机端口被阻断 |
| 重置并禁用 UFW 后连通性恢复 | `ufw status verbose`、systemd 状态、VS Code Server 和代理端点检查 | 作为本地开发恢复策略的运行证据 |

## 决策

### 决策 1：本地 WSL 恢复为禁用 UFW，而不是逐端口放行

**理由**：VS Code Server 与开发服务会使用多个或动态的 localhost 端口。只放行当前端口会留下
未来连接中断风险，也偏离用户“恢复宝塔安装前本地防火墙强度”的目标。

**备选方案**：为 `loopback0` 或单个 localhost 端口添加 UFW 规则。

**未采用原因**：规则需要长期维护，容易遗漏服务；同时不能证明所有本地开发链路已恢复。

### 决策 2：只记录当前 WSL mirrored 本地开发策略

**理由**：生产 Docker 部署与宿主 WSL 网络边界不同，当前证据不能支持“生产也应禁用 UFW”。

**备选方案**：把禁用 UFW 作为项目通用防火墙建议。

**未采用原因**：会将本地便利性策略错误推广到安全边界不同的运行环境。

### 决策 3：不让仓库脚本自动修改 UFW 或 `.wslconfig`

**理由**：这两者是宿主机系统配置。自动执行会扩大 SC-Wiki 项目的权限与故障面。

**备选方案**：在 `make start` 中检测后自动禁用 UFW。

**未采用原因**：启动应用不应改变系统防火墙状态；用户需要明确控制此类配置。

## 已实施恢复与验证

已在当前本地 WSL 环境执行：

```bash
sudo ufw --force reset
sudo systemctl disable --now ufw
```

随后确认：

- `ufw status verbose` 显示 `Status: inactive`。
- `systemctl is-enabled ufw` 输出 `disabled`。
- `systemctl is-active ufw` 输出 `inactive`。
- VS Code Server 的 localhost 端点返回 HTTP 200；Windows VS Code 的转发端点返回 HTTP 200；
  转发 TCP 连接处于 `ESTABLISHED`。

## 未决事项

无。生产防火墙策略是独立运维议题，不在本 Feature 中跟踪。
