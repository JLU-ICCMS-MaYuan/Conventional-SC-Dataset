# 技术决策记录：提交审核压强区间校验与草稿保存语义修复

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## D1：单臂区间入库（方案 A）优于规范化降级（方案 B）

- **决策**：放宽 CHECK 允许 `min=200, max=NULL` 单臂入库。
- **理由**：忠实保留 "above 200 GPa" 的结构化下限信息；影响面核查确认零下游消费——搜索筛选走 `key_properties.pressure_gpa`（`goserver/handlers/papers.go:253-257`）、论文详情 API 仅输出 `pressure_value_gpa`（`materialStatesToDict`）、`backend/` 内对 min/max 只有数值透传无 BETWEEN/中点计算、goserver 模型为可空指针。
- **备选**：方案 B（min/max 置空、仅保留 raw）丢失结构化区间，被用户否决。
- **证据**：Issue #54 讨论；`backend/models.py:803-814`；grep 全量核查记录（见 tasks T002 报告）。

## D2：`partial` 参数分离两级校验，不拆函数

- **决策**：`_validate_draft(draft, *, partial: bool = False)`；partial=True 时仅执行 `_draft_values` 结构性检查后返回。PUT 传 True，submit 两处调用保持默认 False。
- **理由**：业务校验规则只有一份，避免两个函数漂移；submit 行为零变化（默认参数）。
- **备选**：拆 `_validate_draft_structure` / `_validate_draft_business` 两个公开函数（调用点更多、规则复制风险，拒绝）。

## D3：前端消费 `ApiError.detail`，不动 api helper

- **决策**：组件内新增 `backendErrorReason`（detail 字符串直用、对象取 message 附 code、其余回退 null）与 `failureMessage(action, reason, fallback)`；`frontend/src/lib/api.ts` 已把 `body.detail` 挂到 `ApiError.detail`，无需改动。
- **证据**：`backend/api/rag.py:38-41`（`_upload_error` 的 detail 为 `{code, message}`）；`frontend/src/lib/api.ts:30-38`。

## D4：flake 修复用单用例 testTimeout，不调全局

- **决策**：仅给 `upload-task-editor-classification.test.tsx` 的重度交互用例加 `{ timeout: 15000 }`。
- **理由**：并行 CPU 争抢下该用例贴 5000ms 默认线偶红（HEAD 上复现 2/2）；全局调参会掩盖其他用例的真实劣化。
