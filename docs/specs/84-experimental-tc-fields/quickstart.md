# 验证路径：实验 Tc 的条件字段与计算上下文一致性

**GitHub Issue**：[#84](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/84)

1. 在上传校对页新增 Tc，先选择 `experimental`，确认只显示 Tc 字段；切至理论方法后确认显示 λ、ωlog、μ*；再切回实验方法确认它们未恢复。
2. 保存草稿并检查请求负载：实验条目没有 `calculation_context`。
3. 在管理员和超级管理员论文编辑页重复步骤 1，保存后获取科学数据，确认实验结果没有 `calculation_context_id`。
4. 分别向上传草稿和科学数据重写端点发送实验 Tc 加计算上下文的负载，期望 400 与可定位错误；确认数据库没有部分新行。
5. 在隔离 MySQL 执行迁移，查询实验 Tc 均无计算上下文，理论 Tc 的关联保持可用。
