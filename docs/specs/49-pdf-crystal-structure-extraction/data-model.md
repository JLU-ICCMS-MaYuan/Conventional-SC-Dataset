# 数据模型：论文附件晶体结构提取

**GitHub Issue**：[#49](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/49)

## 设计原则

结构候选是上传草稿阶段的临时聚合；正式结构沿用 #32 的 `StructureModel`，不新增结构级审核
状态。原始输入、直接报告字段和派生表示分别保存，避免把推导内容误标为论文原文。

## 草稿实体

### `structure_candidates[]`

| 字段 | 类型 | 必填 | 约束 |
|---|---|---:|---|
| `candidate_id` | string | 是 | 当前上传任务内稳定唯一 |
| `material_state_ref` | string | 是 | 指向 `material_states[]` 项 |
| `source_kind` | enum | 是 | `attachment`, `pdf_reported`, `pdf_derived`, `merged` |
| `status` | enum | 是 | `needs_review`, `valid`, `confirmed`, `excluded`, `blocked` |
| `confirmation` | enum | 是 | `unreviewed`, `confirmed`, `excluded` |
| `original_format` | enum/null | 否 | `cif`, `poscar`；PDF 候选为空 |
| `original_text` | string/null | 否 | 原始结构文本，不可被派生输出覆盖 |
| `reported_structure` | object | 否 | 原文直接报告的晶格、坐标、空间群和占位 |
| `derivation` | object/null | 否 | 展开或标准化方法、输入位点、推导摘要 |
| `validation` | object | 是 | ASE 解析状态、错误、元素、原子数、晶胞、体积和哈希 |
| `representations` | object | 否 | `primitive`、`conventional` 两个派生结构引用 |
| `sources[]` | object | 是 | 文件、角色、页码、章节/表格、quote、evidence_ref |
| `conflicts[]` | object | 是 | 条件或几何冲突说明 |
| `user_note` | string/null | 否 | 用户修正说明，不替代原文证据 |

### `structure_candidates[].representations`

每个表示包含 `cell_kind`（`primitive` 或 `conventional`）、`format`（`cif` 或 `poscar`）、
`text`、`derived_from_candidate_id`、`standardization_method` 和 `validation`。表示是可重新
生成的派生内容，不能作为新的独立论文来源。

## 正式实体

正式提交使用 #32 的：

- `material_states`：保存材料、压力、物相和论文报告空间群；没有完整几何时仍可存在。
- `structure_models`：保存完整 `structure_format`、`structure_text`、哈希、生成方法、核处理和
  可选父结构；必须绑定同一 `paper_id + paper_revision + material_state_id`。
- `paper_evidence`：保存来源文件、页码、章节/表格定位和原文证据。
- `structure_model_evidences`：连接结构模型与同 revision Evidence，禁止跨论文或跨 revision。

## 状态转换

```text
discovered -> needs_review -> valid -> confirmed -> persisted
                    |             |
                    v             v
                 blocked       excluded
```

- `discovered`：来源识别出可能的结构字段。
- `needs_review`：字段缺失、冲突或需要用户核对。
- `valid`：结构完整且 ASE 校验通过，但尚未确认。
- `confirmed`：用户明确接受该候选。
- `blocked`：不能安全生成结构。
- `excluded`：用户明确排除，不进入正式提交。
- `persisted`：随论文当前 revision 成功写入正式实体。

## 等价与合并

候选只允许在同一材料状态条件内比较。比较前生成 primitive/conventional 派生表示，并按元素、
晶胞长度/角度和周期性原子位置执行固定容差比较。等价时合并来源集合，不等价时保留多个候选
并写入 `conflicts[]`；禁止跨论文自动合并。
