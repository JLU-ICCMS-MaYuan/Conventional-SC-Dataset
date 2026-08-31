# Feature 规格：统一「研究驱动力」字段

**GitHub Issue**：[#66](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/66)

**创建日期**：2026-08-31

**状态**：草稿

## 背景与目标

同一份数据在三个界面有三个叫法，而数据库只有 `papers.rationale` 一列：

| 位置 | 界面标签 | 实际字段 |
| --- | --- | --- |
| `frontend/src/pages/AdminPage.tsx:1060` 管理员/超管编辑页 | 研究理由 (rationale) | `rationale` |
| `frontend/src/components/PaperEditView.tsx:378` 论文详情只读页 | 分类理由 | `editRationale`（即 `rationale`） |
| `frontend/src/components/UploadTaskEditor.tsx:965` 上传校对草稿页 | 分类理由 | `draft.classification_reason` |

`classification_reason` 没有独立数据库列，仅是草稿层字段名，最终写入 `rationale`
（`backend/api/rag.py:1046`）；`backend/ingest/upload_jobs.py:1098、1141` 中两个名字互相兜底。

### 与 Issue #59 的关系（重要）

[Issue #59](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/59) 曾做过一次**方向相反**的
统一：把详情页的「研究理由」纠正为「分类理由」。当时的判断是正确的——该字段确实装的是
AI 分类判据（`SUMMARY_SYSTEM_PROMPT` 返回结构中的 `rationale`）。`AdminPage.tsx` 那处
「研究理由」是 #59 漏改的残留，这才是用户看到不一致的直接原因。

**本 Feature 不是推翻 #59，而是变更该字段承载的内容**：从「AI 为何这样分类」改为
「作者为何开展这项研究」。这是两件不同的事，分类判据整体退役。

### 现有实现的一处缺陷

`SUMMARY_SYSTEM_PROMPT`（`upload_jobs.py:92-126`）的返回结构里有 `rationale`，但提示词
正文**完全没有描述它该写什么**。这解释了实际产出为何是背景陈述而非分类判据——模型在
没有指引的情况下自行发挥。新字段必须有明确的内容要求。

## 用户场景与验收

### 用户故事 1：上传者在校对页填写研究驱动力（P1）

上传者提交 PDF 后进入校对页，看到 AI 提取的「研究驱动力」——分条列出作者开展这项研究的
动因，可直接修改或补充后提交审核。

**独立验收**：校对页显示「研究驱动力」且可编辑，不再出现「分类理由」。

**验收场景**：

1. **假如** 上传者完成解析进入校对页，**当** 查看论文字段区，**那么** 显示标签
   「研究驱动力」，内容为 AI 依据 PDF 引言生成的分条文本，且输入框可编辑。
2. **假如** 上传者修改研究驱动力后提交审核，**当** 提交成功，**那么** 修改后的内容
   落库到 `research_motivation`。
3. **假如** 上传者查看校对页，**那么** 界面上不存在「分类理由」标签。

### 用户故事 2：管理员与读者看到一致的字段名（P1）

管理员在编辑页、任何人在论文详情页看到的都是「研究驱动力」，三处名称统一。

**独立验收**：三个界面标签一致，全仓库无论文侧 `rationale` / `classification_reason` 残留。

**验收场景**：

1. **假如** 管理员打开论文编辑页，**那么** 该字段标签为「研究驱动力」，可编辑并保存。
2. **假如** 任何人打开论文详情页，**那么** 该字段标签为「研究驱动力」，只读展示，
   多行内容保持 `pre-wrap` 换行（沿用 Issue #65 的渲染约定）。
3. **假如** 在全仓库检索论文侧的 `rationale` 与 `classification_reason` 标识符，
   **那么** 均已清除（`backend/rag/inspiration/` 下的同名字段除外）。

### 用户故事 3：AI 生成符合要求的研究驱动力（P1）

**独立验收**：新上传论文的 `research_motivation` 满足字数、分条与来源要求。

**验收场景**：

1. **假如** 上传一篇含引言的 PDF，**当** 解析完成，**那么** `research_motivation`
   内容 ≤500 字、按 `1. 2. 3.` 分条、依据 PDF 引言与背景陈述而非凭空生成。
2. **假如** 论文没有可识别的引言或背景段落，**当** 解析完成，**那么** 该字段为空或
   如实反映信息不足，不编造内容。

### 边界与异常场景

- **存量数据**：`rationale` 当前仅 1 行有内容（id=9）。**2026-08-31 修正**：删列前复核
  发现该内容已是分条式研究动因（443 字，判定低温电阻三种对立理论、选汞的纯度理由），
  符合新字段契约，故**改为迁移保留**。初稿判定「不迁移」依据的是更早的旧内容
  （「背景：1908 年昂内斯实现氦气液化…」），用户重新解析后该依据已不成立
- **审核快照**：`classification_context` 中的 `classification_reason` 键一并移除
  （`AdminPage.tsx:302-303`）；`paper_review_events` 已有历史快照不动（不可变记录）
- **字段可编辑性**：与 `summary`、`key_finding` 等 AI 提取字段一致，用户与管理员均可
  修改，用于兜底 LLM 的幻觉或遗漏
- **Neo4j 同步**：`PAPER_FIELDS` 与 SELECT 语句需同步替换，否则同步脚本查不存在的列会报错
- **Go 白名单 PATCH**：接受 `research_motivation`，不再接受 `rationale`
- **不影响灵感探索模块**：`backend/rag/inspiration/` 下的 `rationale` 是「思考模式选择
  原因」，与论文字段同名但完全无关

## 需求

### 功能需求

- **FR-001**：数据库必须新增 `papers.research_motivation` 列（Text，可空），并删除
  `papers.rationale` 列。

- **FR-002**：三个界面（上传校对页、论文详情页、管理员/超管编辑页）必须统一显示
  标签「研究驱动力」，不得出现「分类理由」或「研究理由」。

- **FR-003**：草稿层必须退役 `classification_reason` 字段名，统一使用
  `research_motivation`，不再保留两个名字互相兜底的逻辑。

- **FR-004**：AI 提示词必须明确描述 `research_motivation` 的内容要求：阐述作者开展该
  研究的动因，依据 PDF 引言与背景段落，≤500 字，按 `1. 2. 3.` 分条。

- **FR-005**：`research_motivation` 必须允许上传者在校对页、管理员在编辑页修改。

- **FR-006**：Neo4j 同步（`sync_neo4j.py` 的 `PAPER_FIELDS` 与 SELECT）必须同步替换
  字段名，同步脚本可正常执行。

- **FR-007**：Go 白名单 PATCH（`papers.go:159`）、论文详情响应（`papers.go:488`）、
  管理员可更新字段（`admin.go:37`）与 GORM 模型（`models.go:116`）必须同步替换。

- **FR-008**：审核请求的 `classification_context` 不再包含 `classification_reason` 键。

- **FR-009**：论文详情页的 `research_motivation` 必须保持 `pre-wrap` 渲染，使分条内容
  不被折叠成一段（沿用 Issue #65 约定）。

### 关键实体

**论文（Paper）**：
- `research_motivation`（新增，Text 可空）：作者开展该研究的动因，分条文本
- `rationale`（删除）：原 AI 分类判据

## 成功标准

- **SC-001**：迁移执行后，`papers` 表存在 `research_motivation` 列、不存在 `rationale` 列。
- **SC-002**：三个界面均显示「研究驱动力」；全界面检索无「分类理由」「研究理由」。
- **SC-003**：全仓库检索论文侧 `rationale` 与 `classification_reason` 标识符均已清除
  （`rag/inspiration/` 下同名字段除外）。
- **SC-004**：新上传论文的 `research_motivation` ≤500 字且含 `1.` `2.` 分条标记。
- **SC-005**：Neo4j 同步脚本对任一论文执行成功，不报缺列错误。
- **SC-006**：Go PATCH 接受 `research_motivation` 字段；提交 `rationale` 被拒绝。
- **SC-007**：审核请求体的 `classification_context` 不含 `classification_reason` 键。
- **SC-008**：`go build ./...`、`go test ./...`、`tsc -b --force`、`vitest run` 全通过。

## 假设与依赖

- 上传解析主链路的字段提示词位于 `backend/ingest/upload_jobs.py` 的
  `SUMMARY_SYSTEM_PROMPT`；`backend/ingest/enrich_papers.py` 是离线富化脚本，需一并更新
  以免两处字段名不一致
- 现有 LLM 调用能力足以按引言生成分条文本，无需联网（联网增强见 Issue #67）
- `paper_review_events.classification_snapshot` 为不可变历史记录，不回溯修改

## 范围外事项

- **联网检索增强**：见 [Issue #67](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/67)，
  本 Feature 只用 PDF 引言背景生成
- 不改动 `backend/rag/inspiration/` 下的 `rationale`（灵感探索模块的思考模式选择原因）
- 不回溯修改 `paper_review_events` 已有快照内容
- ~~不迁移 `rationale` 存量数据~~ —— 已改为迁移，见「边界与异常场景」的存量数据条目
- 不为其他字段调整语义或标签

## 澄清记录

### 2026-08-31

- 问：`rationale` 列如何处置？ → 答：**方案 B**——新增 `research_motivation` 列并删除
  `rationale`。用户明确不希望研究驱动力写在名为 `rationale` 的列里。
- 问：存量数据是否迁移？ → 答：初稿定为不迁移（依据旧内容为背景陈述）；执行迁移前
  复核发现 id=9 内容已符合新语义，**改为迁移保留**。教训：涉及不可逆删除时，
  规划期的数据快照可能已过期，执行前必须重新核查。
- 问：审核快照中的 `classification_reason` 如何处置？ → 答：**方案 A**——一并移除。
  分类判据整体退役，快照保留该键必然为空；追溯主体（材料状态分类、scope 证据）不受影响。
- 问：新字段是否仍允许用户在校对页编辑？ → 答：**允许**，与 `summary`、`key_finding`
  等 AI 提取字段一致。项目内没有「AI 生成且用户不可改」的先例，且需要人工兜底 LLM 幻觉。
- 问：联网检索是否包含在本 Feature？ → 答：不包含，拆分至 Issue #67。
