# 验证指南

## 自动化

在仓库根目录，使用已安装依赖运行：

```bash
node "frontend/node_modules/vitest/vitest.mjs" run --config "vitest.config.ts" "tests/02_identity_governance/admin-paper-list-fields.test.tsx" "tests/02_identity_governance/admin-narrative-edit.test.tsx" "tests/02_identity_governance/admin-edit-page.test.tsx"
(cd "frontend" && node "node_modules/typescript/bin/tsc" -b)
(cd "goserver" && "/home/mayuan/.local/go/bin/go" test ./handlers -run "TestAdminPaperListFields" -count=1)
```

预期：页面测试验证列表展示、输入与重载；Go 测试经真实处理器写入隔离 SQLite 后读取，证明文本列可持久化；tsc 无错误。

## 浏览器验收路径

1. 管理员或超级管理员登录，从论文审核进入编辑页。
2. 作者只显示姓名标签；关键词和研究方法每项一行。
3. 输入含逗号姓名、按 Enter 添加，再输入另一个姓名直接点保存；重开检查全部保留。
4. 方法内输入逗号、括号及换行；关键词增加两项；保存重开检查条目和标点。
5. 删除作者、清空两文本框，保存重开确认空态。
6. 请求失败时错误提示可见，修改仍在，可重试。

浏览器验收需要运行服务与账号；自动测试不代表已部署或已人工执行该路径。

## 已执行结果（2026-09-08）

- 新增页面交互测试最初 11 项失败，复现原页面的 JSON 展示问题。
- 完成实现后，5 个前端测试文件共 45 项通过，覆盖本功能、管理员编辑、英文叙述字段、只读详情与数据来源。
- 最终补充中文输入法回车场景，12 项本功能测试全部通过；加上此前 34 项既有回归，共 46 项不同测试通过。
- Go 的 TestAdminPaperListFields 通过，包含 admin/superadmin 两种角色下真实 PUT、SQLite 落库、GET 重载及清空。
- 最终 TypeScript 构建检查通过；9 个本次相关文档的相对链接通过检查，git diff --check 通过。
- 未执行部署或登录运行环境的人工浏览器验收；Go 持久化测试使用隔离 SQLite，不修改现有 MySQL 数据。
