# 20题 development pilot 标注手册

## 目的与限制

本轮只检查题目清晰度、工具可运行性、临时数据一致性和评测流程。原始 PDF 未到位，所有现有数据库证据必须标记 `pdf_verified=false`，不得称为正式 gold。

## 双人独立标注

1. 标注者 A、B 使用相同冻结数据快照，独立判断题目类型、可回答性、规范化答案、必需条件和临时证据。
2. 初次标注期间不得查看对方答案。
3. AI可用于搜索候选记录，不得替代第二位人工标注者。
4. 每个判断保留标注者、时间、schema版本和备注。

## 各题型规则

- **数值事实**：记录 `value_min/value_max/unit`，以及压力、温度、样品态等必需条件；范围不得压成单一最大值。
- **机制解释**：拆成必须覆盖的原子 claim 和禁止出现的无证据 claim。
- **文献元数据**：比较 DOI、标题、年份、作者等类型化字段，不用模糊语义代替精确字段。
- **图谱单跳/多跳**：记录节点 ID、关系类型、source/target 和 `directed/symmetric`；任一有向边反转均算方向错误。
- **混合题**：分别记录 Qdrant、MySQL、Neo4j 所需证据，不能只凭最终文本判断。
- **不可回答题**：标记原因 `missing_evidence`、`conflicting_conditions`、`ambiguous_entity` 或 `unsupported_property`。

## 临时gold生成

- Qdrant：保存 `(paper_id, chunk_index)` 与 snapshot ID。
- MySQL：保存记录主键、数值范围、单位和完整条件。
- Neo4j：保存节点与边的稳定业务键、关系方向和路径。
- 不得把临时gold复制到 formal split；PDF到位后必须逐条回查并重新裁决。

## 一致性指标

- 可回答性与离散标签：Cohen's kappa。
- 等级评分：加权 kappa 或 ICC。
- evidence集合：F1与Jaccard。
- 标准化数值：含单位和条件的精确匹配。
- 任一关键维度低于0.80，修订手册并重新标注20题。

## 裁决规则

1. 系统先生成逐字段差异，不自动覆盖任一标注。
2. A、B仅讨论差异字段并引用现有快照证据。
3. 能由冻结数据确定的分歧形成 `adjudicated` 版本，同时保留A、B原记录。
4. 依赖PDF才能解决的分歧标记 `deferred_pdf`，不得强行裁决。
5. 若发现数据库明显污染，题目状态改为 `blocked_data_quality`，不静默删除。
6. PDF到位后，所有 `deferred_pdf` 和临时证据重新独立回查；旧development记录保持不可变。
