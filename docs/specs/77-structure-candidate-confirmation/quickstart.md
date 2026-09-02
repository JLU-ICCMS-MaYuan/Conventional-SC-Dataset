# 快速验证：未分配结构候选的分配与确认交互

**GitHub Issue**：[#77](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/77)

**日期**：2026-09-02

**Spec**：[spec.md](spec.md)　**Plan**：[plan.md](plan.md)

本文件给出端到端验证路径。每步含预期结果，可逐条核对。

## 前置条件

```bash
make start      # 启动全部服务
make status     # 确认 frontend / goserver / python / mysql 均在运行
```

浏览器打开 `http://127.0.0.1:5173`。

**本 Feature 无数据库迁移、无后端改动**。仅前端交互补齐 + 一次性存量数据修复。

## 场景 1：随任务上传结构 → 分配确认 → 落库（US1）

1. 上传一篇 PDF，并在同一任务中附带一个 VASP/CIF 结构文件。
   **预期**：任务进入解析，结构附件通过 ASE 校验。
2. 解析完成后打开校对页。
   **预期**：材料状态卡片之外出现「未分配结构候选」区域，显示结构文件名与校验状态。
3. 选择目标材料状态，点击「采用」。
   **预期**：候选从未分配区消失，出现在对应材料状态卡片的候选面板（绿色「已确认」标记）。
4. 提交草稿。
   **预期**：落库后 `structure_models` 出现对应记录：
   ```bash
   mysql -h 127.0.0.1 -P 3307 -e "SELECT paper_id, structure_format, atom_count FROM structure_models ORDER BY id DESC LIMIT 1"
   ```
5. 打开该论文详情页。
   **预期**：材料状态的结构区用 3Dmol 渲染该结构。

## 场景 2：空材料状态（US1 边界）

1. 打开一篇综述论文（无材料状态）的校对页，且存在未分配候选。
   **预期**：目标材料状态下拉禁用，提示「请先创建材料状态」；「采用」不可用。

## 场景 3：校验失败候选（US1 边界）

1. 上传一个内容损坏的结构文件（或构造 `blocked` 候选）。
   **预期**：候选显示校验失败原因，「采用」不可用。

## 场景 4：管理端共用（US2）

1. 管理员打开某篇含未分配候选的论文编辑弹窗。
   **预期**：出现与上传页一致的未分配候选区，可分配确认。
2. 分配确认后保存。
   **预期**：C1 body 的 `structure_candidates` 含该候选；落库后详情页可见。

## 场景 5：存量数据恢复（US3）

1. 打开已审核的 Hg 论文详情（`/papers/9`）。
   **预期**：材料状态结构区用 3Dmol 渲染 Hg 结构（恢复自 `Hg-R-3m.vasp`）。

## 自动化测试

```bash
scripts/run-tests.sh frontend   # Vitest（含新增未分配候选区用例）
scripts/run-tests.sh go         # go test ./...（确认无回归）
scripts/run-tests.sh backend    # pytest backend/tests（确认无回归）
```

**预期**：全部通过，除 `tests/07_researcher_community_forum/news-feed.test.tsx` 的既有失败用例（与本 Feature 无关）。

## 生产构建

```bash
cd frontend && npm run build
```

**预期**：`tsc -b` 无类型错误（i18n 字典缺键会在此暴露）。
