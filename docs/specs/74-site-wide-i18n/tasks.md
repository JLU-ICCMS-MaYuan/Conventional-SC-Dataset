# 实施任务：全站中英文界面切换，数据层统一英文

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：确认迁移链与测试基线，避免把既有问题误判为本 Feature 引入。

- [x] T001 执行 `python -m alembic current` 与 `SHOW COLUMNS FROM papers LIKE 'knowledge_graph_title'`，确认 `alembic_version` 指向 `add_kg_title` 且该列存在（本地曾用 `alembic stamp head` 对齐而未真正 upgrade，见 [quickstart.md](quickstart.md) 前置条件）
- [x] T002 执行 `scripts/run-tests.sh frontend`、`go`、`backend` 记录基线，确认 `tests/07_researcher_community_forum/news-feed.test.tsx` 的既有失败用例，后续不计入本 Feature 回归

## 阶段 2：基础能力

**目的**：i18n 基建。本阶段阻断全部用户故事，且 Issue #75、#76 依赖其完成。

- [x] T003 新增 `frontend/src/i18n/index.ts`：定义 `Lang` 类型、字典类型（以中文字典推导）、聚合导出（契约 [i18n-frontend.md](contracts/i18n-frontend.md) F3）
- [x] T004 [P] 新增 `frontend/src/i18n/zh/common.ts` 与 `frontend/src/i18n/en/common.ts`：通用文案（确认、取消、保存、删除、加载中、暂无数据）
- [x] T005 [P] 新增 `frontend/src/i18n/zh/enums.ts` 与 `frontend/src/i18n/en/enums.ts`：七类固定枚举标签按 `value` 索引（F4、R2）
- [x] T006 新增 `frontend/src/context/LanguageContext.tsx`：`lang`/`setLang`/`t(key, vars?)`，localStorage 键 `sc-wiki.language`，读写 try/catch 且非法值回退 `zh`（F1、F2、F7；FR-003、FR-005、FR-006）
- [x] T007 修改 `frontend/src/main.tsx`：在 `AuthProvider` 外层挂载 `LanguageProvider`（F1）
- [x] T008 修改 `frontend/src/lib/classifications.ts`：新增 `familyName(term, lang)`，英文缺失回退中文名（F5；FR-009、FR-010）

## 阶段 3：用户故事 1——语言切换与界面文案（P1，MVP）

**目标**：非中文研究者可把整站界面切为英文并持久保持。

**独立验收**：未登录点击切换按钮，导航、按钮、表单标签、提示语全部变英文；刷新后保持。

### 测试

- [x] T009 [P] [US1] 在 `tests/02_identity_governance/language-switch.test.tsx` 新增测试：默认中文、点击切换即时生效、`localStorage` 写入、刷新后保持、存储抛异常时不白屏（FR-003、FR-004、FR-005、FR-006、SC-002、SC-003）
- [x] T010 [P] [US1] 在 `tests/02_identity_governance/language-switch.test.tsx` 新增无障碍测试：`role="group"`、`aria-label`、两按钮 `aria-pressed` 随语言变化、可键盘聚焦（FR-002、F6）

### 实施

- [x] T011 [US1] 修改 `frontend/src/components/AppShell.tsx`：顶栏头像左侧加 `CH / EN` 两段式控件，当前语言高亮并带 `aria-pressed`；同时替换导航与角色标签文案（FR-001、FR-002、F6）
- [x] T012 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/nav.ts` 并替换 `frontend/src/App.tsx`、`frontend/src/LazyRoutes.tsx`、`frontend/src/pages/NotFoundPage.tsx`、`frontend/src/components/RoleRoute.tsx` 的文案
- [x] T013 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/search.ts` 并替换 `frontend/src/pages/SearchPage.tsx`（216 处）文案
- [x] T014 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/share.ts` 并替换 `frontend/src/pages/share.tsx`（150 处）、`frontend/src/components/ChartScatter.tsx`（96 处）、`frontend/src/lib/scatterConfig.ts`（89 处）、`frontend/src/lib/chartPreferences.ts`（20 处）、`frontend/src/components/ChartGroupEditor.tsx`（66 处）文案
- [x] T015 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/news.ts` 并替换 `frontend/src/pages/NewsPage.tsx`（100 处）、`frontend/src/components/NewsFeed.tsx`（66 处）文案
- [x] T016 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/paperDetail.ts` 并替换 `frontend/src/components/PaperEditView.tsx`（102 处）、`frontend/src/lib/paperDetailView.ts`（92 处）、`frontend/src/pages/PaperDetailPage.tsx`、`frontend/src/components/MyPapersList.tsx`、`frontend/src/components/StructureViewer3D.tsx` 文案
- [x] T017 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/upload.ts` 并替换 `frontend/src/pages/UploadPage.tsx`（80 处）、`frontend/src/components/UploadTaskCenter.tsx`、`frontend/src/components/UploadParsingDetail.tsx`、`frontend/src/components/MultiFileUploadPanel.tsx`、`frontend/src/components/StructureCandidatePanel.tsx`、`frontend/src/components/EvidenceCard.tsx` 文案
- [x] T018 [US1] 新增 `frontend/src/i18n/{zh,en}/upload.ts` 的校对器条目并替换 `frontend/src/components/UploadTaskEditor.tsx`（264 处）文案；与 T017 同字典文件故串行
- [x] T019 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/admin.ts` 并替换 `frontend/src/pages/AdminPage.tsx`（289 处）文案
- [x] T020 [P] [US1] 替换 `frontend/src/components/SuperAdminGovernance.tsx`（66 处）、`frontend/src/components/NewsManager.tsx`、`frontend/src/components/UsernameField.tsx`、`frontend/src/lib/username.ts` 文案，复用 `admin.ts` 字典
- [x] T021 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/account.ts` 并替换 `frontend/src/pages/AccountPage.tsx`（67 处）、`frontend/src/components/AuthDialog.tsx`（44 处）、`frontend/src/pages/PublicUserPage.tsx`、`frontend/src/context/AuthContext.tsx` 文案
- [x] T022 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/rag.ts` 并替换 `frontend/src/pages/RagPage.tsx`、`frontend/src/lib/useStreamingChat.ts`、`frontend/src/components/MarkdownMessage.tsx` 文案
- [x] T023 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/kg.ts` 并替换 `frontend/src/pages/KnowledgeGraphPage.tsx`（42 处）文案
- [x] T024 [P] [US1] 新增 `frontend/src/i18n/{zh,en}/tcPredict.ts` 并替换 `frontend/src/pages/TcPredictPage.tsx` 文案
- [x] T025 [P] [US1] 替换外部数据源组件文案：`frontend/src/components/AlexandriaDetail.tsx`（46 处）、`frontend/src/components/HtscDetail.tsx`、`frontend/src/components/PeriodicTable.tsx`、`frontend/src/lib/paperProcessing.ts`、`frontend/src/components/ClassificationAutocomplete.tsx`
- [x] T026 [US1] 在 `tests/03_data_search_and_database_discovery/english-ui-sweep.test.tsx` 新增巡检测试：英文模式下渲染各页面主视图，断言无中日韩字符（SC-001）

## 阶段 4：用户故事 2——枚举与分类目录双语（P1）

**目标**：英文界面下下拉选项与分类家族名为英文。

**独立验收**：英文界面打开校对页，全部下拉与家族名为英文，提交值不变。

### 测试

- [x] T027 [P] [US2] 在 `tests/01_decentralized_uploading/enum-labels-i18n.test.tsx` 新增测试：七类枚举标签随语言切换，选中后提交值不变（FR-008、SC-009）
- [x] T028 [P] [US2] 在 `tests/01_decentralized_uploading/enum-labels-i18n.test.tsx` 新增测试：seed 家族显示英文名，自建家族（`name_en` 空）英文界面回退中文名（FR-009、FR-010）
- [x] T029 [P] [US2] 在 `goserver/handlers/classifications_i18n_test.go` 新增 Go 测试：目录响应含 `name`、`name_zh`、`name_en` 且 `name === name_zh`（契约 [bilingual-api.md](contracts/bilingual-api.md) C1）

### 实施

- [x] T030 [P] [US2] 修改 `goserver/handlers/classifications.go` 的 `serializeCatalog`：增加 `name_zh` 与 `name_en` 输出，保留 `name` 键兼容（C1、R3）
- [x] T031 [P] [US2] 修改 `backend/services/classification_catalog.py` 的 `load_active_catalogs` 序列化：同步增加 `name_zh` 与 `name_en`，保持两服务响应形状一致（C1）
- [x] T032 [US2] 修改 `frontend/src/components/UploadTaskEditor.tsx`、`frontend/src/pages/AdminPage.tsx`、`frontend/src/components/PaperEditView.tsx`、`frontend/src/lib/classifications.ts`：枚举标签改为查 `enums.ts` 字典、家族名改用 `familyName()`（FR-008–FR-010、F4、F5）
## 阶段 5：用户故事 3——解析产出英文叙述字段（P2）

**目标**：新解析论文的六个叙述字段为英文，与论文原文语言一致。

**独立验收**：解析一篇新 PDF，六个字段内容为英文且不含中日韩字符。

### 测试

- [x] T033 [P] [US3] 在 `backend/tests/test_narrative_english_output.py` 新增测试：解析汇总 prompt 要求英文产出，六个字段键名不变（FR-011、[research.md](research.md) R4）
- [x] T034 [P] [US3] 在 `backend/tests/test_narrative_english_output.py` 新增测试：某字段无原文依据时为空，不产出编造内容（FR-012）

### 实施

- [x] T035 [US3] 修改 `backend/ingest/upload_jobs.py` 的 `SUMMARY_SYSTEM_PROMPT`：`summary`、`keywords_tags`、`methodology`、`key_finding`、`research_motivation`、`knowledge_graph_title` 六个字段全部改为英文产出要求；`knowledge_graph_title` 的字数约束由「15-30 字（中文）」改为纯英文词数（FR-011）
- [x] T036 [P] [US3] 修改 `backend/ingest/extractor.py` 第 34、49-50 行：`summary` 的「中文总结，100-200字」与 `keywords_tags` 的「5-10 个中文关键词」改为英文产出要求（FR-011）
- [x] T037 [US3] 修改 `frontend/src/components/UploadTaskEditor.tsx` 与 `frontend/src/components/PaperEditView.tsx`：六个字段的展示不随界面语言变化，两种语言下都显示同一份内容（FR-014）

## 阶段 6：用户故事 4——存量中文数据转换（P2）

**目标**：库内已有的中文叙述字段转为英文，消除语言混杂。

**独立验收**：转换后库内六个字段无中日韩字符；脚本在验证完成后已删除。

### 测试

- [x] T038 [P] [US4] 在 `backend/tests/test_narrative_backfill.py` 新增测试：空字段被跳过、单篇失败时继续处理其余论文并输出失败清单（FR-016）

### 实施

- [x] T039 [US4] 新增一次性脚本 `backend/scripts/convert_narrative_to_english.py`：读取六个字段中含中日韩字符的记录，调 `backend/rag/llm.py` 的 `complete_json` 转为英文后写回；输出处理数、成功数、跳过数与失败清单（FR-015、FR-016）
- [x] T040 [US4] 执行转换脚本处理存量数据（当前库中 1 篇论文），核对六个字段已为英文；确认 `papers.id=9` 的 `knowledge_graph_title` 双重编码损坏被英文内容覆盖修复（FR-015、SC-005、R5）
- [x] T041 [US4] 转换验证通过后删除 `backend/scripts/convert_narrative_to_english.py` 与 `backend/tests/test_narrative_backfill.py`，确认代码库中不存在一次性脚本（FR-017、SC-008）

## 阶段 7：用户故事 5——管理员编辑英文叙述字段（P2）

**目标**：管理员能校正 LLM 产出的英文内容，且 `knowledge_graph_title` 的编辑不再被静默丢弃。

**独立验收**：管理员修改任一叙述字段保存后生效，含 `knowledge_graph_title`。

### 测试

- [x] T042 [P] [US5] 在 `goserver/handlers/papers_test.go` 新增测试：`PUT /api/admin/papers/:id` 与 `PATCH /api/papers/:id` 接受并持久化 `knowledge_graph_title`（FR-019、SC-007、契约 [bilingual-api.md](contracts/bilingual-api.md) C2）
- [x] T043 [P] [US5] 在 `tests/02_identity_governance/admin-narrative-edit.test.tsx` 新增测试：六个叙述字段以单栏呈现且可编辑保存（FR-018、SC-006）

### 实施

- [x] T044 [US5] 修改 `goserver/handlers/admin.go` 的 `paperUpdateFields`（34-39 行）：追加 `knowledge_graph_title`（FR-019、C2、R6）
- [x] T045 [US5] 修改 `goserver/handlers/papers.go` 的 `PatchPaper` 白名单（155-162 行）：追加 `knowledge_graph_title`（FR-019、C2、R6）
- [x] T046 [US5] 修改 `frontend/src/pages/AdminPage.tsx`：编辑弹窗补 `knowledge_graph_title` 输入框，六个叙述字段以单栏英文形式呈现（FR-018）

## 阶段 8：手工快讯英文化（P3）

- [x] T047 [P] 修改 `frontend/src/components/NewsManager.tsx`：录入表单的提示文案说明标题与摘要以英文填写（FR-020）

## 最终阶段：完善与跨故事事项

- [x] T048 执行 `scripts/run-tests.sh frontend`、`go`、`backend` 与 `python -m pytest tests -q`，与 T002 基线比对确认无新增失败（SC-009）
- [x] T049 执行 `cd frontend && npm run build`，确认 `tsc -b` 无类型错误（英文字典缺键会在此暴露）
- [x] T050 按 [quickstart.md](quickstart.md) 全部场景手工走查
- [x] T051 确认代码库中无一次性转换脚本残留（SC-008）
- [x] T052 更新 Issue #74 正文：将「双语数据列」范围修订为「数据层统一英文」，与 Spec 澄清记录一致
- [x] T053 交由 `big-project-overview-maintainer` 回写 `docs/overview/`：README 的语言切换事实、上传解析管线的英文产出、领域模型的叙述字段语言约定

## 依赖与执行顺序

- **阶段 1** 无依赖，T002 基线是 T048 判定回归的前提。
- **阶段 2** 阻断阶段 3–8 全部；T003 阻断 T004、T005，T006 依赖 T003，T007 依赖 T006。
- **阶段 3、4** 均为 P1，可在阶段 2 完成后并行。
- **阶段 5** 阻断阶段 6：存量转换的目标语言由解析 prompt 的产出定义，prompt 未定则转换标准不明。
- **阶段 6** 的 T041 必须在 T040 验证通过后执行，不可提前删除脚本。
- **阶段 7** 与阶段 5、6 无依赖，可并行——白名单缺口与语言无关。
- **阶段 8** 无依赖。

**串行触点（同文件任务必须串行）**：

| 文件 | 涉及任务 |
| --- | --- |
| `frontend/src/components/AppShell.tsx` | T011 |
| `frontend/src/components/UploadTaskEditor.tsx` | T018、T032、T037 |
| `frontend/src/pages/AdminPage.tsx` | T019、T032、T046 |
| `frontend/src/i18n/{zh,en}/upload.ts` | T017、T018 |
| `goserver/handlers/papers.go` | T045 |
| `goserver/handlers/admin.go` | T044 |
| `backend/ingest/upload_jobs.py` | T035 |

**并行机会**：阶段 3 的文案替换任务（T012–T017、T019–T025）分布在不同文件，除标注的串行触点外均可并行；T035 与 T036 分属两个文件可并行；阶段 7 的 T044、T045 分属两文件可并行。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001、FR-002 / US1 | T009、T010、T011 | 切换控件与无障碍属性 |
| FR-003、FR-004、FR-005、FR-006 / US1 | T006、T009 | 默认语言、持久化、失败回退 |
| FR-007 / US1 | T012–T026 | 全站文案替换 |
| FR-008 / US2 | T005、T027、T032 | 枚举标签双语且提交值不变 |
| FR-009、FR-010 / US2 | T008、T028、T030、T031 | 分类目录双语与英文缺失回退 |
| FR-011、FR-012 / US3 | T033–T036 | 解析英文产出 |
| FR-013 / US3 | T035、T036 | 落库内容为英文 |
| FR-014 / US3 | T037 | 展示不随界面语言变化 |
| FR-015、FR-016 / US4 | T038、T039、T040 | 存量转换与失败处理 |
| FR-017 / US4 | T041、T051 | 脚本用后删除 |
| FR-018 / US5 | T043、T046 | 单栏编辑 |
| FR-019 / US5 | T042、T044、T045 | 白名单缺口修复 |
| FR-020 | T047 | 快讯英文录入 |
| FR-021 | T026 | 原文字段不翻译 |
| SC-001 | T026 | 英文界面无中日韩字符 |
| SC-002、SC-003 | T009 | 即时生效与跨会话保持 |
| SC-004 | T033 | 解析产出英文 |
| SC-005 | T040 | 存量转换后无中文 |
| SC-006 | T043 | 编辑保存一致 |
| SC-007 | T042 | 白名单修复 |
| SC-008 | T041、T051 | 脚本已删除 |
| SC-009 | T048 | 三套测试无回归 |

## MVP 与增量策略

1. 完成阶段 1、2：i18n 基建就位，Issue #75、#76 解除阻塞。
2. 完成阶段 3、4（P1）：英文界面已可完成浏览、检索、上传等主要操作——最小可用交付。
3. 完成阶段 5、6（P2）：数据层统一英文，消除语言混杂。
4. 完成阶段 7（P2）：管理员可校正英文内容，并修复既有的静默丢弃缺陷。
5. 完成阶段 8 与收尾。

阶段 3、4 交付后即可独立使用；阶段 5、6 未完成时，叙述字段仍是中文，界面双语不受影响。

## 阶段 9：收敛补漏

- [x] T054 [US3] [收敛：missing] 补齐 `backend/ingest/upload_jobs.py::_normalize_draft` 与 `backend/api/rag.py::_create_pending_paper` 的 `knowledge_graph_title` 传递和落库，避免英文解析结果在归一化或提交时静默丢失（FR-013、FR-019）
