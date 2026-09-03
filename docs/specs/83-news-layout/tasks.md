# 实施任务：News 页面品牌信息与三列独立资讯流

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[quickstart.md](quickstart.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：建立可观察的品牌、三列独立查询和交互回归基线。

- [x] T001 在 `tests/03_data_search_and_database_discovery/news-page-layout.test.tsx` 创建 News 页面测试夹具，覆盖三类各至少 6 条的 API 响应和中英文渲染。
- [x] T002 [US1] 在 `tests/03_data_search_and_database_discovery/news-page-layout.test.tsx` 先编写双语品牌、删除入口与 `/search` 跳转的失败测试。
- [x] T003 [US2] 在 `tests/03_data_search_and_database_discovery/news-page-layout.test.tsx` 先编写每栏 `page_size=5`、类型隔离和单栏 `Next` 不影响其他栏的失败测试。
- [x] T004 [US3] 在 `tests/03_data_search_and_database_discovery/news-page-layout.test.tsx` 先编写空/失败隔离、详情抽屉与安全外链的失败测试。

## 阶段 2：用户故事 1——品牌与唯一探索入口（P1，MVP）

**目标**：读者可识别双语站点定位，并从唯一 Hero 按钮进入 Explore 页面。

**独立验收**：中英文文案准确；四个指定入口不存在；按钮进入 `/search`。

### 实施

- [x] T005 [P] [US1] 修改 `frontend/src/i18n/zh/news.ts`，写入已确认的中文品牌、机构署名与 Hero 简介，移除不再使用的 AI 助手文案键。
- [x] T006 [P] [US1] 修改 `frontend/src/i18n/en/news.ts`，写入已确认的英文品牌、机构署名与 Hero 简介，移除不再使用的 AI 助手文案键。
- [x] T007 [US1] 修改 `frontend/src/pages/NewsPage.tsx`，渲染本地化机构署名，删除三张功能卡和 AI 助手按钮，并保留标题下方跳至 `/search` 的主行动按钮。

## 阶段 3：用户故事 2——三列独立资讯浏览（P1）

**目标**：读者在一个紧凑桌面视图中并列浏览三种类型，每栏独立翻页。

**独立验收**：每类至少 6 条数据时，各栏初始仅 5 条；任一 `Next` 只替换所在栏。

### 实施

- [x] T008 [US2] 重构 `frontend/src/components/NewsFeed.tsx`，以固定类型可复用资讯列封装独立页码、请求、加载、失败、重试、空状态和分页，并固定使用 `page_size=5`。
- [x] T009 [US2] 修改 `frontend/src/components/NewsFeed.tsx`，在页面级组装 News、Preprints、Articles 三个列，保留一个共享详情抽屉和一个来源状态区。
- [x] T010 [US2] 修改 `frontend/src/pages/NewsPage.tsx` 与 `frontend/src/components/NewsFeed.tsx`，完成桌面三列与窄屏纵向响应式布局，保证 1440×900 首屏的分页可见性。

## 阶段 4：用户故事 3——保留详情与异常反馈（P2）

**目标**：三列布局不损失既有的资讯详情和异常可见性。

**独立验收**：任意栏的条目可打开详情；一栏失败或为空时其他栏不受影响。

### 实施

- [x] T011 [US3] 修改 `frontend/src/components/NewsFeed.tsx`，使每个列条目都能更新共享选中项并复用现有详情抽屉、安全外链和来源状态行为。

## 最终阶段：完善与验证

- [x] T012 [US1] [US2] [US3] 运行 `frontend/node_modules/.bin/vitest run --config vitest.config.ts tests/03_data_search_and_database_discovery/news-page-layout.test.tsx`、英文全站巡检和 `npm --prefix frontend run build`，修复本 Feature 引入的回归。
- [x] T013 [US2] [US3] 按 `docs/specs/83-news-layout/quickstart.md` 完成真实页面验收；用户确认三栏布局，并在发现行高和分页未对齐后完成修复与复核。
- [x] T014 [US1] [US2] [US3] 实现验收后更新 `docs/overview/news.md`，记录实际已落地的三列分页布局，并回写 Issue #83 的 Documentation Impact。

## 依赖与执行顺序

- T001 是 T002–T004 的测试夹具基础。
- T002–T004 必须先于其对应实现任务。
- T005、T006 可并行；T007 依赖两项文案完成。
- T008 阻断 T009–T011；T009 与 T010、T011 修改同一组件，应串行。
- T012 依赖全部实现任务；T013 依赖 T012；T014 仅在实现和浏览器验收通过后执行。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001–FR-003 / SC-001 | T002、T005–T007、T012 | 双语品牌、删除范围和 Explore 跳转 |
| FR-004–FR-005 / SC-002 | T003、T008–T010、T012 | 三种类型、5 条限制和独立分页 |
| FR-006 / SC-003 | T010、T013 | 桌面首屏与窄屏响应式验收 |
| FR-007 / SC-004 | T004、T008–T011、T012–T013 | 状态隔离、详情抽屉和安全外链 |
| SC-005 | T012 | 自动化测试与生产构建 |

## MVP 与增量策略

1. 完成 T001–T010 后，品牌、唯一入口和三列独立分页可独立交付。
2. 完成 T011 后，保留详情与异常体验。
3. 完成 T012–T014 后，获得可验证的交付证据和当前功能文档回写。

## 阶段 5：收敛——三栏垂直对齐

- [x] T015 [US2] 修改 `frontend/src/components/NewsFeed.tsx`，为五个资讯槽位和分页区域设置稳定尺寸，使三栏内容行与底部分页控件对齐；通过 News 专项测试、英文全站巡检和前端生产构建验证。
