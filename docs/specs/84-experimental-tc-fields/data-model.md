# 数据模型：实验 Tc 的条件字段与计算上下文一致性

**GitHub Issue**：[#84](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/84)

## 目标不变量

| `tc_results.tc_method` | `result_kind` | `calculation_context_id` | `experimental_context_id` |
| --- | --- | --- | --- |
| `experimental` | `experimental` | 必须为 `NULL` | 必须非空 |
| 其他允许方法 | `theoretical` | 必须非空 | 必须为 `NULL` |

λ、ωlog、μ* 仅属于 `calculation_contexts`。因此实验 Tc 不能通过任何关联路径拥有它们。

## 数据迁移

1. 锁定并读取 `tc_results.tc_method='experimental'` 的行。
2. 将这些行的 `calculation_context_id` 清为 `NULL`；保留或补齐其 `experimental_context_id`，无法满足实验上下文约束的异常记录必须迁移失败并报告主键，不得臆造测量条件。
3. 删除没有被 `tc_results` 或 `superconductor_properties` 引用的 `calculation_contexts`。
4. 替换 `ck_tc_results_context_kind`，令其同时表达上表中的方法与结果类型关系。
5. 用迁移后的 SQL 断言验证零条违例记录，并以真实隔离 MySQL 回归测试验证约束。

## 生命周期

- 用户切到 `experimental`：浏览器删除条目级计算上下文；草稿保存与提交校验重复执行。
- 管理员科学数据整体重写：同一验证先于删除/重建事务；持久化按方法建模。
- 历史数据：迁移一次性收敛；不在正常读取路径添加永久兼容分支。
