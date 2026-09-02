# 数据模型：论文级 Superconductor type 单选分类

**GitHub Issue**：[ #80](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/80)

| 实体 | 字段 | 规则 |
| --- | --- | --- |
| `papers` | `superconductor_kind` | 非空，默认 `unknown`，仅允许 `conventional`、`unconventional`、`unknown` |
| `material_states` | 不含 `superconductor_kind` | 保留状态条件、结构与结果字段 |

## 升级步骤

1. 给 `papers` 增加 `superconductor_kind`，默认 `unknown`。
2. 按 `(paper_id, paper_revision)` 聚合状态级历史值并写入当前匹配 revision 的论文。
3. 删除状态级 CHECK 约束和列。

冲突值写入 `unknown`，而不是依赖状态行顺序。
