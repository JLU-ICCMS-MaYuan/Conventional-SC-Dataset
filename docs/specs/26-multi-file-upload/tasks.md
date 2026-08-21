# 实施任务：#26

- [x] T001 [TEST] 增加 manifest、角色、格式、50 MiB 和重复哈希测试
- [x] T002 [TEST] 增加三并发更新、锁定和单次入队测试
- [x] T003 [TEST] 增加一致性警告、确认与事务回滚测试
- [x] T004 新增 PaperFile、PaperChunk 来源、Evidence 和 upload_task_id 迁移
- [x] T005 实现文件上传、哈希、manifest 锁定和 legacy adapter
- [x] T006 实现多文件文本提取和轻量一致性检查
- [x] T007 实现一任务一论文的原子提交
- [x] T008 实现前端分组文件队列和最多三并发调度
- [x] T009 完成相关测试与容器验证

## 验证记录

- 2026-08-20：Alembic head 为 `20260820_0005`；manifest、重复哈希、事务回滚和前端三并发契约测试通过。
