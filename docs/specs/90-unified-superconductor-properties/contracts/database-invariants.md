# 数据库不变量：统一物性持久化

## Revision 与归属

1. Tc、通用物性、Context、Structure 和 Evidence 必须属于同一 `paper_id + paper_revision`。
2. 物性与 Context 必须属于同一 `material_state_id`。
3. 科学子实体继续服从论文整篇 revision 审核，不增加独立审核状态。

## 物性值

1. 每条记录至少有原始值、规范单值、完整范围、文本值或布尔值中的一种有效表达。
2. 范围上下界必须同时存在且下界不大于上界。
3. 原始名称、值和单位不得被规范化覆盖。
4. λ、ωlog、μ* 新值只以通用物性行作为权威来源。
5. 同一论文 revision 的来源指纹不得重复。

## Context

1. 通用物性最多关联一个计算 Context 或一个实验 Context。
2. Tc 按 `tc_method` 必须且只能关联正确类型的 Context。
3. 计算 Context 无结构时必须填写结构缺失原因。
4. Context 不得跨材料状态或 revision 引用。
5. Context 只保存共享方法环境和条件，不保存 λ、ωlog、μ* 或结果级判据。

## Tc

1. `tc_method=experimental` 必须对应 `result_kind=experimental` 和实验 Context。
2. 其他已知 Tc 方法必须对应 `result_kind=theoretical` 和计算 Context。
3. `result_kind` 由 `tc_method` 推导，不作为独立写入权威。
4. `tc_method=unknown` 不得进入正式提交或新批准 revision。
5. 每个论文 revision、材料状态和 Tc 方法最多一条代表结果。
6. Tc 数值或完整区间至少存在一种，所有 K 值和不确定度非负。
7. 实验 Tc 的结果级 `criterion` 必须是允许值；理论 Tc 的实验判据必须为空。

## Evidence

1. 新建或编辑后准备批准的每条物性至少有一个同 revision Evidence。
2. 历史 Context 参数回填不得伪造 Evidence；缺失项进入迁移报告。
3. Evidence 连接行可以级联删除，但不得反向删除物性或 Evidence 正文。

## 兼容与单一来源

1. 旧字段只允许在边界读取和迁移中使用。
2. 新草稿、新写入和新响应只使用统一 `superconductor_properties[]`。
3. 持久化通用物性行优先于旧 Context 参数列；两者同时存在时不得返回两条记录。
4. 回填和验证成功后必须移除旧 Context 参数列，不得长期双写。
