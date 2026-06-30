# VI. Researcher Community Forum

## Definition

Researcher Community Forum 指围绕研究者身份、贡献、审核、讨论和数据展示建立的社区功能。当前代码中已经有社区基础，但没有完整论坛。因此这个功能的准确状态是：社区基础部分落地，论坛互动未落地。

## Current Status

已经落地的社区基础包括用户注册、邮箱验证、真实姓名、单位、上传者身份、审核者身份、贡献者排行、管理员审批、用户管理、Tc-Year/Tc-Pressure 实时图表展示。这些能力使平台具有“研究者社区雏形”。

尚未落地的社区论坛能力包括评论区、弹幕、点赞、浏览量、帖子、回复、收藏、关注、热度排序、审核者排行的完整前台展示和用户个人主页。

## What Belongs Here

你决定把首页图表与统计展示并入本功能，这个归并是合理的。因为贡献者排行、Tc-Year 和 Tc-Pressure 实时展示并不是单纯的数据表格，它们体现的是社区贡献和领域进展的可见性。

因此本功能包含三层。

第一层是研究者身份。`users` 表保存邮箱、真实姓名、单位、角色、邮箱验证状态和审批状态。

第二层是社区贡献。论文和结构记录可以关联上传用户，论文可以关联审核用户，贡献者排行可以按上传论文数量统计。

第三层是社区可见性。首页图表展示 Tc-Year、Tc-Pressure 和贡献排行，让社区贡献以动态数据形式呈现。

## Current Community Features

当前已有：

- 普通用户注册和邮箱验证。
- 管理员申请和超级管理员审批。
- 用户角色和权限管理。
- 上传者与论文关系。
- 审核者与论文关系。
- 贡献者排行接口。
- Tc-Year 图表。
- Tc-Pressure 图表。
- 管理员后台和用户管理页面。

贡献者排行接口是 `GET /api/papers/stats/user-ranking`。图表接口包括 `GET /api/papers/stats/tc-pressure`、`GET /api/papers/stats/tc-year` 和兼容旧前端的 `GET /api/papers/stats/chart-data`。

## What Is Not Implemented

当前没有以下数据库表、API 或前端功能：

- 评论区
- 弹幕
- 点赞
- 浏览量
- 收藏
- 关注
- 论坛帖子
- 回复楼层
- 社区热度排序
- 研究者主页
- 审核者热度排行的完整产品化展示

因此对外介绍时不能说 SC-Wiki 已经拥有完整 Researcher Community Forum。更准确的说法是：SC-Wiki includes the foundations of a researcher community, while full forum-style interaction remains future work.

## Code and API Evidence

用户和权限：

- `backend/models.py` 中的 `User`
- `backend/api/auth_routes.py`
- `backend/api/admin.py`
- `/login`
- `/register`
- `/admin/register`
- `/admin/users`

社区贡献和图表：

- `GET /api/papers/stats/user-ranking`
- `GET /api/papers/stats/tc-pressure`
- `GET /api/papers/stats/tc-year`
- `GET /api/papers/stats/chart-data`
- `frontend/static/js/chart.js`
- 首页 `/`

## Boundary

本功能不负责数据是否可信，那属于 Maintenance and Verification。它也不负责数据如何进入系统，那属于 Decentralized Uploading。它负责把研究者、贡献、审核、排行、图表和未来讨论空间组织成社区层。

## Future Direction

最自然的下一步是先补研究者主页、贡献者和审核者排行，再补评论区和数据记录讨论。等文献、记录、结构和审核流稳定后，再引入点赞、弹幕、浏览量和热度排序，避免社区互动压过数据质量治理。
