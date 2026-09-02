# 数据模型：论文引用与图谱里程碑

**GitHub Issue**：[ #81](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/81)

## 关系

```text
papers (id, content_revision)
  1 --- 1 paper_reference_extractions
  1 --- * paper_references --- 0..1 papers (cited_paper_id)
  1 --- * paper_graph_marks
```

`paper_references` 的源端绑定引用论文的当前内容版本；目标端只绑定被引论文身份 `papers.id`。引用的是一篇发表物，不是被引论文的某个 SC-Wiki 内容版本。

`papers.year` 是必填的论文出版年份。引用文献来自外部论文，`paper_references.year` 可以为空；这两个字段的可空性不能混用。

## `paper_reference_extractions`

| 字段 | 类型 | 规则 | 含义 |
| --- | --- | --- | --- |
| `paper_id` | INTEGER | 复合主键、外键 | 引用论文 |
| `paper_revision` | INTEGER | 复合主键、外键 | 解析时的论文版本 |
| `status` | VARCHAR(20) | `succeeded/partial/failed/unavailable` | GROBID 结果 |
| `parser_name` | VARCHAR(32) | 非空，默认 `grobid` | 解析器来源 |
| `parser_version` | VARCHAR(64) | 可空 | 服务报告的版本 |
| `error_message` | TEXT | 可空 | 失败或降级原因 |
| `processed_at` | DATETIME | 非空 | 最近处理时间 |

一篇版本只有一个状态行；重新解析整体替换参考文献并更新该行。

## `paper_references`

| 字段 | 类型 | 规则 | 含义 |
| --- | --- | --- | --- |
| `id` | BIGINT | 主键 | 参考文献记录 |
| `paper_id`、`paper_revision` | INTEGER | 复合外键 | 引用论文及版本 |
| `reference_index` | INTEGER | 非负、同版本唯一 | 文末顺序 |
| `raw_citation` | LONGTEXT | 非空 | 原始引文 |
| `doi` | VARCHAR(255) | 可空、索引 | 规范 DOI |
| `title` | TEXT | 可空 | 解析题名 |
| `normalized_title` | VARCHAR(512) | 可空、索引 | Unicode 小写、去标点、归一空白后的题名 |
| `authors` | JSON | 可空 | 解析作者数组 |
| `year` | INTEGER | 可空、索引 | 解析年份 |
| `cited_paper_id` | INTEGER | 可空、外键 RESTRICT、索引 | 已匹配的 SC-Wiki 目标 |
| `match_status` | VARCHAR(20) | `matched/unmatched/ambiguous` | 关联状态 |
| `match_method` | VARCHAR(20) | `doi/title_year/manual` 或空 | 关联依据 |
| `match_checked_at` | DATETIME | 可空 | 最近匹配检查时间 |
| `created_at`、`updated_at` | DATETIME | 非空 | 审计时间 |

约束与索引：

- 唯一键 `(paper_id, paper_revision, reference_index)`。
- `(paper_id, paper_revision)` 引用 `papers(id, content_revision)`，随当前版本级联更新；当前版本替换时在删除 File/Chunk 前显式删除引用记录。
- `cited_paper_id` 引用 `papers.id`，`ON DELETE RESTRICT`。删除引用论文时先删其源记录；删除被引用论文时拒绝，避免无审计地丢失图边。
- 匹配 `matched` 时必须有 `cited_paper_id` 和 `match_method`；其余状态必须为空目标和方法。

## `paper_graph_marks`

| 字段 | 类型 | 规则 | 含义 |
| --- | --- | --- | --- |
| `paper_id` | INTEGER | 复合主键、外键 RESTRICT | 被标记论文 |
| `mark_type` | VARCHAR(20) | 复合主键：`origin/breakthrough` | 人工里程碑类型 |
| `created_by_user_id` | INTEGER | 外键 RESTRICT | 操作者 |
| `created_at`、`updated_at` | DATETIME | 非空 | 审计时间 |

一个 Paper 可以同时有 `origin` 和 `breakthrough`。标记不绑定某个 Material family，也不影响引用计数、分类或可见性。

## 图投影与计数

公开引用边满足：

```text
reference.paper_id = citing.id
reference.paper_revision = citing.content_revision
reference.cited_paper_id = cited.id
citing.review_status = cited.review_status = 'approved'
citing.approved_revision = citing.content_revision
cited.approved_revision = cited.content_revision
```

节点的 `citation_count` 是满足上述条件的 `COUNT(DISTINCT reference.paper_id)`。同一论文的多个原始引文命中同一被引 Paper 时只形成一条展示边、只计一次。

分类过滤：

- Material family：`EXISTS paper_material_families` 且 `paper_revision = papers.content_revision`。
- Superconductor type：直接比较 `papers.superconductor_kind`；`unknown` 只能在无此筛选或标题搜索中返回。

## 生命周期

1. 上传 Worker 调用 GROBID，把解析结果放入草稿；失败时保存 extraction 状态，不中断人工校对。
2. 提交时 Python 保存当前版本 extraction 和 reference 记录，并尝试匹配已审核 Paper。
3. 审核批准后重新匹配该论文的出边，并扫描可匹配到该论文的历史未匹配参考文献。
4. 论文升版时先读取旧版本主 PDF并重新解析；版本号级联后删除新版本中级联来的旧引用，再保存新 extraction/reference。解析失败也只保存失败状态，旧版本参考文献不参与公开图。
5. 公共图查询只从当前已审核版本投影，Neo4j 不拥有独立事实。
