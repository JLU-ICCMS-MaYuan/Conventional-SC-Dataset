# 技术研究：上传 Worker 版本漂移恢复

## 决策 1：使用 RQ `exception_handlers` 收敛业务任务状态

**决策**：为上传队列的每个 Worker 注册异常回调。回调从 job 参数提取 `task_id`，仅当对应
任务仍处于运行态时写入固定的队列级失败状态。

**理由**：本次错误发生在 RQ 解析函数路径时，`process_upload_task` 尚未被调用，其内部异常
处理天然无法覆盖。RQ 2.12 在 job 异常后、写入 FailedJobRegistry 前调用自定义异常回调，
正好是业务状态收敛边界。

**备选方案**：轮询 FailedJobRegistry 并修复状态。拒绝原因是引入额外常驻任务、延迟和双重
事实匹配；异常回调可以在同一次消费内完成。

**证据**：两条故障 job 已进入 FailedJobRegistry，但 Redis 任务仍为 `queued / processing`，
且 `started_at` 为空、无 Markdown 或审核产物。

## 决策 2：回调使用固定用户错误摘要，不公开原始异常

**决策**：保存稳定错误码 `upload_worker_execution_failed` 和固定中文提示；完整异常仍由 RQ
写入服务端日志和失败 job，不进入公开任务 DTO。

**理由**：入口异常可能包含文件路径、配置值或第三方库细节。用户只需要知道后台任务未能
启动以及可以重试。

**备选方案**：直接保存 `str(exc)`。拒绝原因是无法保证不泄露敏感运行信息，且 RQ 的
`Invalid attribute name` 对用户没有恢复指导。

**证据**：当前解析业务异常直接保存 `str(exc)`，但本修复覆盖的是更低层基础设施边界，
应采用更严格的公开错误契约。

## 决策 3：本地使用 `watchfiles` 包装 Worker 命令

**决策**：`scripts/dev.sh` 启动上传 Worker 时，由 `watchfiles --filter python` 监视
`backend/` 并管理实际 `python -m backend.scripts.run_upload_workers` 子进程。

**理由**：项目已经使用并安装 `watchfiles` 支撑 Python API 热重载；复用同一依赖可以确保
源码变更创建全新解释器，清除所有旧模块缓存。

**备选方案**：在 `run_worker_forever` 每轮调用 `importlib.reload`。拒绝原因是依赖图无法可靠
整体重载，父子模块可能继续混用；完整进程替换更简单可靠。

**证据**：旧 Worker PID 在 Redis 空闲超时后只重建 RQ Worker 对象，Python 进程和
`sys.modules` 未刷新；隔离复现可稳定得到相同 `Invalid attribute name`。

实际热重载验收还发现：RQ 空闲 Worker 收到温和关闭信号时设置
`_shutdown_requested_date` 并返回，但既有 `run_worker_forever` 只检查
`_stop_requested`，会错误重建 Worker。监督器超时杀死父进程后，该子进程成为孤儿并继续
消费队列。因此共享生命周期判断必须同时识别两种 RQ 关闭标记，确保完整进程替换。

## 决策 4：历史任务采用一次性定向恢复

**决策**：修复加载后，仅对 Issue 已记录的两个 task ID 执行 `failed → queued` 合法重试
转换并生成新 job，不引入扫描所有旧 job 的永久兼容逻辑。

**理由**：已知任务及原始文件仍存在，恢复对象明确；全局扫描可能错误复活用户已放弃或正在
处理的任务。

**备选方案**：启动时自动恢复所有 `queued` 且 job 已失败的任务。拒绝原因是改变正常启动
语义并可能造成无界重试。

**证据**：两个任务 ID、旧 job ID、失败时间和原始文件均已核验。
