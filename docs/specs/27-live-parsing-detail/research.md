# 调研记录：#27

- 现有 Worker 已逐段写 `chunks/00000.json`，但没有可查询 manifest、文件来源或稳定跨文件 ID。
- 直接写 JSON 可能在崩溃时留下半文件，需要 temp + replace。
- 当前 Compose 只有一个 RQ Worker，实际并发为 1。
- 未完成段没有记录，前端无法区分等待与不存在。

**决定**：复用现有分段算法，补足 manifest、原子落盘和公开查询，不引入新的实时传输协议。
