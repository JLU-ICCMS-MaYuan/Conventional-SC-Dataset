# 实施任务：已提交论文详情页持久入口

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[contracts/routing.md](contracts/routing.md)、[quickstart.md](quickstart.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：基础能力

**目的**：建立可寻址的详情页页面壳与路由注册，阻断后续全部用户故事。

- [x] T001 新建 `frontend/src/pages/PaperDetailPage.tsx`：用 `useParams` 读取 `:id` 并本地校验为正整数，调用 `GET /api/papers/{id}` 加载数据，按 `ApiError.status` 分流 400/403/404/其他四类失败（失败时不渲染 `PaperEditView`），`onBack` 用 `useNavigate` 导航至 `/upload`
- [x] T002 改 `frontend/src/LazyRoutes.tsx`：`lazy` 引入 `PaperDetailPage` 并注册 `<Route path="/papers/:id">`，不包裹 `RoleRoute`（理由见 contracts/routing.md「路由契约」）

## 阶段 2：用户故事 1——提交后随时回到详情页复查（P1，MVP）

**目标**：详情页可达性由 URL 决定，刷新、前进/后退与直接访问地址都能到达同一篇论文。

**独立验收**：quickstart 场景 1、2、4——刷新停留在详情页；返回后前进仍可回到；提交成功后直达
`/papers/<id>`。

### 测试

- [x] T003 [P] [US1] 新建 `tests/01_decentralized_uploading/paper-detail-route.test.tsx`：断言给定 `/papers/4` 渲染出该论文只读详情、不同 `:id` 渲染不同论文、点击返回触发导航至 `/upload`

### 实施

- [x] T004 [US1] 改 `frontend/src/components/PaperEditView.tsx`：移除内部 `loadPaper`／`api.get` 与 `loading`/`error` 状态，改为通过 props 接收已就绪的 `paper` 数据与 `onBack`；字段渲染、`editKps` 与编辑态代码保持不动（清理属 #57）
- [x] T005 [US1] 改 `frontend/src/pages/UploadPage.tsx`：删除 `stage`/`detailPaperId` 状态、`handleDetailOpen`/`handleDetailBack` 与 `stage === 'detail'` 渲染分支及 `PaperEditView` 引入；`handleTaskSubmitted` 与 `openExistingPaper` 改为 `navigate('/papers/<id>')`

## 阶段 3：用户故事 2——无权访问时得到明确提示（P2）

**目标**：无权、不存在、编号无效三类访问各自给出可区分提示，且不泄漏论文内容。

**独立验收**：quickstart 场景 3——三类提示文案互不相同；无效编号不发起网络请求；无权时页面
无任何论文字段。

### 测试

- [x] T006 [US2] 在 `tests/01_decentralized_uploading/paper-detail-route.test.tsx` 追加 4 个失败分支用例：403 显示无权提示、404 显示不存在提示、非数字 `:id` 显示编号无效且未调用 `api.get`、其他异常显示加载失败；每个用例断言页面不含论文标题

### 实施

- [x] T007 [US2] 在 `frontend/src/pages/PaperDetailPage.tsx` 补齐四类失败文案与返回操作，确认前端无角色判断、无 `review_status` 判断（FR-005）

## 最终阶段：完善与跨故事事项

- [x] T008 全量验证：`cd frontend && npm run test:upload-ui` 7 文件 53 用例全通过（原 45 + 新增 8）、`npx tsc --noEmit` 通过
- [x] T009 重建前端镜像（`cd /home/mayuan/work/SC-Wiki-docker && docker compose -f dev.yaml build frontend && docker compose -f dev.yaml up -d`）后按 quickstart 场景 1–5 人工验收（用户已确认通过）
- [x] T010 将「提交后详情页可达性与入口」回写 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/pdf-ingestion.md`（持久化与可见性段新增 2 条：`/papers/:id` 地址承载与错误分流、「我的论文」入口及与解析任务列表分离的理由），并在相关变更记录追加 Issue #56 链接

## 阶段 4：收敛——首轮验收缺口（US3 与兜底路由）

**来源**：2026-08-26 首轮人工验收。用户确认场景 2 的「浏览器前进」在其浏览器不可用，且
无任何界面入口，必须手工拼接网址才能到达详情页；另发现访问 `/upload/papers/999999`
（相对路径误拼）渲染全白页面。

**差距类型**：missing——原 Spec 将「我的论文」列表列为范围外，导致 FR-002 虽在技术上成立，
但用户的原始诉求「始终能只读复查」未真正达成；未匹配路由无兜底页属遗漏。

- [x] T011 [US3] 新建 `frontend/src/components/MyPapersList.tsx`：调用既有 `GET /api/papers/my-uploads`（`goserver/handlers/admin.go:621`，无需新增后端接口），按提交时间倒序展示标题与审核状态，每条可点击进入 `/papers/:id`；含空状态与加载失败提示
- [x] T012 [US3] 改 `frontend/src/pages/AccountPage.tsx`：新增「我的论文」区块并挂载 `MyPapersList`（FR-007、FR-010——不放上传页，理由见 spec.md 澄清记录）
- [x] T013 [US3] 改 `frontend/src/pages/PaperDetailPage.tsx`：详情页头部增加「我的论文」入口，导航至 `/account`（FR-008）。注：原计划改 `UploadPage` 的 Snackbar 加「查看详情」，实测 `handleTaskSubmitted` 提交成功后已直接 `navigate` 到详情页、Snackbar 随页面卸载消失，该按钮不可见；真实缺口是离开详情页后回不去
- [x] T014 新建 `frontend/src/pages/NotFoundPage.tsx` 并在 `frontend/src/LazyRoutes.tsx` 注册 `path="*"` 兜底路由：显示「页面不存在」与返回操作，消除白屏（FR-009）
- [x] T015 [P] 在 `tests/01_decentralized_uploading/paper-detail-route.test.tsx` 追加用例：「我的论文」列表渲染并可点击进入详情、空状态、加载失败提示、未匹配地址显示「页面不存在」
- [x] T016 全量验证：`cd frontend && npm run test:upload-ui` 7 文件 58 用例全通过（新增 5 个：详情页「我的论文」入口、列表渲染可点击、空状态、加载失败重试、误拼地址兜底）、`npx tsc --noEmit` 通过
- [x] T017 重建前端镜像（`cd /home/mayuan/work/SC-Wiki-docker && docker compose -f dev.yaml build frontend && docker compose -f dev.yaml up -d`）后按 quickstart 场景 6–8 人工验收（用户已确认通过）

## 依赖与执行顺序

- T001 → T002 串行（路由注册依赖页面壳存在）。
- T003 可与 T004、T005 并行编写（独立新文件），但需在 T001 完成后才能运行通过。
- T004 → T005 串行语义：`UploadPage` 移除 `PaperEditView` 引入依赖 T004 完成 props 改造。
- T006、T007 同改 `PaperDetailPage.tsx` 与同一测试文件，必须在 T003–T005 之后串行执行。
- T008 依赖全部实现任务；T009 依赖镜像重建（运维前置）；T010 依赖 T009 人工验收通过。
- 阶段 4：T011 → T012 串行（区块挂载依赖列表组件存在）；T013、T014 改不同文件，可与 T011 并行；
  T015 依赖 T011–T014 全部完成；T016 依赖 T015；T017 依赖镜像重建。
- T009 与 T010 的收尾判定改以阶段 4 完成为前提：入口缺失时 Feature 不算交付完整。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001 / US1 | T001、T002 | 页面壳按 URL 参数寻址并注册路由 |
| FR-002 / US1 | T001、T003、T009 | 内容仅由 URL 决定；测试断言不同 `:id`；场景 1、2 验证刷新与前进 |
| FR-003 / US1 | T005、T009 | 提交成功后路由跳转；场景 4 验证 |
| FR-004 / US1 | T001、T003 | `onBack` 导航至 `/upload` 且详情地址仍可用 |
| FR-005 / US2 | T007 | 确认前端零权限判定，只按状态码分流 |
| FR-006 / US2 | T006、T007 | 四类失败分流与不泄漏内容断言 |
| SC-001 / SC-002 | T009 | quickstart 场景 1、2 |
| SC-003 | T006、T009 | 失败分支用例 + 场景 3 |
| SC-004 | T008、T009 | 既有 45 用例全通过 + 场景 5 无回归 |
| FR-007 / US3 | T011、T012、T015 | 用户页「我的论文」列表与可点击进入 |
| FR-008 / US3 | T013、T015、T017 | 详情页前往「我的论文」的入口 |
| FR-009 | T014、T015 | 兜底路由消除白屏 |
| FR-010 | T012 | 列表置于用户页而非上传页活动任务区 |
| SC-005 | T011–T013、T017 | 两次点击内到达任意已提交论文详情 |
| SC-006 | T014、T015、T017 | 未定义地址不再白屏 |

## MVP 与增量策略

1. 完成 T001、T002 建立可寻址页面壳。
2. 完成 US1（T003–T005）即可独立验收核心缺陷修复：详情页不再因返回而永久丢失。
3. 加入 US2（T006、T007）补齐失败语义，不影响 US1 已交付能力。
4. T008–T010 收尾：自动化验证、人工验收、Overview 回写。
