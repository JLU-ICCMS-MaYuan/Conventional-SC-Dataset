# 验证与恢复：WSL mirrored 本地开发防火墙兼容性

**GitHub Issue**：[#89](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/89)

**Spec**：[spec.md](spec.md)

## 适用范围

本文只适用于当前 Windows + WSL 的 `networkingMode=mirrored` 本地开发环境。不要将这些命令
用于生产服务器、远程主机或任何需要由运维策略保护的环境。

## 检查当前状态

```bash
sudo ufw status verbose
systemctl is-enabled ufw
systemctl is-active ufw
```

预期结果：

- 第一条命令显示 `Status: inactive`。
- 第二条命令输出 `disabled`。
- 第三条命令输出 `inactive`。

## 仅限本地 WSL 的恢复步骤

当宝塔安装后出现 VS Code Remote WSL 无法连接、或 Windows 无法访问本地 `127.0.0.1` 服务，
并且上述检查发现 UFW 已启用时，执行：

```bash
sudo ufw --force reset
sudo systemctl disable --now ufw
```

`ufw --force reset` 会删除现有 UFW 规则。它仅用于恢复本项目当前本地开发环境；不要在生产
服务器执行，也不要用“只放行当前 VS Code 端口”的方式替代此策略。

## 验证连通性

1. 重新运行“检查当前状态”中的三条命令，确认三项预期结果。
2. 在 VS Code 中重新连接 Remote WSL；VS Code Server 不应再因 localhost WebSocket 连接失败而断开。
3. 启动项目后访问 `http://127.0.0.1:5173`，或执行 `make status` 确认本地服务可用。

若 UFW 已是 `inactive` 和 `disabled`，问题不属于本 Feature 的已验证故障边界，应按服务日志和
端口状态继续排查。
