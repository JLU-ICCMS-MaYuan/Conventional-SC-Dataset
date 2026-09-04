# 契约：统一物性记录的持久化映射

## 原则

领域上的单一集合不等于数据库中的单一宽表。持久化层必须隐藏表差异，同时保留各表已有的
强约束和查询能力。

## 写入映射

| 条件 | 目标实体 | 关键映射 |
| --- | --- | --- |
| `property_code=tc` | `tc_results` | 公共值字段映射为 Tc K 值/区间；保存结果级判据；Tc 专用字段按 `tc_method` 校验；关联一种 Context |
| `property_code!=tc` | `superconductor_properties` | 使用 `property_definitions` 规范代码和值类型；保存结果级方法/判据；关联零或一种 Context |
| `context.kind=calculation` | `calculation_contexts` | 按请求内 `context_key` 去重；只保存方法和条件 |
| `context.kind=experimental` | `experimental_contexts` | 按请求内 `context_key` 去重；保存样品和测量条件 |
| 记录 Evidence | 对应 Tc 或通用物性 Evidence 连接表 | 必须与记录属于同一论文 revision |

λ、ωlog、μ* 新写入只进入 `superconductor_properties`，不得再写
`calculation_contexts.lambda_ep/omega_log_k/mu_star`。

## 读取映射

1. 读取材料状态下的 `tc_results`，映射为 `property_code=tc`。
2. 读取材料状态下的 `superconductor_properties`，按定义代码映射为其余记录。
3. 批量读取并嵌入关联 Context、Structure 和 Evidence。

旧 Context 参数列由 Alembic 在升级时完成回填和移除，不是升级后运行时读取的第二来源。
旧 Redis 草稿和旧 API fixture 由边界兼容器转换。

## 事务边界

- 上传提交和管理员科学数据重写继续在单一数据库事务内完成。
- Context 必须在关联物性前建立；Evidence 必须在目标物性建立后连接。
- 任一记录、Context、Structure、revision 或 Evidence 校验失败时，整份科学数据写入回滚。
- 已批准论文的管理员重写继续使用 #76 的升版重审流程。

## 数据库约束

- `tc_results` 保留 #84 的理论/实验 Context 互斥约束。
- `tc_results` 增加结果级 `criterion`，`result_kind` 继续由 `tc_method` 推导并受数据库约束。
- `superconductor_properties` 增加结果级 `method_raw`、`criterion`，以及计算/实验 Context 最多一个的 CHECK 和同 revision 复合外键。
- `experimental_contexts` 只保存共享实验条件，不再保存结果级 `tc_criterion`。
- `property_definitions` 继续禁止 `tc` 进入通用定义，但必须允许并预置
  `lambda_ep`、`omega_log`、`mu_star`。
- 代表 Tc 唯一约束保持不变。
- 范围完整性、非负约束和来源指纹唯一约束保持不变或在统一值映射中提供等价保护。

## λ、ωlog、μ* 迁移

迁移对每个非空旧值建立一条通用物性记录：

| 旧列 | 新 `property_code` | 规范单位 |
| --- | --- | --- |
| `calculation_contexts.lambda_ep` | `lambda_ep` | 无量纲 |
| `calculation_contexts.omega_log_k` | `omega_log` | `K` |
| `calculation_contexts.mu_star` | `mu_star` | 无量纲 |

迁移必须满足：

- 来源指纹由论文、revision、材料状态、Context 和旧列名确定，可重复执行而不产生重复行；
- 新行保留原 Context 关系；
- 不把关联 Tc 的 Evidence 自动复制为参数 Evidence；
- 对缺少独立 Evidence 的历史值输出明细报告；
- 回填计数与迁移前各列非空计数逐项一致；
- upgrade 在计数核验成功后移除三个旧 Context 参数列，失败时整体回滚；
- downgrade 只恢复迁移生成行对应的旧列值并移除这些迁移生成行，不会删除迁移前或新版本创建的通用物性行。

## 实验判据迁移

- upgrade 将 `experimental_contexts.tc_criterion` 复制到每条关联实验 Tc 的
  `tc_results.criterion`；同一 Context 关联多条 Tc 时逐条复制。
- 计数和非空值核验成功后移除 Context 的 `tc_criterion` 列。
- downgrade 恢复该列；同一 Context 下判据不一致时必须停止并报告，不能任意选择一个值。

## 删除顺序

删除论文或重建当前 revision 时，至少遵守：

```text
Tc/通用物性 Evidence 连接
→ tc_results / superconductor_properties
→ calculation_contexts / experimental_contexts
→ structure_models
→ material_states
```

只删除最后一个关联记录后形成的孤立 Context；仍被其他物性引用的 Context 必须保留。
