# 数据模型：Mentor RAG 评测

## Experiment

唯一键 `experiment_id`。字段包括状态（development/provisional/formal）、Git commit、配置哈希、数据快照 ID、环境指纹、开始/结束时间、价格表版本和 schema 版本。创建后不可覆盖。

## Question

唯一键 `question_id`；字段包括 split、题型、问题文本、可回答性、必需工具能力、accepted answers、类型化容差规则和 gold evidence 集合。pilot 与 formal 的 question_id 不得重复。

## GoldEvidence

字段包括 `evidence_id`、source/paper ID、DOI、PDF SHA-256、物理页、印刷页、locator 类型和值、原始文本、规范化文本 SHA-256、claim 类型、标注者和裁决状态。正式状态要求全部必填。

## DataSnapshot

记录 Qdrant collection 与 point manifest、embedding 配置、MySQL schema/行数/导出哈希、Neo4j schema/节点边计数/导出哈希、PDF manifest 和冻结时间。

## RunRecord

复合唯一键 `(experiment_id, question_id, ablation_group, repetition)`；保存请求、答案、引用、工具轨迹、SSE事件、首次与重试状态、usage、成本、TTFT、总延迟和结构化错误。

## EvaluationResult

关联 RunRecord；包含 evaluator 类型与版本、盲化输入哈希、正确性、忠实度、引用 precision/recall、拒答分类、逐 claim 判定和解释。LLM judge 不得知道消融组名。

## 生命周期

`draft dataset → independently_annotated → adjudicated → frozen`；`development experiment → provisional → formal`。只有 PDF Gate、标注门、数据快照门、工具隔离门和统计协议门全部通过，才能创建 formal Experiment。
