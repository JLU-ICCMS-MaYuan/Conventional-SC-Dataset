# 研究者贡献与公开指标

## 职责

当前已验证能力是贡献排行和公开图表指标，而不是论坛或社区讨论系统。

## 当前行为

- 文献记录可关联上传用户和审核用户。
- 文献 API 提供贡献排行等聚合能力。
- 仅 `show_in_chart` 的超导记录属于公开图表候选数据。

## 证据

- `backend/models.py`
- `backend/api/papers.py`
- `backend/api/admin.py`
- `tests/07_researcher_community_forum/test_community_metrics.py`

## 已知缺口

- 未发现帖子、评论、论坛治理、独立社区路由或相应数据模型。论坛应保持
  `type:idea`，直到有明确 Spec 与实现。
