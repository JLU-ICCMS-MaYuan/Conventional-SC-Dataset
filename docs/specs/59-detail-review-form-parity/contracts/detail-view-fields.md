# 展示契约：详情页字段集与校对表单对照

**Feature**：[spec.md](../spec.md)

**日期**：2026-08-27

本文是 SC-001「字段集逐项一致」的判定依据。左列为校对页（基准），右列为详情页应呈现的对应项。数据来源见 [#57 的接口契约](../../57-paper-detail-data-parity/contracts/paper-detail.md)。

## 材料状态：分类区

| 校对页字段 | 详情页对应项 | 数据来源 |
|---|---|---|
| 材料 | 材料 | `material_states[].material` |
| 材料家族 | 材料家族 | `material_states[].material_family.name` |
| 不同元素种类数 | 不同元素种类数 | `material_states[].element_count` |
| 材料维度 | 材料维度 | `material_states[].material_dimensionality` |
| 更多类型标签（可以填写不止一个类型） | 结构家族标签 | `material_states[].structure_families[].name` |
| 晶系 | 晶系 | `material_states[].crystal_system` |
| 空间群符号 | 空间群符号 | `material_states[].reported_space_group_symbol` |
| 空间群号 | 空间群号 | `material_states[].reported_space_group_number` |
| 超导类型 | 超导类型 | `material_states[].superconductor_kind` |

## 材料状态：压强区

| 校对页字段 | 详情页对应项 | 数据来源 |
|---|---|---|
| 压强 (GPa) | 压强 | `pressure_value_gpa` |
| （helperText）原文压力 | 原文压强 | `pressure_raw` + `pressure_unit_raw` |
| — | 压强下限 / 上限 | `pressure_min_gpa` / `pressure_max_gpa` |

**单臂区间规则**：`pressure_min_gpa` 与 `pressure_max_gpa` 只有一侧有值时，另一侧为 `null`，详情页**不得**显示凭空补造的边界，也不得把 `null` 渲染为 0。这是 #54 确立、#57 读取侧保持的语义。

**为何详情页多出下限/上限两项而不违反 FR-005**：校对页的压强输入框在无单值时以 helperText 显示原文压力，区间信息本身来自同一批 `pressure_*` 字段，属同一字段族的完整呈现，不是校对页不存在的新概念。相反，隐藏已入库的区间边界会使 #54 的成果再次不可见。

## 材料状态：临界温度 Tc 区

| 校对页字段 | 详情页对应项 | 数据来源 |
|---|---|---|
| Tc 数值 (K) | Tc 数值 | `tc_results[].tc_value_k` |
| Tc 方法 / 自定义 Tc 方法 | Tc 方法 | `tc_results[].tc_method` / `tc_method_custom` |
| — | Tc 区间 | `tc_results[].tc_min_k` / `tc_max_k` |
| — | 原文值与单位 | `tc_results[].value_raw` / `unit_raw` |
| — | 结果类型 | `tc_results[].result_kind` |
| 电声耦合强度 λ | 电声耦合强度 λ | `calculation_contexts[].lambda_ep` |
| 对数声子频率 ωlog (K) | 对数声子频率 ωlog | `calculation_contexts[].omega_log_k` |
| 库伦屏蔽常数 μ* | 库伦屏蔽常数 μ* | `calculation_contexts[].mu_star` |

**组织层级差异（允许）**：校对页把 λ/ωlog/μ* 挂在每条 Tc 结果的 `calculation_context` 内；详情页按材料状态级 `calculation_contexts` 数组完整列出。字段名称与含义一致，仅层级不同。SC-001 的基准是字段集一致，不要求 DOM 结构一致。

**多条计算上下文规则**：全部展示，含数值全为 NULL 的记录。不得只取首条——paper 4 的首条恰好全为 NULL，取首条会使 λ=2.56 不可见。

## 材料状态：其他普通物性区

| 校对页字段 | 详情页对应项 | 数据来源 |
|---|---|---|
| 物性 #N 名称 | 物性名称 | `key_properties[].name`（规范名，回退 `name_raw`） |
| 原始值 | 原始值 | `key_properties[].value_raw` |
| 单位 | 单位 | `key_properties[].unit` |
| — | 解析值 | `key_properties[].value_number` |
| — | 条件说明 | `key_properties[].condition_note` |

**禁止出现的项**：「最小值」「最大值」。校对页没有这两个输入，且 paper 4 实测两者均为 NULL —— 显示它们会让用户以为自己填过或系统丢了值。若 `value_min`/`value_max` 确有值（区间型物性），以「数值范围」单项呈现，不拆成两个空框。

**原始值与解析值并存**：两者都显示，可能不一致（paper 4 为 `"0"` 与 200）。详情页不裁决谁正确；该不一致属写入侧历史数据问题，已列入范围外。

## 论文层面字段

| 校对页字段 | 详情页对应项 | 数据来源 |
|---|---|---|
| 关键词（每行一个） | 关键词 | `keywords_tags` |
| 研究方法（每行一项） | 研究方法 | `methodology` |
| 分类理由 | **分类理由** | `rationale` 列 |

**研究方法形态**：必须逐项可读展示（每行一项或 Chip），不得输出 `["particle swarm optimization...", ...]` 形式的 JSON 原文。库内本就是英文术语列表，不做翻译。

**分类理由标签纠正**：`papers.rationale` 列当前存储的是用户在校对页填写的 `classification_reason`（后端 `rationale=draft.get("classification_reason") or paper_data.get("rationale")`，`or` 短路使前者优先）。因此详情页必须标为「分类理由」。**禁止出现**标为「研究理由」且有内容的字段——那会让用户认为系统凭空生成了他没写过的内容。

写入侧的字段分离属范围外事项。

## 只读性契约

详情页是纯展示组件：

- 不得存在可编辑的输入控件（所有文本展示为只读形态）
- 不得保留增删改函数（`updateKp`／`addKp`／`deleteKp` 之类）与「添加物性」「删除」按钮
- 不得依赖 `fieldset disabled` 之类的整体禁用手段来伪装只读——那会留下「移除 disabled 即可编辑但存不下」的陷阱

## 空态契约

| 场景 | 预期 |
|---|---|
| 无材料状态 | 明确空态说明，不渲染空白卡片骨架 |
| 无 Tc 结果 | 不渲染 Tc 区，或显示「无」；不显示空输入框 |
| 无计算上下文 | 同上 |
| 无结构数据 | 保留既有空态文案（当前全库 `structure_models` 为 0 行，这是唯一可实测路径） |
| 可选字段为 NULL | 不显示该项或显示「未填写」；不得渲染 `null`、`undefined` |
| 研究方法为空或非列表 | 不渲染空列表容器，不抛错 |
