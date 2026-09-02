# 快速验证：管理端审核编辑页独立化并功能对齐提交页

**GitHub Issue**：[#78](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/78)

**日期**：2026-09-02

**Spec**：[spec.md](spec.md)　**Plan**：[plan.md](plan.md)

本文件给出端到端验证路径。每步含预期结果，可逐条核对。

## 前置条件

```bash
make start      # 启动全部服务
```

以管理员身份登录，浏览器打开 `http://127.0.0.1:5173`。

**本 Feature 无数据库迁移**。后端新增一个结构表示生成端点，前端新增独立编辑页路由并移除编辑弹窗。

## 场景 1：列表跳转独立编辑页（US1）

1. 管理员进入工作台论文列表，点击某篇论文的「编辑」。
   **预期**：跳转到 `/admin/papers/:id/edit` 独立页面（非弹窗），页面含论文级字段、材料状态编辑区、审核区。
2. 直接访问 `/admin/papers/9/edit`。
   **预期**：同样加载该论文的编辑页；未登录或非管理员被拒绝。

## 场景 2：结构晶胞/格式转换与下载（US2）

1. 打开已审核的 Hg 论文（`/papers/9`）的编辑页，展开材料状态的结构区。
   **预期**：结构可见（惯用胞 CIF）。
2. 切换晶胞表示为「原胞」、格式为 POSCAR。
   **预期**：预览显示原胞 POSCAR 内容。
3. 点击「下载结构」。
   **预期**：下载得到当前 cell/format 对应的 CIF 或 POSCAR 文件。
4. 停止表示端点（或断开）后刷新页面。
   **预期**：结构区降级为仅显示落库惯用胞 CIF，其他编辑能力不受影响。

## 场景 3：保存与升版（US3）

1. 修改任一科学数据字段并保存。
   **预期**：先 `PUT /api/admin/papers/:id` 后 `PUT /api/rag/papers/:id/scientific-draft`；`pending` 原地保存、`approved` 保存前显示升版警告、保存后按 `revision_bumped` 提示退回待审核。

## 自动化测试

```bash
scripts/run-tests.sh frontend   # Vitest（含 admin-edit-page 新用例）
scripts/run-tests.sh go         # go test ./...（确认无回归）
scripts/run-tests.sh backend    # pytest backend/tests（含表示端点用例）
```

**预期**：全部通过，除 `tests/07_researcher_community_forum/news-feed.test.tsx` 的既有失败用例（与本 Feature 无关）。

## 生产构建

```bash
cd frontend && npm run build
```

**预期**：`tsc -b` 无类型错误。
