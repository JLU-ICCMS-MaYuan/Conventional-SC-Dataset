# 技术决策记录：校对表单迭代

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## D1：晶系↔群号映射做成静态范围表，不依赖 spglib

- **决策**：`backend/services/space_groups.py` 追加 `crystal_system_for_number(n)`（范围命中即返回）与 `numbers_for_crystal_system(system)`（返回 range）；映射为代码内静态表。前端复用同一映射（内联常量，与后端一致）。
- **理由**：7 个范围是晶体学固定事实，无运行时数据需求；群号→晶系由此确定性可得。
- **备选**：spglib 逐群取 hall 符号推晶系（更重且无收益，拒绝）。

## D2：群号是晶系的权威来源

- **决策**：规范化时 `reported_space_group_number` 非空 → `crystal_system` 强制按范围推导覆盖；群号空 → 保留白名单化的 AI/用户值。前端同样：符号/群号确定后立即改写晶系；只改晶系不清符号。
- **理由**：用户明确「一旦确定了空间群符号或者群号，其他两者也都自动确定」；范围推导无歧义。

## D3：研究方法推导放后端规范化，双向单向明确

- **决策**：`_normalize_draft` 在材料状态规范化后调用 `_apply_methodology_inference(methodology, material_states)`：扫描论文级 methodology 文本，按 FR-002 映射去重得方法集合；集合非空且状态 superconductor_kind 为 unknown → conventional；集合恰一个方法时补该状态 unknown 方法的理论 Tc 条目。AI prompt 不为此改动（规则确定性优于模型发挥，D3 与 #52 D10 一致）。
- **理由**：GET/PUT/summary 都过 `_normalize_draft`，推导自动生效且可单测；只补 unknown 不覆盖人工/AI 已填值。
- **备选**：放前端（保存时机不一致、不可单测，拒绝）；放 prompt（不可单测，拒绝，已被用户选项排除）。

## D4：is_primary 数据保留、编辑器停写

- **决策**：草稿 `structure_families[].is_primary` 字段保留（兼容旧草稿与 #51 审核），编辑器删除主结构家族 Select 且不再设置 is_primary（新写入均为 false）；标签改「更多类型标签（可以填写不止一个类型）」。
- **理由**：#51 的数据库约束是「最多一个主项」，零主项合法；不改数据模型则无迁移成本。

## D5：超导类型 UI 两项、数据三层不变

- **决策**：Select 选项仅 conventional/unconventional，label 全称「常规超导体（BCS超导体）」「非常规超导体」；值为 unknown 时 Select 显示占位（renderValue 空显示「请选择」）。
- **理由**：用户明确要求只提供两项；DB CHECK 与既有 unknown 默认不动。
