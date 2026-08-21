# 技术研究：上传任务分层清理与待审核快照生命周期

## 决策 1：任务读取保持 Redis 单一来源

**决策**：Worker 在 duplicate 检测时查询 MySQL 一次并将权限结果写入 Redis；任务列表和详情
不查询 Paper 表，论文详情接口执行最终鉴权。

**理由**：符合 #25 的服务端任务索引设计，避免轮询 N+1 和 MySQL 故障拖垮任务中心。

**备选方案**：每次 GET 重算权限。拒绝，因为它把历史兼容变成永久架构依赖。

## 决策 2：旧状态使用一次性迁移

**决策**：迁移脚本只处理缺少当前契约版本或完整 duplicate 字段的现存 Redis 状态，默认
dry-run，显式 apply 后原子写回；迁移完成后正常 API 不保留兼容分支。

**理由**：历史状态数量有限，具有明确退出条件，且不会污染长期读取路径。

## 决策 3：三类清理职责分离

**决策**：分别实现 `cleanup_transient_data`、`cleanup_unsubmitted_files` 和
`cleanup_duplicate_candidate`，由提交、到期和审核路径组合调用。

**理由**：三类数据的保留条件不同，单一“删除所有”函数无法安全复用。

## 决策 4：清理调度携带最小上下文

**决策**：定时清理 Job 参数保存 task_id、user_id、processing_job_id、existing_paper_id、
expected_updated_at 和 schema_version，不保存任意文件路径。

**理由**：Redis state 到期后仍需删除索引、RQ Job 和候选副本；只保存标识可限制删除范围。

## 决策 5：提交后保留精简审核快照

**决策**：`result.json` 收敛为绑定 task、paper 和 revision 的审核快照；提交后删除同目录的
chunks 和其他中间文件，但保留该文件至 approved/rejected。

**理由**：管理员当前审核界面依赖 AI 值、用户值和证据对比，而 #33 不永久保存这些差异。

## 决策 6：审核事务与快照清理采用后置幂等调用

**决策**：Go 先提交审核事务，再调用 Python DELETE。DELETE 失败只记录并允许重试，不回滚审核。

**理由**：文件系统清理不能与 MySQL 跨系统原子提交；正式审核状态优先，清理保持幂等。

## 决策 7：提交重试先查永久认领

**决策**：提交入口在依赖 Redis 前，先按 upload_task_id 查询已提交论文并验证 uploaded_by_user_id。

**理由**：提交成功后的设计会立即删除 Redis；响应丢失时必须从永久事实恢复。

## 决策 8：RQ Job 使用 RQ 官方删除语义

**决策**：对 processing_job_id 使用 `Job.fetch` 和 `Job.delete()`，不存在视为成功。

**理由**：官方方法同时移除 registry、queue、job hash 和依赖键，避免手工猜 Redis 键。

## 决策 9：正式 Markdown 暂按全部解析 Markdown 保留

**决策**：提交成功后保留组合 Markdown 与分文件 Markdown；只有未提交任务清理才删除。

**理由**：当前 PaperChunk 已入库，但后续重分块和审计仍可能使用文件级 Markdown；在没有独立
“正式 Markdown 归档”设计前，保守保留符合零误删目标。
