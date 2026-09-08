# 论文元数据边界

## 读取与写入

- GET /api/admin/papers/:id：当前 Go 三字段为 JSON 文本或 null；前端接受数组及普通文本。
- PUT /api/admin/papers/:id：沿用现有接口，三字段编辑后发送 JSON 数组的字符串形式。例如 authors 的 HTTP 属性值为 "[\"A\",\"B\"]"。
- 已是字符串的原值不再 JSON.stringify；真正数组输入才编码。清空提交 "[]"。
- 多行输入仅以换行分项，过滤空行、去条目两端空白，保留内部标点。
- JSON 解码失败返回原文本一项，不静默删除内容。

## 权限、错误与版本

沿用现有 admin/superadmin 路由和 API 守卫，不改变鉴权。失败沿用页面错误提示并保留编辑缓冲。
不引入版本化接口或迁移，不修改 history_operation_id 与科学数据第二段请求。
