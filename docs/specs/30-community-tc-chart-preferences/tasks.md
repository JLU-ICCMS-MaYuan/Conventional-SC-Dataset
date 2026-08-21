# 实施任务：社区 Tc 双图个人配置与品质因子

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备

- [x] T001 核对 #30 文档门与工作树，在 `docs/specs/30-community-tc-chart-preferences/` 完成一致性分析。

## 阶段 2：基础能力

- [x] T002 [P] 在 `goserver/handlers/stats_test.go` 先写 Tc 字段白名单、默认值、非法值和缓存键测试。
- [x] T003 在 `goserver/handlers/stats.go` 实现字段解析、公共查询和字段级缓存，满足 FR-007–FR-009。
- [x] T004 [P] 在 `frontend/src/lib/chartPreferences.ts` 实现 Tc 枚举、默认配置、用户键和损坏数据恢复，满足 FR-002、FR-005–FR-006。

## 阶段 3：用户故事 1——并排比较两张图（P1，MVP）

**独立验收**：1440 px 双列、390 px 单列且无横向溢出。

- [x] T005 [US1] 在 `frontend/src/pages/share.tsx` 使用响应式网格重组两张图卡片，满足 FR-001。

## 阶段 4：用户故事 2——独立选择并保留 Tc 字段（P1）

**独立验收**：两图可选不同字段，刷新恢复且账号隔离。

- [x] T006 [US2] 在 `frontend/src/pages/share.tsx` 接入独立字段状态、带参数请求、加载/错误/空状态和恢复默认，满足 FR-002–FR-006。
- [x] T007 [US2] 在 `frontend/src/components/ChartScatter.tsx` 与 `frontend/src/pages/share.tsx` 明确 Y 轴、Tooltip 和类别文本，满足 FR-003–FR-004、FR-011、FR-013。

## 阶段 5：用户故事 3——品质因子评估（P2）

**独立验收**：压力图动态显示正确 S 曲线及 77 K、300 K 参考线，年份图无覆盖层。

- [x] T008 [US3] 在 `frontend/src/components/ChartScatter.tsx` 实现可选 S 等值线与温度参考线，满足 FR-010–FR-011。
- [x] T009 [US3] 在 `frontend/src/pages/share.tsx` 仅为压力图启用品质因子覆盖层并完成响应式高度调优。

## 最终阶段：完善与跨故事事项

- [x] T010 运行 `go test ./...`、`npm run build`、社区目录 pytest、`git diff --check` 并按 `quickstart.md` 完成验收。
- [x] T011 更新 `docs/overview/05-visualization-and-metrics/tc-history-and-pressure-charts.md`，记录落地后的事实。
- [x] T012 对照 FR、SC 和代码执行 converge；未发现实现缺口，保留 T010 作为真实环境验收门。

## 依赖与执行顺序

- T001 完成后，T002 与 T004 可并行；T003 依赖 T002。
- T005 依赖 T004；T006 依赖 T003、T004、T005。
- T007–T009 在 T006 后按共享文件串行。
- T010–T012 依赖全部实现任务。

## 需求覆盖

| 来源 | 任务 |
| --- | --- |
| FR-001 / US1 / SC-001 | T005、T010 |
| FR-002–FR-009 / US2 / SC-002–SC-003 | T002–T007、T010 |
| FR-010–FR-011 / US3 / SC-004 | T007–T010 |
| FR-012–FR-013 / SC-005–SC-006 | T006–T012 |

## MVP 与增量策略

1. 先交付白名单 API、本地偏好与响应式双图。
2. 再加入 S 等值线和科学参考线。
3. 最后完成构建、浏览器回归、Overview 和收敛检查。

## 验证记录

- 2026-08-20：`go test ./...` 通过；包含字段白名单、非法字段 HTTP 400 与缓存键隔离测试。
- 2026-08-20：隔离 Linux Node 依赖执行 `npm run build` 通过；仅有仓库既存的 3Dmol `eval` 和大 chunk 警告。
- 2026-08-20：应用内浏览器验证 1440 px 双列（两图各 634 px）与 390 px 单列，页面无横向溢出；无后端预览时两图错误状态独立显示。
- 2026-08-20：`python3 -m pytest tests/07_researcher_community_forum -q` 通过（10 passed）；#30 测试覆盖字段/API/缓存/本地配置/响应式/S 曲线/参考线/无障碍编码契约。
- 2026-08-20：#30 三个前端文件的独立 TypeScript `--noEmit` 检查通过，Vite 生产打包通过。共享工作树当前完整 `npm run build` 被并行开发中的 `UploadPage.tsx:589,591` 空值错误阻断；该文件不属于 #30，未越权修改。

## 阶段 6：Convergence

- [x] T013 [P] [US2] 在 `tests/07_researcher_community_forum/test_issue30_tc_chart_preferences.py` 增加 #30 最终合同与数学测试，并纳入 `quickstart.md`。
