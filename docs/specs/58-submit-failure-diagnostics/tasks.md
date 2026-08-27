# 实施任务：提交审核失败的可诊断性与必填定位

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[contracts/error-response.md](contracts/error-response.md)、[quickstart.md](quickstart.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

本 Feature 无需项目级准备工作：依赖、测试框架、部署编排均已就绪，不新增依赖与数据库迁移。

## 阶段 2：基础能力

无跨故事阻断依赖。三个用户故事触及不同文件（`chunker.py`+`rag.py` / `main.py` / `UploadTaskEditor.tsx`），可并行推进。

## 阶段 3：用户故事 1——解析噪声不再阻断提交且正文不丢失（P1，MVP）

**目标**：被误判为 `##` 标题的正文段落不再导致提交 500，且其文字进入可检索内容。

**独立验收**：ThH10 任务重新提交成功，三段探针文字出现在 `paper_chunks.content`（quickstart 场景 1、2）。

### 测试

- [x] T001 [P] [US1] 在 `backend/tests/test_upload_jobs.py` 新增分段判定用例：构造含 1389 字符 `##` 行的 Markdown，断言该行文字进入某个 chunk 的 `content`、其 `section_name` 沿用前一个真实章节名（FR-001、FR-002、SC-002）
- [x] T002 [P] [US1] 在 `backend/tests/test_upload_jobs.py` 新增边界用例：无任何 `##` 标题、全部 `##` 行超长（断言不产出零块）、超长行位于首个真实章节之前（断言回退「全文」）（Spec 边界场景 1–3）
- [x] T003 [P] [US1] 在 `backend/tests/test_upload_jobs.py` 新增短标题无回归用例：65–204 字符的真实标题仍作为 `section_name`，分段结果与修复前一致（FR-001、SC-003）

### 实施

- [x] T004 [US1] 修改 `backend/ingest/chunker.py` 的 `_split_by_h2`：按 300 字符阈值判定 `##` 行；超长行不作为章节边界，其整行文本并入前一节 `body` 并沿用该节 `section_name`；无前置真实章节时归入「全文」（FR-001、FR-002；research D1）
- [x] T005 [US1] 修改 `backend/api/rag.py` 的 `PaperChunk` 写入点（约 `:1097-1108`）：`section_name` 与 `heading` 按 500 字符安全截断作为第二道防线（FR-003；research D2）
- [x] T006 [US1] 运行 `docker compose -f /home/mayuan/work/SC-Wiki-docker/dev.yaml exec -T python python -m pytest backend/tests/test_upload_jobs.py -q` 并确认 T001–T003 全部通过

## 阶段 4：用户故事 2——后端异常给出可理解原因（P1）

**目标**：任何未捕获异常都返回结构化 `{code, message}`，前端不再退化为通用文案；响应体不泄漏内部信息。

**独立验收**：契约测试断言响应体结构且不含 SQL、堆栈、内部路径（quickstart 场景 3）。

### 测试

- [x] T007 [P] [US2] 新增 `backend/tests/test_submit_error_contract.py`：构造一个抛未预期异常的临时路由，经真实 FastAPI 请求断言响应体为 `{"detail": {"code": "internal_error", "message": ...}}`、状态码 500（FR-004；research D8 要求经真实路由验证）
- [x] T008 [US2] 在 `backend/tests/test_submit_error_contract.py` 增加泄漏断言：响应体不含 `asyncmy`、`DataError`、`section_name`、`INSERT`、`/app/backend/`（FR-005）
- [x] T009 [US2] 在 `backend/tests/test_submit_error_contract.py` 增加既有契约无回归断言：`_upload_error` 产出的 400/409 响应不被全局处理器改写（FR-006、US2 场景 4）

### 实施

- [x] T010 [US2] 修改 `backend/main.py`：注册全局异常处理器，返回 `{"detail": {"code": "internal_error", "message": "<中文说明>"}}`，异常原文仅写服务端日志（FR-004、FR-005；research D4）
- [x] T011 [US2] 运行 `docker compose -f /home/mayuan/work/SC-Wiki-docker/dev.yaml exec -T python python -m pytest backend/tests/test_submit_error_contract.py -q` 并确认 T007–T009 通过

## 阶段 5：用户故事 3——必填校验定位到字段（P1）

**目标**：提交失败时展开出错卡片、滚动聚焦到字段、字段标红、横幅汇总全部缺失项。

**独立验收**：构造缺少「材料」的材料状态并提交，卡片展开、字段聚焦标红、横幅列出全部项（quickstart 场景 4）。

### 测试

- [x] T012 [P] [US3] 新增 `tests/01_decentralized_uploading/submit-validation-feedback.test.tsx`：断言多处缺失时横幅汇总全部项而非仅第一条（FR-007、FR-009）
- [x] T013 [US3] 在同文件新增用例：出错字段位于默认折叠卡片内时该卡片被展开、字段获得焦点并显示错误态（FR-008、FR-009、SC-005）
- [x] T014 [US3] 在同文件新增用例：模拟后端 400 `invalid_pressure_range`（message 含「第 N 个材料状态」），断言解析序号并定位；另断言无法解析序号时仅显示横幅不报错（FR-010、边界场景 4；research D6 要求专门测试保护该脆弱耦合）
- [x] T015 [US3] 在同文件新增用例：修正后提交成功清除全部错误态与横幅（FR-011）

### 实施

- [x] T016 [US3] 修改 `frontend/src/components/UploadTaskEditor.tsx` 的 `validate()`（约 `:619-649`）：签名由 `string | null` 改为返回 `ValidationIssue[]`，收集全部问题而非遇错即 return，每项含 `stateIndex`/`field`/`message`（FR-007；contracts 第 2 节）
- [x] T017 [US3] 修改 `frontend/src/components/UploadTaskEditor.tsx`：为 contracts 第 2.1 节列出的各字段添加 `data-*` 定位锚点，避免依赖 MUI 内部 DOM 结构（FR-008；research D5）
- [x] T018 [US3] 修改 `frontend/src/components/UploadTaskEditor.tsx` 的 `submit()`（约 `:651-681`）：校验失败时展开对应卡片、滚动并聚焦首个错误字段、渲染字段错误态、横幅汇总全部 message；提交成功时清除（FR-008、FR-009、FR-011）
- [x] T019 [US3] 修改 `frontend/src/components/UploadTaskEditor.tsx`：后端 400 响应按 `detail.message` 解析材料状态序号并做同样定位；解析失败时仅显示横幅（FR-010）
- [x] T020 [US3] 运行 `cd frontend && npm run test:upload-ui` 与 `npx tsc --noEmit`，确认 T012–T015 通过且既有 58 用例无回归（SC-006）

## 最终阶段：完善与跨故事事项

- [x] T021 后端全量回归：`docker compose -f /home/mayuan/work/SC-Wiki-docker/dev.yaml exec -T python python -m pytest backend/tests -q --ignore=backend/tests/test_concurrency.py`（SC-006）
- [x] T022 重建后端与前端镜像：`docker compose -f dev.yaml build python frontend && docker compose -f dev.yaml up -d python worker frontend`（在 `/home/mayuan/work/SC-Wiki-docker` 执行）。注：后端代码打进镜像而非 bind mount，仅 `restart python` 不会生效，原任务描述已按此更正
- [x] T023 按 [quickstart.md](quickstart.md) 场景 1、2 人工验收：ThH10 提交成功、三段探针文字入库且 `section_name` ≤ 500（SC-001、SC-002）
  - 证据：`papers` 表出现 id=8（`upload_task_id=946c56c2a2854b2d8b8bba08518cba43`，2026-08-27 04:59:37 创建），修复前该任务 500 失败；55 个 chunk，`MAX(CHAR_LENGTH(section_name))=178`、`heading=181`（修复前 1389）；三段探针文字各命中 1 次；`logs python | grep -c DataError` 为 0
- [x] T024 按 [quickstart.md](quickstart.md) 场景 4、5 人工验收：必填定位与后端专属规则定位（SC-005）（用户已确认验收通过）
- [x] T025 按 [quickstart.md](quickstart.md) 场景 6 人工验收：短标题分段无回归、DOI 重复 409 与一致性确认 409 行为不变（SC-003、SC-006）（用户已确认验收通过）
- [x] T026 使用 `big-project-overview-maintainer` 将「分段对解析噪声的鲁棒性」与「提交失败的结构化原因与必填定位」回写 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/pdf-ingestion.md`，并在相关变更记录追加 Issue #58 链接
- [x] T027 交由 `big-project-issue-manager` 回写 Spec 链接并在全部门槛满足后关闭 Issue #58

## 依赖与执行顺序

- 阶段 1、2 无实际任务，不阻断。
- 三个用户故事互不依赖，可并行：US1 改 `chunker.py`+`rag.py`，US2 改 `main.py`，US3 改 `UploadTaskEditor.tsx`。
- 故事内部：测试先于实施（T001–T003 → T004–T005；T007–T009 → T010；T012–T015 → T016–T019）。
- 同文件任务串行：T004 与 T005 在不同文件可并行；T016–T019 同在 `UploadTaskEditor.tsx`，必须串行。
- T021 依赖 T006、T011；T022 依赖全部实施任务；T023–T025 依赖 T022；T026 依赖 T023–T025 全部通过；T027 依赖 T026。
- `[P]` 标记的任务位于不同文件且无未完成依赖。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001 / US1 | T001、T003、T004 | 阈值判定 + 短标题无回归 |
| FR-002 / US1 | T001、T004、T023 | 探针文字进入 `content` |
| FR-003 / US1 | T005、T023 | 写入前截断，第二道防线 |
| FR-004 / US2 | T007、T010 | 结构化异常响应 |
| FR-005 / US2 | T008、T010 | 不泄漏 SQL、堆栈、路径 |
| FR-006 / US2 | T009 | 既有 `_upload_error` 契约不被改写 |
| FR-007 / US3 | T012、T016 | `validate` 返回清单 |
| FR-008 / US3 | T013、T017、T018、T024 | 卡片展开 + 滚动聚焦 |
| FR-009 / US3 | T012、T013、T018 | 字段错误态 + 横幅汇总 |
| FR-010 / US3 | T014、T019、T024 | 后端错误码定位 |
| FR-011 / US3 | T015、T018 | 提交成功清除错误态 |
| SC-001 | T023 | ThH10 提交成功 |
| SC-002 | T001、T023 | 三探针命中 |
| SC-003 | T003、T025 | 真实标题无回归 |
| SC-004 | T007、T008 | 异常原因可理解且不泄漏 |
| SC-005 | T013、T024 | 定位反馈可见 |
| SC-006 | T020、T021、T025 | 前后端全量回归 + 既有 409 分支 |
| 边界场景 1–3 | T002 | 无标题 / 全超长 / 无前置章节 |
| 边界场景 4 | T014 | 错误码无法解析时不阻断 |
| 边界场景 5 | T025 | 校验通过但 409 的既有路径 |

## MVP 与增量策略

1. **MVP = US1**：解除硬阻塞。此类 PDF 当前完全无法提交，US1 单独交付即可让用户的校对工作落地。
2. **US2**：保证下一个未知故障源不再退化为无信息量的通用文案。
3. **US3**：交付用户原始诉求的正面表达——失败后知道该改哪里。
4. 三者可并行实施，但按上述顺序验收，任一故事完成后前序故事仍可用。
