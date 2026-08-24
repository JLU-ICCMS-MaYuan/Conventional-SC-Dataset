# 数据模型：论文分类证据作用域与汇总前状态

## 临时分段结果

临时分段结果仍保存在任务的分段 JSON 中，不进入 MySQL。新结果携带契约版本，用于判断缓存
是否具备证据作用域能力。

### 分类证据条目

| 字段 | 类型 | 约束 | 含义 |
|------|------|------|------|
| `candidate` / `value` | string | 按原字段要求非空 | 论文类型候选或自由材料类型候选 |
| `scope` | enum | `current_paper` 或 `referenced_work` | 证据描述本文还是引用工作 |
| `page` | integer/null | 正整数或空 | PDF 页码 |
| `quote` | string | 可逐字核对 | 原文证据 |

`paper_type_evidence.candidate` 仍只允许
`theoretical|experimental|review|unknown`。`sc_type_candidates.value` 不使用固定枚举。

### 作用域规则

- `current_paper`：本文作者实际提出、计算、合成、测量、分析或总结的工作。
- `referenced_work`：前人研究、引用论文、历史发现、对领域现状的回顾。
- 同一分段同时含两者时必须拆成独立证据项。
- 作用域缺失或非法的旧条目不能参与本文分类。

## 解析预览字段

`PreviewField.state`：

- `waiting`：尚无该字段候选。
- `filled`：非分类字段已有一致候选。
- `conflict`：非分类单值字段存在真实不一致。
- `pending_summary`：分类字段已有或正在等待分段候选，但全文尚未形成最终建议。

状态转换：

```text
extracting → waiting
reading/summarizing + 分类字段 → pending_summary
reading/summarizing + 非分类字段 → waiting|filled|conflict
ready → 使用可编辑最终草稿，不再以临时预览作为最终分类
failed/cancelled → 保留最后可读候选和任务终态，不伪造 ready
```

## 缓存兼容生命周期

1. 新分段结果写入当前契约版本和带作用域证据。
2. Worker 恢复任务时，只复用当前契约版本的缓存。
3. 旧版本或无版本缓存由 Worker 定向重读并原子覆盖。
4. 在重读发生前，公开预览可以读取旧结构，但作用域缺失分类项不得进入本文候选。
5. 上传临时数据最长保留 24 小时；旧契约兼容随这些任务自然退出，不进入永久数据库模型。

## 不变的数据边界

- `Paper.paper_type`、`Paper.theoretical_subtype` 和正式审核状态不变。
- `KeyProperty.article_type=e|t` 与论文整体分类继续独立。
- `sc_type` 和物性 `superconductor_type` 继续接受人工确认后的自由文本。
