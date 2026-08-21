# 快速验收：社区 Tc 双图个人配置与品质因子

## 自动验证

```bash
cd goserver && go test ./...
cd ../frontend && npm run build
cd .. && python3 -m pytest tests/07_researcher_community_forum -q
git diff --check
```

预期：所有命令退出码为 0。

## API 验收

1. 请求两个端点且不传参数，确认响应点的 `tc_field=experimental_tc`。
2. 依次传入五个合法字段，确认 HTTP 200、空字段记录不回退。
3. 传入 `tc_field=drop_table`，确认 HTTP 400。
4. 连续请求两个不同字段，确认响应和缓存不串用。

## 浏览器验收

1. 1440 px 查看 `/share`：两图并排；390 px：两图单列且无横向滚动。
2. 登录账号 A，将压力图和年份图设为不同字段，刷新确认恢复。
3. 切换账号 B，确认不读取 A 的配置；退出后刷新，确认两图回到实验值。
4. 写入损坏的偏好 JSON，刷新确认安全回到默认。
5. 检查压力图 S=1 曲线在 P=0 时经过 Tc=39 K，并显示 77 K、300 K 线；年份图无 S 曲线。
6. 检查图例/Tooltip 可用文本与形状区分实验和计算，当前 Tc 字段清晰。
7. 点击散点，确认详情抽屉与 DOI 跳转仍工作；检查网络请求中不存在个人配置写 API。
