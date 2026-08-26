# 数据模型：校对表单迭代

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 持久层变更（MySQL，alembic 迁移 `20260826_0015`）

### material_states（新增 1 列）

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| `crystal_system` | VARCHAR(32) NOT NULL，server_default `'unknown'` | CHECK `IN ('triclinic','monoclinic','orthorhombic','tetragonal','trigonal','hexagonal','cubic','unknown')`（`ck_material_states_crystal_system`） | 晶系；历史行默认 unknown |

其余表不变。`tc_results`、`structure_families`（is_primary）等维持 #51/#52 模型。

## 晶系↔群号静态映射（代码常量，不入库）

| 晶系 | 群号范围 |
|------|----------|
| triclinic 三斜 | 1–2 |
| monoclinic 单斜 | 3–15 |
| orthorhombic 正交 | 16–74 |
| tetragonal 四方 | 75–142 |
| trigonal 三方 | 143–167 |
| hexagonal 六方 | 168–194 |
| cubic 立方 | 195–230 |

规范化权威规则：`reported_space_group_number` 非空 → `crystal_system` 按范围强制推导；群号空 → 保留白名单化值（非法 → unknown）。

## 草稿契约变更

```ts
interface DraftMaterialState {
  // ……#52 字段不变
  crystal_system?: 'triclinic'|'monoclinic'|'orthorhombic'|'tetragonal'
                 | 'trigonal'|'hexagonal'|'cubic'|'unknown'  // 新增，默认 unknown
}
```

- `structure_families[].is_primary` 字段保留；编辑器新写入一律 false（D4）。
- `superconductor_kind` 数据契约不变（D5：仅 UI 选项收敛）。

## 研究方法推导（规范化期计算，不落新字段）

- 输入：paper 级 `methodology: string[]`；输出：原地改写材料状态的 `superconductor_kind`（unknown→conventional）与既有理论 Tc 条目的 `tc_method`（unknown→映射方法）。
- 映射（忽略大小写，先 Allen-Dynes 后 McMillan）：`Allen-Dynes`→allen_dynes；`McMillan`→mcmillan；`Eliashberg`+`anisotropic`→anisotropic_eliashberg；其余 `Eliashberg`→isotropic_eliashberg；`SCDFT`/`superconducting density functional`→scdft。
- 去重后方法集合为空：不动；集合 ≥1：补类型；集合 ==1：补方法；集合 ≥2：不补方法。

## goserver 同步

- `MaterialState` 增 `CrystalSystem string`（`materialStatesToDict` 输出 `crystal_system`）；`classificationSnapshotState` 同步。
