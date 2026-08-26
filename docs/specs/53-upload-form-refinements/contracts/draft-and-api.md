# 接口契约：校对表单迭代

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 接口变更

无新增/删除接口。`GET /api/rag/space-groups` 响应不变（前端晶系过滤在客户端用静态范围表完成）。

## 草稿 JSON 契约调整（GET/PUT draft、submit）

- `material_states[].crystal_system`：新增受控字段，8 值（见 data-model.md），缺省/非法 → `unknown`；群号非空时服务端按范围强制推导（权威）。
- `material_states[].structure_families[].is_primary`：保留读取；编辑器不再写入 true。
- 规范化副作用（PUT/GET 均生效）：研究方法推导可能改写 `superconductor_kind`（unknown→conventional）与理论 Tc 条目的 `tc_method`（unknown→映射方法），规则见 data-model.md；不产生新 Tc 条目。

## AI 汇总契约（SUMMARY_SYSTEM_PROMPT）

- `material_states[]` 新增 `"crystal_system": "triclinic|monoclinic|orthorhombic|tetragonal|trigonal|hexagonal|cubic|unknown"`，依据论文明确表述（如 cubic、tetragonal 或空间群推断）填写，无法确定填 unknown。
- 其余不变（CHUNK 契约与版本不动）。

## 前端 UI 契约

- AI 建议（EvidenceNotes）：默认单行截断；溢出时显示「展开/收起」切换。
- 晶系 Select：8 值（中文标签：三斜/单斜/正交/四方/三方/六方/立方/未知）。
- 空间群符号 Autocomplete：选项按当前晶系范围过滤（晶系未知显示全部 230）；选中符号 → 群号+晶系自动写；自由输入不联动。
- 群号输入：合法 1–230 输入 → 符号（按标准表该群号符号）+晶系自动写。
- 结构家族：标签「更多类型标签（可以填写不止一个类型）」；无主结构家族 Select。
- 超导类型 Select：仅「常规超导体（BCS超导体）」「非常规超导体」；unknown 显示占位。
