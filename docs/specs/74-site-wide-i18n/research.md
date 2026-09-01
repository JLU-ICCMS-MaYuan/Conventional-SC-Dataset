# 技术研究：全站中英文界面切换，数据层统一英文

**GitHub Issue**：[#74](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/74)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)

本文件只记录本 Feature 内的技术决策，不复制项目级稳定事实。

## R1：i18n 方案选自研轻量上下文，不引入 react-i18next

**决策**：新增 `frontend/src/context/LanguageContext.tsx`，提供 `lang`、`setLang`、`t(key, vars?)`；文案字典为普通 TypeScript 模块，按功能域分文件静态导入。

**理由**：

- 只需两种语言，无复数规则（英文 plural rules）、无性别变格、无按语言懒加载远程资源的需求。react-i18next 的核心价值集中在这些场景。
- 现有依赖控制克制：`frontend/package.json` 的 dependencies 仅 18 项，且已有 `chartPreferences.ts` 这类自研 localStorage 偏好模块作为同类先例。
- 字典静态导入可被 TypeScript 校验键名，缺键在编译期暴露；`i18next` 的运行时 key 查找只会静默回退。
- 现有 `AuthProvider` 已建立 Context + localStorage 的组织方式（`frontend/src/context/AuthContext.tsx`），`LanguageProvider` 与之同构，维护者无需学习新范式。

**备选方案**：

- **react-i18next**：功能完备但引入 `i18next` + `react-i18next` 两个运行时依赖与一套配置体系，为两种语言付出的复杂度不成比例。已拒绝。
- **MUI 自带 localization**：只覆盖 MUI 组件内置文案（分页、DataGrid 等），不解决业务文案。作为补充手段保留，不作为主方案。

**证据**：`frontend/package.json` 无 i18n 依赖；`frontend/src/context/AuthContext.tsx:46-58` 的 localStorage 读写模式；`frontend/src/lib/chartPreferences.ts` 的自研偏好持久化先例。

## R2：固定枚举标签放在前端字典，不改后端枚举契约

**决策**：材料维度、晶系、Tc 方法、论文类型、审核状态、用户角色、超导类型七类枚举的显示标签由前端按 `value` 查双语字典；后端返回的枚举值与现有契约完全不变。

**理由**：

- 这些枚举值稳定且已由后端约束校验（如 `MATERIAL_DIMENSIONALITIES`、`CRYSTAL_SYSTEMS`、`SUPERCONDUCTOR_KINDS`），前端已存在兜底常量 `DEFAULT_MATERIAL_DIMENSIONALITIES`（`frontend/src/lib/classifications.ts:36-44`）与 `TC_METHOD_OPTIONS`、`CRYSTAL_SYSTEM_OPTIONS`（`frontend/src/components/UploadTaskEditor.tsx:56-83`），本已是前端维护标签的形态。
- 若改为后端按 `Accept-Language` 返回本地化标签，则 Go 与 Python 两侧都要各维护一份字典，且 `materialDimensionalities`（`goserver/handlers/classifications.go:19-27`）与 `MATERIAL_DIMENSIONALITIES`（`backend/services/classification_catalog.py:18-26`）已经是重复定义，再加语言维度会放大重复。
- 枚举提交值不变，保证 FR-008 的「切换语言不改变提交值」天然成立，也不影响既有 Go/pytest 契约测试。

**备选方案**：后端返回本地化标签。会新增跨语言字典重复与 `Accept-Language` 协商逻辑，且要改动两个服务的目录接口契约。已拒绝。

**证据**：`frontend/src/lib/classifications.ts:36-44`、`frontend/src/components/UploadTaskEditor.tsx:44-83`、`goserver/handlers/classifications.go:19-27`、`backend/services/classification_catalog.py:18-26`。

## R3：分类目录接口增量返回英文名，保留 `name` 键兼容

**决策**：目录接口在现有 `name` 键之外增加 `name_zh` 与 `name_en`；`name` 继续等于 `name_zh`。前端按当前语言选用，`name_en` 为空时回退 `name_zh`。

**理由**：

- `name` 键被 `ClassificationAutocomplete`、`ChartGroupEditor`、`AdminPage` 审核弹窗、社区图表家族筛选多处消费，直接改语义会波及全部调用点并破坏既有测试。
- 数据库已有 `name_en` 列（`material_families`、`structure_families`），无需迁移，只需在序列化层输出。
- 用户自建家族只写 `name_zh`（`goserver/handlers/classifications.go` 的 `resolveMaterialFamily`），`name_en` 天然为空，回退规则正是 FR-010 要求的行为。

**备选方案**：把 `name` 改为按语言返回的单值。会让后端承担语言协商职责，与 R2 的结论冲突，且破坏兼容。已拒绝。

**证据**：`goserver/models/models.go:218-219`、`240-241` 的 `NameZH`/`NameEN` 列；`goserver/handlers/classifications.go:80-100` 的 `serializeCatalog` 现只输出 `NameZH`；`backend/services/classification_catalog.py:169-174` 的 `serialize` 同样只输出 `name_zh`。

## R4：六个叙述字段统一英文，不做双语存储

**决策**：`SUMMARY_SYSTEM_PROMPT` 与 `extractor.py` 的 prompt 改为以英文产出六个叙述字段。不新增 `*_en` 列，不做双语存储，不做同步状态检测。

**理由**：

- 这些字段的事实来源是英文论文原文：`summary` 浓缩英文摘要，`methodology` 提取 `particle swarm optimization` 这类英文术语，`key_finding` 引用英文正文。先译成中文再存，是在事实来源与存储之间插入一道有损转换。
- 审核质量：审核者对着英文原文核对英文摘要可逐句比对；核对中文摘要则需先在脑中翻译一遍。
- 项目已有同类结论：`docs/specs/59-detail-review-form-parity/research.md` 记录过一次类似核查——当时以为「提交中文、审核英文」是翻译丢失，核实后发现研究方法在库中本就是英文术语列表，问题只是展示形态差异。
- 消除的成本：7 个新列（6 个 `*_en` + 1 个指纹列）、双侧 ORM 同步、Go 写入白名单扩 7 项、同步状态检测机制、管理员并排双栏界面、重新生成端点、幂等回填脚本、`narrative_en_sync` 契约。

**代价**：中文界面下这六个字段仍是英文，中文用户阅读这部分内容有难度。可接受——论文原文本就是英文，读者已处于英文语境；界面的导航、按钮、表单、枚举、分类家族名仍为中文。

**备选方案**：

- **新增 6 个 `*_en` 列 + 指纹快照检测同步 + 并排双栏编辑 + 回填脚本**：本 Spec 早先版本的设计。已在范围修订中拒绝——复杂度与收益不成比例，且译文质量无法长期治理。
- **运行时按需机器翻译 + 缓存表**：首次访问延迟，译文绕过人工审核。已拒绝。

**证据**：`backend/ingest/extractor.py:34,49-50`（「中文总结」「5-10 个中文关键词」）；`backend/ingest/upload_jobs.py` 的 `SUMMARY_SYSTEM_PROMPT`；`docs/specs/59-detail-review-form-parity/research.md`。

## R5：存量中文数据一次性转换，脚本用后即删

**决策**：写一次性脚本把库中已有的中文叙述字段转为英文；转换验证完成后从代码库删除该脚本。

**理由**：

- 不转换则库内长期混有两种语言的同一字段，展示层要写语言判断分支——这正是本次范围修订想消除的复杂度。
- 当前库中只有 1 篇论文（`papers.id = 9`），转换规模极小，无需考虑批量性能、断点续传或并发。
- 脚本是一次性维护工具而非长期能力。留在代码库中会被误认为可反复运行的正式功能；按 FR-017 要求删除。

**附带收益**：`papers.id=9` 的 `knowledge_graph_title` 存在双重编码损坏（UTF-8 字节经 Latin-1 通道写入，实测无法用单一编码完整还原）。该字段按英文重新产出即修复此损坏。

**备选方案**：只管新数据、不转存量。会留下永久的语言混杂状态。已拒绝。

**证据**：实测库中 6 个字段均为中文、论文总数为 1；`papers.id=9` 的 `knowledge_graph_title` 读出为 `'é¦–æ¬¡å\x8f‘çŽ°...'`，`latin-1` 与 `cp1252` 均无法完整还原。

## R6：`knowledge_graph_title` 的写入白名单缺口一并修复

**决策**：把 `knowledge_graph_title` 加入 Go 的 `paperUpdateFields` 与 `PatchPaper` 的 `allowed` map。

**理由**：该字段不在两处白名单内，管理员编辑会被静默丢弃——接口返回 200 但数据未保存，无任何错误信号。这是最难发现的失败模式。因 FR-018 要求管理员能编辑六个叙述字段，而该字段是其中之一，故必须修复。

**性质**：这是 Issue #70 遗留的贯通遗漏，与语言无关，但落在本 Feature 的必经路径上。

**证据**：`goserver/handlers/admin.go:34-39` 的 `paperUpdateFields` 不含该字段；`goserver/handlers/papers.go:155-162` 的 `allowed` map 同样不含。

## R7：语言偏好只存 localStorage，键名与现有偏好一致风格

**决策**：键名 `sc-wiki.language`，取值 `'zh' | 'en'`。读取失败或值非法时回退 `'zh'`。

**理由**：

- 纯展示偏好，不影响权限与数据可见性，无需服务端持久化，避免为此新增 `users` 列与账户接口改动。
- 读写包裹在 try/catch 中：浏览器禁用存储（隐私模式、配额耗尽）时组件状态仍可切换，满足 FR-006 的「保持页面可用」。
- 与 `chartPreferences.ts` 的偏好持久化风格保持一致。

**备选方案**：写入 `users.language_preference` 支持跨设备。已在澄清阶段拒绝，记入 Spec 范围外事项。

**证据**：`frontend/src/lib/chartPreferences.ts` 的既有偏好存储实现。

## R8：测试目录必须登记到 vitest include 白名单

**决策**：本 Feature 的前端测试放入既有已登记目录，若新建目录则必须同步修改 `vitest.config.ts` 的 `include` 数组。

**理由**：`vitest.config.ts` 的 `include` 是逐目录白名单而非 `tests/**` 通配，其注释已明确警告「新增含 .test.tsx 的目录时必须同步加到这里，否则该目录的用例会被静默跳过——不报错、不计数，看不出漏了」。这是本 Feature 最容易产生「测试假通过」的陷阱。

**证据**：`vitest.config.ts:24-33` 的 include 白名单与其注释。

## R9：本 Feature 无数据库改动

**决策**：不新增 Alembic 迁移，不改 ORM 模型字段。

**理由**：范围修订后，数据层统一英文意味着不加任何列——六个叙述字段沿用现有列，只是内容语言从中文变为英文；`news_items` 同样不加列。分类目录的 `name_zh` / `name_en` 列本就存在（`goserver/models/models.go:218-219`、`240-241`），只需在序列化层输出。

**唯一的服务端写入改动**：Go 的两处字段白名单补 `knowledge_graph_title`（R6），这是 map 与数组字面量的改动，不涉及 Schema。

**对比早先设计**：本 Spec 早先版本需要 1 次迁移（`papers` 加 7 列、`news_items` 加 2 列）、双侧 ORM 模型同步、Go 白名单扩 7 项。范围修订后全部消除。

**证据**：`alembic/versions/` 无需新增文件；`goserver/models/models.go:218-219`、`240-241` 的既有 `NameZH` / `NameEN` 列。

## 未决事项

无。范围修订的全部决策已记入 [spec.md](spec.md) 澄清记录。
