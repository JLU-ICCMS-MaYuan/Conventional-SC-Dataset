# 技术研究：实验 Tc 的条件字段与计算上下文一致性

**GitHub Issue**：[#84](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/84)

## R1：以 `tc_method` 而非上层分类决定字段

**决策**：`tc_method='experimental'` 是唯一的 UI 和写入开关。

**理由**：一篇论文或一个材料状态可同时含实验和理论 Tc。`superconductor_kind` 描述配对类型，`state_kind` 描述材料状态来源，都不能准确表达单条结果的计算或测量方式。

**证据**：`MaterialStatesEditor.tsx` 当前同时使用 `superconductorKind` 和 `state_kind`；`TcResult` 已有条目级 `tc_method`。

## R2：应用层校验与数据库约束共同保障

**决策**：API 返回可定位 400，数据库 `CHECK` 兜底。

**理由**：前者给用户可修正反馈，后者保护管理员重写、脚本和其他未来写入方。只依赖 UI 会让手工请求绕过规则。

## R3：一次性迁移清理孤立上下文

**决策**：解除实验 Tc 的关联后，仅删除无 Tc 和普通物性引用的上下文。

**理由**：`CalculationContext` 还可为理论普通物性服务；直接按实验 Tc 删除会破坏仍被引用的数据。
