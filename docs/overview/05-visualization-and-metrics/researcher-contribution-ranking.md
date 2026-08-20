# 研究者贡献排行

## 功能说明

根据审核通过的论文上传和不可变审核历史汇总研究者贡献，在社区页面公开展示参与规模、上传榜、审核榜和登录用户个人排名。

## 当前行为

- Go API `GET /api/community/contributions` 对匿名访问者返回贡献参与人数、上传贡献 Top 20 和审核贡献 Top 20；有效登录请求额外返回当前用户的两项全量排名。
- 参与人数是至少有一篇当前审核通过上传或至少有一条有效审核历史的注册用户去重数。
- 上传榜只统计当前 `review_status = approved` 的论文；审核榜按 `paper_review_events` 中的有效审核动作累计。
- 同一论文的不同有效审核轮次分别计数；请求幂等键、状态与意见均未变化的重复提交不重复计数。
- 社区 `/share` 页面展示两个榜单、个人排名、最后更新时间、加载/空数据/失败状态，并支持按钮立即刷新。
- 公共榜单快照缓存一小时；页面保持打开时每小时自动重新获取。

## 工作流程

管理员提交单篇或批量审核时，Go 服务在更新论文当前审核状态的同一数据库事务中逐篇写入审核事件。排行榜分别聚合审核通过论文和审核事件，按贡献数降序、达到当前累计数的时间升序、用户 ID 升序形成稳定全量排名，再裁剪公开 Top 20 并按登录身份附加本人排名。普通请求读取一小时 Redis 快照，`refresh=true` 绕过缓存并重建快照。

## 约束

- 贡献值只代表 SC-Wiki 当前收录与关联数据；旧论文只能按现存最终审核人和审核时间回填一条历史，无法推断更早审核轮次。
- 公开响应只包含用户 ID、真实姓名、派生头像文本、名次和贡献数，不包含邮箱、角色或审批信息。
- 匿名用户没有个人排名；有效登录用户零贡献项显示 0 次且没有虚构名次。
- Redis 不可用时直接查询数据库；数据库聚合失败时不返回不完整榜单。
- 本功能不包含积分奖励、周期榜、排名趋势、帖子、评论、关注、私信或 WebSocket 推送。

## 代码与测试

- `goserver/handlers/stats.go`
- `goserver/handlers/admin.go`
- `goserver/middleware/auth.go`
- `goserver/models/models.go`
- `frontend/src/pages/AdminPage.tsx`
- `frontend/src/pages/share.tsx`
- `alembic/versions/20260820_0004_add_paper_review_events.py`
- `tests/07_researcher_community_forum/test_issue29_contribution_ranking.py`
- `goserver/handlers/stats_test.go`

## 相关变更记录

- [Feature #29：社区贡献排行榜](../../specs/29-community-contribution-ranking/spec.md)
- [GitHub Issue #29](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/29)

## 已知问题

- 当前前端仓库没有独立的组件测试框架；页面契约由 Python 静态测试覆盖，交互仍需按 Feature Quickstart 做浏览器验收。
