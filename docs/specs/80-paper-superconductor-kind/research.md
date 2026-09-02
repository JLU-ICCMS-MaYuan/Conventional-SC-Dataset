# 技术研究：论文级 Superconductor type 单选分类

**GitHub Issue**：[ #80](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/80)

## 决策

1. 在 `papers` 添加 `superconductor_kind`，默认 `unknown`；不新建关联表，因为该分类是单值。
2. 删除 `material_states.superconductor_kind` 与对应 CHECK 约束。
3. 历史数据按 `(paper_id, paper_revision)` 聚合。只能得到一个非 `unknown` 值时保留；无值或冲突时设为 `unknown`。
4. 草稿主契约使用 `paper.superconductor_kind`。旧状态字段只在读取历史草稿时一次性提升；客户端 PUT 和提交拒绝其写入。
5. `MaterialStatesEditor` 接受论文级 type 作为控制参数，不再拥有该字段；这保持 Tc 结果和计算上下文仍归属于材料状态。

## 原因

论文级 type 是研究结论的整体分类。把相同值复制到每个材料状态会造成重复；多状态值冲突时，强行选第一项会伪造历史结论。`unknown` 是既有枚举的保守表达。

## 兼容边界

不保留正式读写的双契约。旧草稿可在归一化时提升，历史正式数据由迁移一次性转换。这样所有新路径只有一个数据事实来源。
