# 数据模型：上传校对页布局重构与材料状态卡片完善

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 持久层变更（MySQL，alembic 迁移 `20260826_0014`）

### material_states（新增 1 列）

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `superconductor_kind` | VARCHAR(32) NOT NULL，server_default `'unknown'` | CHECK `IN ('conventional','unconventional','unknown')`（`ck_material_states_superconductor_kind`） | 超导类型：常规(BCS)/非常规/未知；历史行默认 unknown |

### tc_results（新增 1 列 + 约束替换）

| 变更 | 内容 |
|------|------|
| `tc_method` CHECK 替换 | 删除 `ck_tc_results_method`，重建为 `IN ('experimental','mcmillan','allen_dynes','isotropic_eliashberg','anisotropic_eliashberg','scdft','other','unknown')` |
| `tc_method_custom` | VARCHAR(128) NULL；`tc_method='other'` 时保存自定义方法文本 |

既有不变：`ck_tc_results_context_kind`（theoretical Tc 必须挂 `calculation_context_id`）、`ck_material_states_element_count`（1–118）、`ck_material_states_reported_space_group`（1–230）。

### 关系语义

- 常规 Tc：`tc_results` 1—1 `calculation_contexts`（逐条创建，λ/ωlog/μ\* 归属该条 Tc）。
- 非常规/未知 Tc 或条目未带专属参数：沿用现状共享材料状态级 CalculationContext（存在时）。
- `element_count` 入库值 = 草稿非空值优先，否则 `count_formula_elements(material)`。

## 草稿契约变更（Redis JSON，`DraftMaterialState` / `DraftTcResult`）

```ts
interface DraftMaterialState {
  // ……既有字段不变
  superconductor_kind?: 'conventional' | 'unconventional' | 'unknown'  // 新增，默认 unknown
  element_count_locked?: boolean                                       // 新增，手动编辑锁定（D2）
}

interface DraftTcResult {
  // ……既有字段不变
  calculation_context?: DraftCalculationContext | null  // 新增：常规 Tc 的 λ/ωlog/μ*
  tc_method_custom?: string | null                      // 新增：other 的自由文本
}
```

规范化规则（`_normalize_material_states` 内新增/调整）：

1. `superconductor_kind` 白名单校验，非法值回落 `unknown`。
2. `element_count`：锁定不动 → 严格解析 → 宽松解析 → 保留已有非空（D2/D3）。
3. 空间群群号：符号命中 spglib 全表（D1）即补，替换 2 条硬编码。
4. 每条 `tc_results[].calculation_context` 按状态级同一套数值化规则处理（lambda/omega_log/mu_star 数值化）。
5. `tc_method` 合法集同 DB 新约束；`tc_method_custom` 仅在 `tc_method='other'` 时保留，否则置空。

## 纸面实体（goserver 同步）

- `goserver/models/models.go`：`MaterialState` 增 `SuperconductorKind string`；`TcResult` 增 `TcMethodCustom *string`。
- `goserver/handlers/papers.go`：`materialStatesToDict` 输出 `superconductor_kind`；tc_results 字典输出 `tc_method_custom` 及（已有关联时）条目级 λ/ωlog/μ\*。

## 生命周期

- 迁移：`alembic upgrade head` 一次执行；downgrade 删除列并恢复原 CHECK。
- 历史数据：`superconductor_kind` 默认 `unknown`；既有状态级 CalculationContext 行不动。
- 草稿：24h TTL 内按新契约读写；旧草稿缺字段时 `setdefault` 兜底（unknown/false/null）。
