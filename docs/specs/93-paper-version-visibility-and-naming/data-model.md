# 数据模型：复用历史事件

本次不修改表、列、关系、约束或事件生命周期。唯一事实来源仍是 `paper_history_events`。

| 字段 | 展示用途 | 约束 |
| --- | --- | --- |
| id | 时间线条目身份 | 名称不作为主键 |
| event_type | 区分上传、修改、审核 | uploaded / modified / reviewed |
| paper_revision | 名称中的 vN | 正整数，沿用当前数据 |
| occurred_at | 本地日期和时间 | API 时间戳；异常值显示时间未知 |
| actor_username_snapshot | 操作者/审核人 | 不关联当前用户名覆盖历史快照 |
| review_comment | 审核简介和评论正文 | 可空；仅审核事件有值 |
| review_status | 原有审核结果 | 不改变任何状态转换 |

数据继续由上传、修改和审核事务追加，GET 仅读取；同一 revision 可以对应多条事件。
