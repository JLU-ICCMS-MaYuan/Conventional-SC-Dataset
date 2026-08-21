# Feature 规格：统一论文查询权限与重复论文跳转

**GitHub Issue**：[#28](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/28)
**父 Epic**：[#24](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/24)
**状态**：已确认，待实施

## 目标

由 Go 统一承载 `/api/papers/**` 查询和修改，按身份返回安全字段；重复论文结果提供用户实际可执行的查看或说明动作，避免错误跳转到仅本人上传接口。

## 权限矩阵

- 匿名用户：仅可查看 `approved`。
- 登录用户：可查看所有 `approved` 和 `pending`。
- 上传者：额外可查看自己的 `rejected` 及 `review_comment`（界面称“审核意见”）。
- 管理员：可查看全部状态及 `admin_internal_note`。
- 无权查看的已知论文返回 403；不存在返回 404。

## 功能需求

- **FR-001**：Go 使用可选鉴权统一实现论文列表、详情和允许字段修改。
- **FR-002**：公开 DTO 不返回源文件路径、审核人内部信息和管理员备注。
- **FR-003**：`review_comment` 保持现有字段名，只对上传者与管理员可见。
- **FR-004**：新增 `admin_internal_note`，仅管理员可读写；历史 `review_comment` 不改名、不迁移。
- **FR-005**：上传者和管理员可 PATCH 白名单业务字段；禁止修改路径、上传者、审核状态、审核人和内部字段。
- **FR-006**：搜索、RAG 和统计继续只使用 approved 数据。
- **FR-007**：重复结果返回 `existing_paper_id/status/allowed_actions/reason`，前端按动作访问统一详情。
- **FR-008**：管理员专用审核接口继续保留并负责状态转换。

## 成功标准

- 权限矩阵的每个身份×状态组合均有自动测试。
- 普通用户响应中零管理员内部备注和服务器路径泄漏。
- 其他用户的 pending 可查看但不可修改；其他用户 rejected 返回 403。
- 重复论文提示不会再跳转到 `/my-uploads/{id}` 导致假 404。

## 范围外

- 不改变管理员审核工作流和 approved-only 搜索口径。
- 不公开原 PDF、Markdown 或附件下载。

## 澄清记录

- 2026-08-20：确认保留字段 `review_comment`，用户界面显示“审核意见”。
- 2026-08-20：确认新增仅管理员可见的 `admin_internal_note`，两类备注不可混用。
