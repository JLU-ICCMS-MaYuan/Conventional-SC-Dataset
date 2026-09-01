# 实施计划：全站中英文界面切换，数据层统一英文

**GitHub Issue**：[#74](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/74)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)
## 摘要

在顶栏头像左侧提供中英切换控件，语言偏好存浏览器本地。前端新增自研 `LanguageContext` 与按功能域分文件的双语文案字典，替换 45 个文件约 2400 处硬编码中文串；固定枚举标签与分类家族名按语言取值，后端枚举契约不变。

数据层不做双语：六个 LLM 叙述字段改为直接产出英文，库内存量中文数据用一次性脚本转换后删除该脚本。因此本 Feature **无数据库迁移、无 ORM 模型改动**，服务端只需在分类目录序列化层输出 `name_en`，并补齐 `knowledge_graph_title` 的写入白名单缺口。

## 技术上下文

- **语言与版本**：TypeScript 5.6 / React 19.2 / Go 1.25（`goserver/go.mod`）/ Python 3.12（FastAPI）
- **主要依赖**：MUI 7.3、react-router-dom 6.28、GORM、SQLAlchemy 2.x、OpenAI 兼容 SDK（`backend/rag/llm.py`）
- **数据存储**：MySQL 主业务库；**本 Feature 不改 Schema、不新增迁移**
- **测试体系**：Vitest（`vitest.config.ts`，逐目录白名单）、pytest（`backend/tests`、`tests/`）、`go test ./...`；统一入口 `scripts/run-tests.sh {backend|go|frontend}`
- **目标平台**：Web 浏览器；服务端 Docker Compose（生产）与宿主机进程（本地，Issue #71）
- **性能目标**：语言切换在当前页面即时生效，不触发网络请求或重新登录（SC-002）；解析不增加 LLM 请求次数
- **约束**：不引入新前端运行时依赖（R1）；不改现有接口键语义（contracts）；`docs/` 用简体中文（AGENTS.md）
- **规模范围**：前端 45 个文件约 2400 处文案、13 个页面级模块；服务端改动为 2 处白名单条目、2 处目录序列化、2 处解析 prompt；存量数据 1 篇论文

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| AGENTS.md | 遵循 KISS/YAGNI/DRY/SOLID | 自研轻量 i18n 而非引入完整框架（R1）；数据层统一英文而非双语存储，消除同步检测与译文治理（R4）；不做第三语言与地区格式化预留 | 通过 |
| AGENTS.md | `docs/` 使用简体中文 | 本 Feature 全部文档为简体中文，代码符号保留原文 | 通过 |
| AGENTS.md | 代码注释与现有代码库语言一致 | 新增代码注释使用简体中文 | 通过 |
| AGENTS.md | 不自动创建分支或提交 | 实施阶段只改文件 | 通过 |
| Overview：接口兼容 | 不破坏既有前端消费点 | 目录接口保留 `name` 键；论文接口不增删键（contracts C1、C3） | 通过 |
| Spec FR-006 | 存储失败仍可用 | localStorage 读写 try/catch，回退默认中文（F7） | 通过 |
| Spec FR-014 | 叙述字段不随语言变化 | 单一英文内容，展示层无语言分支 | 通过 |
| Spec FR-017 | 一次性脚本用后删除 | T041 显式删除，T051 收尾核验 | 通过 |
| Spec SC-009 | 既有功能不回归 | 枚举提交值不变、接口向后兼容；三套测试全量执行 | 通过 |
| `vitest.config.ts` 白名单 | 新测试目录须登记否则静默跳过 | 测试落在已登记目录，不新建目录（F9、R8） | 通过 |

无阻断项。

## Feature 文档结构

```text
docs/specs/74-site-wide-i18n/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/
│   ├── bilingual-api.md
│   └── i18n-frontend.md
├── tasks.md
└── checklists/
    └── requirements.md
```

不创建 `data-model.md`：本 Feature 无持久数据结构变更。

## 源代码结构

```text
frontend/src/
├── main.tsx                          # 挂载 LanguageProvider（F1）
├── context/LanguageContext.tsx        # 新增：lang / setLang / t（F1、F2）
├── i18n/                              # 新增：index.ts + zh/ + en/ 各 13 个域文件（F3）
├── lib/classifications.ts             # 增 familyName(term, lang)（F5）
├── components/AppShell.tsx            # 顶栏切换控件（F6）+ 导航文案
├── components/                        # 其余 20 个组件的文案替换
└── pages/                             # 13 个页面的文案替换

backend/
├── ingest/upload_jobs.py              # SUMMARY_SYSTEM_PROMPT 改英文产出
├── ingest/extractor.py                # summary / keywords_tags 改英文产出
├── services/classification_catalog.py # 目录序列化增 name_zh / name_en（C1）
└── scripts/convert_narrative_to_english.py  # 一次性转换脚本，验证后删除（R5）

goserver/
├── handlers/classifications.go        # serializeCatalog 增 name_zh / name_en（C1）
├── handlers/papers.go                 # PatchPaper 白名单补 knowledge_graph_title（C2）
└── handlers/admin.go                  # paperUpdateFields 补 knowledge_graph_title（C2）

tests/
├── 02_identity_governance/            # 语言切换、顶栏控件、管理员编辑（已登记目录）
└── 03_data_search_and_database_discovery/  # 英文界面巡检（已登记目录）
```

**结构选择**：

- i18n 基建独立于业务组件，使 Issue #75、#76 可在其上直接编写双语文案。
- 转换脚本放 `backend/scripts/`，与既有维护脚本一致；按 FR-017 验证后删除。
- 服务端改动极小：无新增端点、无新增模块，只有白名单与序列化层的增量。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001、FR-002 / US1 | `AppShell.tsx` 切换控件（F6） | Vitest：控件存在、`aria-pressed` 随语言变化 |
| FR-003–FR-006 / US1 | `LanguageContext` + localStorage（F1、F7） | Vitest：默认中文、写入后重载保持、存储抛异常时不白屏 |
| FR-007 / US1 | `i18n/{zh,en}/*` 13 个域文件（F3） | Vitest：英文模式下页面无中日韩字符（SC-001） |
| FR-008 / US2 | `i18n/{zh,en}/enums.ts` 按 value 查表（F4、R2） | Vitest：七类枚举标签切换、提交值不变 |
| FR-009、FR-010 / US2 | 目录接口增 `name_en`（C1）+ `familyName()`（F5） | Go 测试：响应含 `name_zh`/`name_en`；Vitest：自建家族回退中文名 |
| FR-011–FR-013 / US3 | 解析 prompt 改英文产出（R4） | pytest：产出为英文、无依据字段为空 |
| FR-014 / US3 | 展示层无语言分支 | Vitest：两种语言下字段内容一致 |
| FR-015、FR-016 / US4 | 一次性转换脚本（R5、C5） | pytest：空字段跳过、单篇失败继续 |
| FR-017 / US4 | T041 删除脚本 | T051 收尾核验代码库无残留（SC-008） |
| FR-018 / US5 | `AdminPage` 单栏编辑 | Vitest：六字段可编辑保存 |
| FR-019 / US5 | Go 两处白名单补字段（C2、R6） | Go 测试：保存后持久生效，不被静默丢弃（SC-007） |
| FR-020 | `NewsManager` 提示文案 | 手工走查 |
| FR-021 | 不改原文字段渲染路径 | Vitest：两种语言下这些字段一致 |
| SC-005 | 转换脚本执行 | 库内六字段无中日韩字符 |
| SC-009 | 向后兼容设计（C1–C4） | `scripts/run-tests.sh` 三套全量通过 |

## 阶段与依赖

1. **基础能力（阻断全部故事）**：`LanguageContext`、`t()`、字典骨架与类型约束、`main.tsx` 挂载、`AppShell` 切换控件。完成后 Issue #75、#76 即可编写双语文案。
2. **P1 故事（US1、US2）**：按流量顺序替换页面文案；枚举字典与 `familyName()`；目录接口双侧增键。交付后英文界面已可完成主要操作。
3. **P2 数据层（US3、US4）**：解析 prompt 改英文产出；存量数据转换后删除脚本。
4. **P2 编辑能力（US5）**：管理员单栏编辑；补齐 `knowledge_graph_title` 白名单缺口。与前一阶段无依赖，可并行。
5. **P3 与收尾**：快讯提示文案；三套测试全量、生产构建、quickstart 走查、Overview 回写。

**关键依赖**：阶段 1 阻断其余全部；US3 阻断 US4（转换目标语言由 prompt 产出定义）；US5 与 US3、US4 无依赖。

**串行触点**：`AppShell.tsx`、`UploadTaskEditor.tsx`、`AdminPage.tsx`、`goserver/handlers/papers.go`、`goserver/handlers/admin.go`、`backend/ingest/upload_jobs.py` —— 详见 [tasks.md](tasks.md) 的串行触点表。

## 复杂度说明

范围修订后本 Feature 无必要复杂度需要额外说明。早先设计中的指纹快照同步检测、服务端下发同步状态、双语回退规则分歧三项复杂度均随「数据层统一英文」而消除。

唯一保留的设计取舍是分类家族名在英文缺失时回退中文（F5），而这是为避免下拉项显示空白导致不可用——该回退不涉及长文本，不影响英文阅读体验。
