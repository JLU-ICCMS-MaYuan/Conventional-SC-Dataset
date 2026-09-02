# 数据模型：论文级 Material family 多选分类

**GitHub Issue**：[#79](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/79)

**日期**：2026-09-02

## 目标关系

```text
papers (id, content_revision)
  1 ─── * paper_material_families * ─── 1 material_families

papers (id, content_revision)
  1 ─── * material_states
              1 ─── * material_state_structure_families * ─── 1 structure_families
```

Material family 属于论文版本；More type labels 继续属于材料状态。

## 新表 `paper_material_families`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `paper_id` | INTEGER | 非空、复合外键 | 论文 ID |
| `paper_revision` | INTEGER | 非空、复合外键 | 论文内容版本 |
| `material_family_id` | BIGINT | 非空、外键 RESTRICT | 目录项 ID |
| `created_at` | DATETIME | 非空、默认当前时间 | 创建时间 |

约束：

- 唯一键 `(paper_id, paper_revision, material_family_id)`。
- 这三个字段共同构成复合主键，不额外创建无业务意义的自增 ID。
- `(paper_id, paper_revision)` 引用 `papers(id, content_revision)`，`ON UPDATE CASCADE`、`ON DELETE RESTRICT`。
- `material_family_id` 引用 `material_families.id`，`ON DELETE RESTRICT`。
- 为 `material_family_id` 建索引，支持按目录筛选论文。

## 删除字段

- 删除 `material_states.material_family_id` 及其索引、外键。
- `material_states` 的其他列和 `material_state_structure_families` 不变。

## 数据迁移

### Upgrade

1. 创建 `paper_material_families`。
2. 从 `material_states` 选择非空 `(paper_id, paper_revision, material_family_id)` 并 `DISTINCT` 插入。
3. 核验没有重复关联且论文审核状态未被更新。
4. 删除 `material_states.material_family_id` 外键、索引和列。

### Downgrade

1. 检查每个 `(paper_id, paper_revision)` 的 family 数量；大于 1 时终止降级。
2. 恢复 `material_states.material_family_id` 为可空列、索引和 RESTRICT 外键。
3. 对 family 数量为 1 的论文，把该 ID 回填到其全部材料状态。
4. 删除 `paper_material_families`。

降级恢复列为可空，因为新模型允许没有材料状态的 Review 论文，也可能存在未完成历史数据；业务非空由旧应用校验处理。

## 生命周期

- 草稿：Redis 中 `paper.material_families[]` 可以为空并可含 pending 候选。
- 提交：必须至少一项；Python 持久化只写已解析目录 ID，pending 候选保留审核上下文。
- 批准：Go 在事务中解析/创建全部目录项并整体替换论文关联。
- 科学数据编辑：pending 原 revision 重写；approved 升版时已有正式关联随外键级联保留。请求中的候选由管理编辑页继续持有，最终关联只在批准事务中整体替换。
- 删除论文：删除论文前必须先删除 `paper_material_families`，共享目录不删除。
