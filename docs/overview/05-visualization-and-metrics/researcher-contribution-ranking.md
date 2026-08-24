# 研究者贡献排行

## 功能说明

根据审核通过的论文上传和不可变审核历史汇总研究者贡献，在社区页面公开展示参与规模、上传榜、审核榜和登录用户个人排名。

## 当前行为

- Go API `GET /api/community/contributions` 对匿名访问者返回贡献参与人数、上传贡献 Top 20 和审核贡献 Top 20；有效登录请求额外返回当前用户的两项全量排名。
- 参与人数是至少有一篇当前审核通过上传或至少有一条有效审核历史的注册用户去重数。
- 上传榜只统计当前 `review_status = approved` 的论文；审核榜按 `paper_review_events` 中的有效审核动作累计。
- 同一论文的每次实际审核提交分别计数，即使状态和意见与上次相同；相同请求幂等键的网络重试不重复计数。
- 社区 `/share` 页面展示两个榜单、个人排名、最后更新时间、加载/空数据/失败状态，并支持按钮立即刷新。
- 两个榜单的公开身份直接来自大小写敏感且全站唯一的 `users.username`；兼容字段 `display_name` 与 `username` 同值，角色、实名和邮箱不参与展示名生成。可用用户名可点击进入 `/users/:username` 公开研究身份页。
- 封禁账号继续保留榜单身份并显示“已封禁”；注销账号的历史贡献保留，但用户名与展示名统一变为“已注销用户”且不再链接公开主页。
- 上传榜和审核榜的每一项都显示横向贡献条，并分别以本榜最大贡献数为 100% 线性展示相对大小；空榜或非正数安全显示为零宽度。
- 桌面宽度下“我的排名”、上传排名和审核排名位于同一行，两个榜单并排；窄屏时个人排名允许自然换行，两个榜单改为纵向排列且页面无横向溢出。
- 公共榜单快照缓存一小时；页面保持打开时每小时自动重新获取。

## 工作流程

管理员提交单篇或批量审核时，Go 服务在更新论文当前审核状态的同一数据库事务中逐篇写入审核事件。排行榜分别聚合审核通过论文和审核事件，按贡献数降序、达到当前累计数的时间升序、用户 ID 升序形成稳定全量排名，再裁剪公开 Top 20 并按登录身份附加本人排名。普通请求读取一小时 Redis 快照，`refresh=true` 绕过缓存并重建快照。

## 约束

- 贡献值只代表 SC-Wiki 当前收录与关联数据；旧论文只能按现存最终审核人和审核时间回填一条历史，无法推断更早审核轮次。
- 公开响应只包含用户 ID、`username`、同值兼容别名、派生头像文本、名次、贡献数和非敏感账号状态，不包含邮箱、实名、角色或审批信息。
- 历史账号由迁移生成不含邮箱或实名片段的 `sc_` 随机用户名；注册姓名即使为“管理员”也不会再作为榜单身份显示。
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
- `alembic/versions/20260821_0006_add_public_usernames.py`
- `tests/07_researcher_community_forum/test_issue29_contribution_ranking.py`
- `tests/07_researcher_community_forum/test_issue31_ranking_visuals.py`
- `tests/07_researcher_community_forum/test_issue31_public_username.py`
- `goserver/handlers/contribution_ranking_test.go`

## 相关变更记录

- [Feature #29：社区贡献排行榜](../../specs/29-community-contribution-ranking/spec.md)
- [Feature #31：贡献榜身份与可视化优化](../../specs/31-community-ranking-visuals/spec.md)
- [GitHub Issue #29](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/29)
- [GitHub Issue #31](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/31)

## 已知问题

- 榜单与身份 UI 纳入 Vitest，公开资料与注销/封禁映射同时有 Go 行为测试；真实数据库聚合仍需随部署数据验收。
