# 技术研究：文献处理历史

**Feature**：[spec.md](spec.md)

## R1：当前编辑页的元数据缺口在真实接口

**决策**：修复 Go 管理端详情响应，不以继续扩充前端夹具代替。

**理由**：上传者是审核上下文所需的真实元数据；物性数量并非本 Feature 需求，且会与历史
入口混淆，因此列表接口只保留 `uploader_name`，详情接口不重复返回该字段，也不计算或返回 `record_count`。

**证据**：`goserver/handlers/admin.go` 的 `GetPapers`/`GetPaperDetail`；
`frontend/src/pages/AdminPage.tsx` 的论文列表操作区域。

## R2：事件表应演进，而非并行复制

**决策**：将 `paper_review_events` 重命名并演进为 `paper_history_events`，成为唯一写入来源。

**理由**：旧表的 `reviewer_user_id` 非空，`status` 也只允许审核状态；硬塞上传和修改会破坏
名称、约束和审核贡献统计。额外新建表又会留下双写和双事实来源。

**备选方案**：保留旧表并新增历史表。已拒绝，因为每次审核需要双写或两套查询，容易漂移。

**证据**：`backend/models.py` 中 `PaperReviewEvent` 的非空审核人与状态约束；
`goserver/handlers/stats.go` 直接统计该表。

## R3：两段保存需要一个操作标识

**决策**：编辑页生成一次 `history_operation_id`，论文级和科学数据级写入共享它；数据库唯一
约束负责跨服务去重。

**理由**：现有保存先调 Go `PUT /api/admin/papers/:id`，再调 Python
`PUT /api/rag/papers/:id/scientific-draft`。以请求数记历史会把一次用户修改误计为两条。

**备选方案**：只在 Python 写历史。已拒绝，因为纯论文级修改不会进入 Python；只在 Go 写
也会遗漏科学数据单独变化。

**证据**：`AdminPaperEditPage.handleEditSave` 的两段请求；`backend/api/rag.py` 的科学数据
整体重写。

## R4：历史回填只能使用可证实事实

**决策**：回填上传和审核，不回填修改。

**理由**：`papers.created_at`、`uploaded_by_user_id` 和现有审核事件可提供时间和人员；
`updated_at` 没有操作者且可能由系统更新，不能冒充人工修改。

**证据**：`Paper` 模型和 `paper_review_events` 迁移定义。

## R5：用户名使用事件快照

**决策**：新增 `actor_username_snapshot`，新事件记录动作发生时的公开用户名。

**理由**：用户允许改名。时间线只关联当前用户名会让过去的处理记录在改名后改变显示，
不符合“忠实记录谁提交、谁审核”的目标。历史回填无法取得旧名称时仅能使用迁移时名称。

**证据**：`goserver/handlers/username.go` 支持用户更名；现有事件仅保存用户 ID。
