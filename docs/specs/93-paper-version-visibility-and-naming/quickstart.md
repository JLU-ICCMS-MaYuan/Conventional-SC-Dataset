# 快速验收：论文历史

## 前置条件

安装项目已有前端依赖和 Go 1.25 工具链。自动测试使用内存 SQLite，不触碰开发数据库。

## 自动验证

在仓库根目录运行：

```bash
node "frontend/node_modules/vitest/vitest.mjs" run --config "vitest.config.ts" "tests/01_decentralized_uploading/admin-paper-classification-review.test.tsx" "tests/02_identity_governance/identity_ui.test.tsx"
(cd "frontend" && node "node_modules/typescript/bin/tsc" -b)
(cd "goserver" && "$HOME/.local/go/bin/go" test ./handlers -run TestGetPaperHistory -count=1)
```

预期：角色矩阵拒绝未登录及普通用户，管理员和超级管理员成功；弹窗显示版本名称、事件类型、审核结果与原始意见，并覆盖缺失值与长文本。

## 浏览器复核路径

1. 管理员打开工作台 → 论文审核 → 历史；确认名称字段顺序。
2. 超级管理员执行相同操作；使用浏览器当前本地时间核对日期。
3. 普通用户直接打开 /admin 或 /superadmin，确认 403；匿名 API 请求为 401。
4. 切换英文，确认占位文案翻译而姓名/意见保持原样。

浏览器复核为人工路径；自动验证结果另行记录，不把文档步骤视为已部署证据。

## 本次验证结果（2026-09-08）

- 两个前端测试文件共 12 项通过，覆盖中英文版本名、长意见、缺失值和普通用户工作台深链。
- Go 的两个论文历史测试通过，含匿名/user/admin/superadmin 的真实 JWT 与数据库身份验证，以及时间线快照响应断言。
- TypeScript 项目编译通过。
- 文档门：5 项 FR、3 项 SC 均在 Plan 映射到任务和验证；必需产物齐全，无高优先级冲突。
- 本次验证为本地自动验证，未执行生产部署或人工浏览器复核。
