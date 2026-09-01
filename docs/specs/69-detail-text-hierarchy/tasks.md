# 实施任务：修复长文本正文压过标签的视觉层级

**输入**：[spec.md](spec.md)、[plan.md](plan.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：定位与量化

- [x] T001 读 `frontend/src/theme.ts`，取得 variant 定义：`caption` 12px/600、
  `body2` 13px、`body1` 14px
- [x] T002 定位缺陷：`SearchPage.tsx` 核心发现的 `Typography` 未指定 `variant`（默认
  落到 `body1` 14px），且显式 `fontWeight={600}` —— 对标签 12px/600 是大 2px、同字重
- [x] T003 量化层级关系：正文 14px/600 vs 标签 12px/600，正文完全压过标签

## 阶段 2：枚举同类问题的全部位置

**目的**：#68 与 #65 两次都因「逐处修」而遗漏，本阶段先把范围列全。

- [x] T004 `rg '<Typography fontWeight=\{600\}'` 扫两个检索页，列出全部候选
- [x] T005 对比同类字段：同区块「论文总结」是 `body2` 不加粗；详情页 `PaperEditView`
  核心发现也是 `body2` —— 确认只有两检索页的核心发现是例外
- [x] T006 识别 `methodology` 兜底文本（`-` 与原始字符串）同样 `fontWeight={600}`，
  两页面各两处
- [x] T007 判定短值字段（DOI、年份、期刊、标题）不在范围内：短值加粗是有意设计，
  与长文本平铺是按内容长度分的两类（FR 说明与 NFR-002）

## 阶段 3：用户故事 1——恢复正确层级（P2）

- [x] T008 [US1] `SearchPage.tsx` 核心发现：`fontWeight={600}` 改为 `variant="body2"`，
  并在 `sx` 加 `fontSize:12`（FR-001、FR-002）
- [x] T009 [US1] `SearchPage.tsx` 论文总结：补 `fontSize:12`，与核心发现保持一致（FR-003）
- [x] T010 [US1] `share.tsx` 核心发现与论文总结同步改动（FR-004）
- [x] T011 [US1] 两页面 `methodology` 兜底文本改 `variant="body2"`，共四处（FR-005）

## 阶段 4：测试

- [x] T012 `vitest.config.ts` 新增 `@mui/material` 别名——该包装在
  `frontend/node_modules`，测试从仓库根解析不到
- [x] T013 `multiline-text-preserved.test.tsx` 引入 `ThemeProvider` 与项目 `theme`，
  统一渲染入口为 `renderDetail()`（6 处 render 调用）（FR-006）
- [x] T014 用例：核心发现正文 computed 字重为 400（SC-001）
- [x] T015 用例：核心发现正文 computed 字号不大于「核心发现」标签（SC-002）
- [x] T016 用例：核心发现与论文总结的 `{fontSize, fontWeight}` 完全相等（SC-003）
- [x] T017 反向验证：还原为 `fontWeight={600}` 且移除 `variant` 后，3 个新用例全部
  失败；恢复后通过（SC-004）

## 阶段 5：验证

- [x] T018 多行文本文件 6 例通过（3 例换行 + 3 例字号字重）
- [x] T019 `tsc --noEmit` 通过（SC-006）
- [x] T020 前端全量 110 例中 109 通过；唯一失败为 `tests/08_news/NewsFeed.test.tsx`
  （Issue #63 在建代码）
- [x] T021 排查全量中一度出现的另 2 例失败：单独重跑稳定通过，确认为并发超时而非回归
- [x] T022 查清实际服务路径：仓库已在 `abed855`（Issue #71）切为本地化开发环境，8080 由
  宿主机 `goserver` 进程提供，前端容器不参与服务；静态目录是 `backend/main.py:58` 的
  `frontend/static`（详见 plan 的「部署路径的澄清」）
- [x] T022b 解决 `frontend/static/assets` 属主为 root 导致 `npm run build` 失败：父目录
  可写，故整体替换（`mv static static.root-old && mv /tmp/fe-final static`），无需 sudo。
  替换后该目录完全归当前用户，后续构建不再撞权限
- [x] T022c 恢复 Docker Hub 可用性：从 `docker.m.daocloud.io` 拉取 `node:22-alpine` 与
  `nginx:alpine` 并打官方标签，`docker compose build frontend` 已可成功（对本地化环境非
  必需，但恢复了容器化部署的可行性）
- [x] T023 产物核对（`frontend/static/assets/`）：两 bundle 各含 2 处 `pre-wrap` 且均带
  `fontSize:12`；`fontWeight:600` + `pre-wrap` 残留为 0；`/search` 返回 200（SC-005）
- [x] T023b 撤回越界改动：收尾时误将 `tests/07_researcher_community_forum` 加入 vitest
  include，超出 #69 范围且暴露该目录 6 个既有失败。已移除，只保留 `@mui/material` 别名

## 阶段 6：文档

- [x] T024 创建 GitHub Issue [#69](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/69)，
  含主题 variant 对照表与「改 body2 仍大 1px」的取舍说明
- [x] T025 编写 `docs/specs/69-detail-text-hierarchy/`（spec、plan、tasks）
- [x] T026 回写 `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/paper-and-property-results.md`

## 依赖与执行顺序

- **T001-T003**（量化）：须先读主题定义，否则无法判断字号关系
- **T004-T007**（枚举）：依赖 T002；必须在动手前完成
- **T008-T011**（实施）：依赖 T004-T007 的清单
- **T012-T013**（测试基建）：T013 依赖 T012 的别名
- **T014-T017**（用例）：依赖 T008-T013
- **T018-T023**（验证）：依赖全部实现与测试
- **T024-T026**（文档）：依赖验证完成

**关键路径**：T001→T002→T004→T007→T008→T012→T015→T017→T020→T023

## 需求覆盖

| 来源 | 任务 | 验证 |
|------|------|------|
| FR-001（不加粗） | T008、T010 | T014 |
| FR-002（不超标签字号） | T008-T010 | T015 |
| FR-003（两字段一致） | T009 | T016 |
| FR-004（两页面一致） | T010 | T023 产物核对 |
| FR-005（methodology 兜底） | T011 | 代码审查 |
| FR-006（主题下测量） | T012、T013 | T017 反向验证 |
| SC-001 | T014 | 通过 |
| SC-002 | T015 | 通过 |
| SC-003 | T016 | 通过 |
| SC-004 | T017 | 还原后 3 例失败 |
| SC-005 | T023 | 两 bundle 各 2 处 |
| SC-006 | T019、T020 | 通过 |

## 遗留事项

- **旧产物目录待删除**：整体替换时保留的原 `frontend/static`（内含 root 属主文件）已移出
  仓库至 `/tmp/sc-wiki-static-root-old`——`.gitignore` 只忽略 `frontend/static/`，留在原地
  会污染 git 状态。需 `sudo rm -rf /tmp/sc-wiki-static-root-old` 彻底清理，不影响服务。
- **`fontSize: 12` 不走 variant 体系**：为满足「不超过标签字号」显式覆盖。若日后整理全站
  排版规范，应考虑新增一个 12px 正文 variant 替代就地覆盖。
- **`tests/07_researcher_community_forum` 有 6 个既有失败**：图表坐标系、参考线、家族多选
  等，与本 Issue 无关（`git stash` 前后对比确认）。该目录当前不在 vitest include 中，问题
  被掩盖，值得单独立项。
- **标签与正文的层级约定未成规范**：本次只修一个区块。该约定值得整理成全站规范并用组件
  封装或 lint 约束，属独立议题。
