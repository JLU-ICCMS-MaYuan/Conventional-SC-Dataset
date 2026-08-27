# 实施计划：提交审核失败的可诊断性与必填定位

**GitHub Issue**：[#58](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/58)

**日期**：2026-08-26

**Spec**：[spec.md](spec.md)

## 摘要

三条互相独立的改动线，对应三个 P1 用户故事：

1. **分段鲁棒性**（US1）：`_split_by_h2` 按 300 字符阈值判定 `##` 行是否为真实标题，超长行并入前一节正文并沿用其章节名；写入 `PaperChunk` 前对 `section_name`、`heading` 按 500 安全截断作为第二道防线。
2. **异常可诊断**（US2）：在 `backend/main.py` 注册全局异常处理器，把未捕获异常转为 `{code, message}` 结构化响应，异常原文只入服务端日志。
3. **校验可定位**（US3）：`validate()` 由返回单条字符串改为返回错误清单，驱动卡片展开、字段聚焦标红与横幅汇总；后端专属规则错误从 `detail.message` 解析材料状态序号做同样定位。

三条线互不依赖，可并行实施，但共同触及 `UploadTaskEditor.tsx` 与 `rag.py` 的部分需串行。

## 技术上下文

- **语言与版本**：Python 3.12.13（后端）、TypeScript + React 18（前端）、Go 1.x（`goserver/`，本 Feature 不涉及）
- **主要依赖**：FastAPI 0.140.0、SQLAlchemy 2.0.51（asyncmy 驱动）、MUI、react-router-dom v6
- **数据存储**：MySQL 8.4（`paper_chunks.section_name`/`heading` 均为 `varchar(500)`，本 Feature 不改列宽）；Redis（草稿与任务状态）
- **测试体系**：后端 pytest（`backend/tests/`，`test_upload_jobs.py` 已有 chunker 测试）；前端 vitest + Testing Library（`tests/01_decentralized_uploading/`，命令 `cd frontend && npm run test:upload-ui`）
- **目标平台**：Docker Compose 部署于 `/home/mayuan/work/SC-Wiki-docker`（`dev.yaml`，服务名 `python`/`frontend`）
- **性能目标**：分段阈值判定为 O(n) 字符串长度比较，不引入额外解析开销；不新增 LLM 调用
- **约束**：不改数据库 schema；不回溯改写已入库 `paper_chunks`；错误响应体不含堆栈、SQL、内部路径；提交成功路径与既有 409 分支行为不变
- **规模范围**：后端 3 个文件、前端 1 个组件；实测受影响解析产物为全部 28 个 `##` 标题中的 6 个（21%）

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| Overview 失败语义 | 上传、抽取、LLM 和数据库错误必须返回或记录明确原因，前端不得显示假成功 | US2 全局异常处理器返回结构化 `{code, message}`；异常原文入日志 | 通过 |
| Overview 失败语义 | 保存/提交失败横幅展示后端 `detail.message` 及错误码，无结构化 detail 时才回退通用文案 | 沿用既有 `backendErrorReason`，不改协议；US2 让 500 也具备 detail | 通过 |
| AGENTS.md KISS | 拒绝不必要的复杂性 | 长度阈值替代模型判定；卡片展开复用既有 `collapsedStates` | 通过 |
| AGENTS.md YAGNI | 仅实现当前明确所需 | 不做精确标题语义识别；不统一前后端规则集；不改列宽 | 通过 |
| AGENTS.md DRY | 统一相似功能实现 | 异常处理放应用级横切而非逐路由 `try`；错误清单单一数据源驱动三项反馈 | 通过 |
| AGENTS.md SRP | 拆分过大职责 | D1 保正确性（文字不丢）与 D2 保可用性（提交不炸）职责分离 | 通过 |
| AGENTS.md 注释语言 | 与现有代码库注释语言一致 | 新增注释使用简体中文（`chunker.py`、`rag.py`、`UploadTaskEditor.tsx` 现均为中文） | 通过 |
| Spec 假设 | 不回溯已入库数据 | 分段变更只作用于新解析；不在读取路径加旧数据分支 | 通过 |
| Skill Bug 分类 | 修复前先分类 | 分类为「原设计缺陷」：标题识别信任解析结果且标题行不入正文，是分段设计本身的缺陷，非部署或数据问题 | 通过 |
| Skill 测试证据 | 回归测试必须复现实际故障边界 | 分段用真实 Markdown 片段断言探针入 `content`；异常处理器经真实路由验证；校验定位在真实 DOM 断言 | 通过 |

## Feature 文档结构

```text
docs/specs/58-submit-failure-diagnostics/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/
│   └── error-response.md
├── tasks.md
└── checklists/
    └── requirements.md
```

不创建 `data-model.md`：本 Feature 不新增或修改持久实体、字段与状态机。Spec 的两个关键实体（校验错误项、章节判定结果）均为进程内瞬态数据，其结构记录在 `contracts/error-response.md` 与 research D5 中。

## 源代码结构

```text
backend/
├── ingest/chunker.py                  # 修改：_split_by_h2 长度阈值判定（US1）
├── api/rag.py                         # 修改：PaperChunk 写入前截断（US1）
├── main.py                            # 修改：注册全局异常处理器（US2）
└── tests/
    ├── test_upload_jobs.py            # 修改：新增分段判定与截断用例（US1）
    └── test_submit_error_contract.py  # 新增：异常响应契约集成测试（US2）

frontend/src/components/
└── UploadTaskEditor.tsx               # 修改：validate 返回清单 + 定位反馈（US3）

tests/01_decentralized_uploading/
└── submit-validation-feedback.test.tsx  # 新增：校验定位组件测试（US3）
```

**结构选择**：

- 分段判定放 `chunker.py` 而非调用方：章节边界识别是 `_split_by_h2` 的固有职责，调用方 `rag.py:1091` 只消费结果。
- 截断放 `rag.py` 写入点而非 `chunker.py`：截断是存储约束的适配，属于持久化层关注点；`chunker.py` 不应知道数据库列宽。这也是 D1 与 D2 职责分离的落点。
- 异常处理器放 `main.py`：应用级横切关注点，逐路由包 `try` 会重复且必然漏。
- 前端全部改动集中在 `UploadTaskEditor.tsx`：`validate` 与提交流程、折叠状态、字段渲染都在该组件内，跨文件拆分会为传递错误清单引入无价值的 props 层级。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001 / US1 | `chunker.py` `_split_by_h2` 长度阈值判定 | `test_upload_jobs.py` 单元用例；quickstart 场景 1 |
| FR-002 / US1 | 超长行文本并入前一节 `body` | `test_upload_jobs.py` 探针断言文字进入 `content`；quickstart 场景 2 |
| FR-003 / US1 | `rag.py` `PaperChunk` 写入前按 500 截断 | `test_upload_jobs.py` 截断用例；quickstart 场景 1 |
| FR-004 / US2 | `main.py` 全局异常处理器 | `test_submit_error_contract.py` 断言响应体结构 |
| FR-005 / US2 | 异常原文只入日志，响应体用固定文案 | `test_submit_error_contract.py` 断言不含 SQL/堆栈/路径 |
| FR-006 / US2 | 沿用 `backendErrorReason` + `failureMessage` | 既有 2 个用例回归 + quickstart 场景 3 |
| FR-007 / US3 | `validate()` 返回 `ValidationIssue[]` | `submit-validation-feedback.test.tsx` 多错误汇总用例 |
| FR-008 / US3 | `setCollapsedStates` 展开 + `scrollIntoView`/`focus` | 组件测试断言卡片展开与焦点；quickstart 场景 4 |
| FR-009 / US3 | 字段 `error`/`helperText` + 横幅汇总 | 组件测试断言错误态与横幅内容 |
| FR-010 / US3 | 从 `detail.message` 解析材料状态序号 | 组件测试模拟后端 400 响应并断言定位 |
| FR-011 / US3 | 提交成功清除错误态与横幅 | 组件测试断言清除；quickstart 场景 5 |
| SC-001 | 端到端提交成功 | quickstart 场景 1（人工，需重建镜像） |
| SC-002 | 探针检索命中 | `test_upload_jobs.py` 三探针断言 |
| SC-003 | 真实标题分段无回归 | `test_upload_jobs.py` 既有用例 + 新增短标题用例 |
| SC-006 | 既有测试全通过 | 后端 pytest 全量 + 前端 `npm run test:upload-ui` |

## 阶段与依赖

1. **阶段 1 准备**：无需项目级准备工作（依赖、配置、目录均已就绪）。
2. **阶段 2 基础能力**：无跨故事阻断依赖。三个用户故事触及不同文件，可并行。
3. **阶段 3 US1 分段鲁棒性**：`chunker.py` → `rag.py` 截断 → 后端测试。解除硬阻塞，MVP。
4. **阶段 4 US2 异常可诊断**：`main.py` 处理器 → 契约测试。
5. **阶段 5 US3 校验可定位**：`validate` 重构 → 定位反馈 → 前端测试。
6. **阶段 6 完善**：全量回归、镜像重建、quickstart 人工验收、Overview 回写。

US1 与 US2 均触及后端但文件不同（`chunker.py`/`rag.py` vs `main.py`），可并行。US3 完全在前端，与前两者并行。阶段 6 依赖全部故事完成。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|------------|------------|--------------------------|
| 两道防线（阈值判定 + 写入截断）而非单一措施 | 职责不同：阈值判定保证文字不丢（正确性），截断保证任何解析噪声都不触发 `DataError`（可用性）。任一单独实施都留有缺口 | 只截断——丢失最长 1389 字符的真实正文，用户已否决；只判定——阈值以下的异常长标题仍会 500，故障模式不变 |
| 从 `detail.message` 文案解析材料状态序号 | 在不改动后端 12 个 `_upload_error` 调用点的前提下满足 FR-010，控制本 Feature 回归面 | 后端 `detail` 增加 `state_index` 字段——更健壮但需改 12 处调用点并同步前端，超出「让失败可诊断」的最小范围。已在 research D6 记录该耦合的脆弱性与缓解措施（专门单元测试），并说明后续统一升级路径 |
