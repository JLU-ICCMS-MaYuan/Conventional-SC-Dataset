# API 契约：论文级 Superconductor type

**GitHub Issue**：[ #80](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/80)

## 草稿与科学数据

```json
{
  "paper": {
    "superconductor_kind": "conventional",
    "material_families": [{"id": 1, "name": "氢基超导体"}]
  },
  "material_states": [{"material": "LaH10", "structure_families": []}]
}
```

`material_states[].superconductor_kind` 是旧契约；新 PUT/submit 返回 `legacy_classification_contract`。

## 论文详情

论文顶层返回 `superconductor_kind`。每个 `material_states[]` 不返回此字段。
