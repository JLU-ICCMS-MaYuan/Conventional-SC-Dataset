# 数据库不变量：统一物性持久化

## Revision 与归属

1. Tc、通用物性、Context 和 Evidence 必须属于同一 `paper_id + paper_revision`；全局规范结构身份
   可以被多个论文 revision 引用。
2. 物性与 Context 必须属于同一 `material_state_id`。
3. 科学子实体继续服从论文整篇 revision 审核，不增加独立审核状态。

## 物性值

1. 每条记录至少有原始值、规范单值、完整范围、文本值或布尔值中的一种有效表达。
2. 范围上下界必须同时存在且下界不大于上界。
3. 原始名称、值和单位不得被规范化覆盖。
4. λ、ωlog、μ* 新值只以通用物性行作为权威来源。
5. 同一论文 revision 的来源指纹不得重复。
6. `structure_ref` 为空合法；非空引用必须指向至少一个已批准当前 revision 的来源 `StructureModel`。

## Context

1. 通用物性最多关联一个计算 Context 或一个实验 Context。
2. Tc 按 `tc_method` 必须且只能关联正确类型的 Context。
3. 计算 Context 无结构时必须填写结构缺失原因。
4. Context 不得跨材料状态或 revision 引用。
5. Context 只保存共享方法环境和条件，不保存 λ、ωlog、μ* 或结果级判据。
6. 记录和 Context 同时有结构引用时，必须使用相同的全局 `structure_ref`；Context 的论文归属不因
   共享结构身份而改变。

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

## 规范结构身份

1. `structure_ref` 使用系统生成的不透明稳定值，数据库自增 ID 不进入客户端契约。
2. 身份定位只使用标准化化学式、规范压强、空间群和结构计算方法组合；不自动比较几何或合并物性。
3. 候选查询只返回已批准论文的当前 revision，压强绝对差不得超过 `0.01 GPa`，相同距离不得自动选中。
4. 删除或升版来源模型前，必须检查仍被引用的规范身份；不得静默留下无公开来源的有效引用。

## 兼容与单一来源

1. 旧字段只允许在边界读取和迁移中使用。
2. 新草稿、新写入和新响应只使用统一 `superconductor_properties[]`。
3. 持久化通用物性行优先于旧 Context 参数列；两者同时存在时不得返回两条记录。
4. 回填和验证成功后必须移除旧 Context 参数列，不得长期双写。
