# 实施任务

- [x] T001 [US1] 核对论文历史路由权限并保留管理员与超级管理员访问。
- [x] T002 [US1] 补充论文历史 API 的版本时间字段与角色回归断言。
- [x] T003 [US2] 在管理员历史弹窗生成统一版本名称。
- [x] T004 [US2] 增加中英文未知审核人文案。
- [x] T005 [US3] 更新当前功能总览并完成定向测试。

## 收敛任务

初稿 T002、T005 勾选时角色矩阵、Overview 与测试尚未完成，不能作为验收证据；由以下任务纠正并记录真实结果。

- [x] T006 [US2] 在 `tests/01_decentralized_uploading/admin-paper-classification-review.test.tsx` 固定精确名称、缺失字段、双语、长文本与原事件正文；收敛 `frontend/src/pages/AdminPage.tsx` 和 `frontend/src/i18n/{zh,en}/admin.ts` 的命名与换行。
- [x] T007 [US1] 在 `goserver/handlers/paper_history_test.go` 使用真实 JWT 与数据库用户验证匿名、user、admin、superadmin；在 `tests/02_identity_governance/identity_ui.test.tsx` 验证普通用户对两个生产路由的拒绝。
- [x] T008 [US3] 运行定向 Go、Vitest 和 TypeScript 检查；更新 `docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md`，校验本目录链接并回写 Issue。

## 依赖与独立验收

文档与接口事实核对后，T006、T007 涉及不同文件，可以独立执行；T008 依赖两者通过。权限基线与名称均为本次最小交付范围。US1/US3 通过认证与深链矩阵独立验收，US2 通过真实弹窗渲染独立验收。需求到任务映射见 [Plan](plan.md)。
