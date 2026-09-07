# 数据表关系图

## 目标关系

```mermaid
erDiagram
    papers ||--o{ chemical_systems : "论文版本包含元素体系"
    papers ||--o{ superconductors : "论文版本包含材料"
    chemical_systems ||--o{ superconductors : "体系包含具体组成"
    superconductors ||--o{ material_states : "材料具有研究状态"

    material_states ||--o{ structure_models : "具有本论文结构"
    material_states ||--o{ calculation_conditions : "具有计算 Conditions"
    material_states ||--o{ experimental_conditions : "具有实验 Conditions"
    material_states ||--o{ property_modules : "按需挂载模块"

    property_modules ||--o{ property_records : "包含平级记录"
    form_definitions ||--o{ property_records : "按版本解释和校验"
    form_definitions ||--o{ property_definition_promotion_events : "保存管理员提升来源"
    property_records ||--o{ property_record_definition_events : "记录升级与回滚"
    calculation_conditions |o--o{ property_records : "同一次计算产生或使用"
    experimental_conditions |o--o{ property_records : "同一次实验产生"
    structure_models |o--o{ property_records : "可选本论文结构"

    property_records ||--o{ property_record_evidences : "引用原文证据"
    paper_evidences ||--o{ property_record_evidences : "支持科学事实"
```

图中的 `papers` 关系实际使用 `paper_id + paper_revision`。每条子记录都属于明确论文版本；图为便于
阅读省略复合外键列。

## 从论文到物性的理解方式

```text
论文 A
└── H-La
    └── LaH10
        └── 170 GPa 状态
            ├── 计算 Conditions A
            ├── 计算 Conditions B
            ├── 超导性质模块
            │   ├── 预测 Tc 250 K -> Conditions A
            │   └── 预测 Tc 220 K -> Conditions B
            └── 电子性质模块
                └── DOS

论文 B
└── H-La
    └── LaH10                 # 与论文 A 的 LaH10 主键不同
        └── 170 GPa 状态
```

论文 A、B 可以通过规范化学式一起被搜索，但任何一方的修改和删除都不会改变另一方。

## 模块与记录

`property_modules` 是材料状态中的模块清单，`property_records` 保存实际科学事实。添加一个新模块不需要
给 `material_states` 新增一列；发布相应模块和记录定义后即可挂载。记录只属于一个模块，非空模块不能
在未显式处理记录时删除。

```text
MaterialState
└── PropertyModule(module_code=superconductive_properties)
    ├── PropertyRecord(record_type=predicted_tc)
    ├── PropertyRecord(record_type=measured_tc)
    └── PropertyRecord(property_code=hc2)
```

模块内部记录没有上下级归属。预测 Tc 与它采用的 mu_star 通过共同 Conditions 关联，不把 mu_star
嵌套成 Tc 的可变子字段。

## 定义与记录版本

```text
FormDefinition(predicted_tc, v1) <- 历史记录 A
FormDefinition(predicted_tc, v2) <- 新记录 B
```

v2 发布后不会改写 v1 或记录 A。只有显式升级操作才会把 A 转换并重新绑定到 v2。

自定义性质可以使用已发布通用模板随论文审核保留。管理员提升时发布独立的全站普通性质定义，并保存
来源快照；不改写原 PropertyRecord，不创建跨论文共享记录。来源以审计快照保留，不使用阻止论文删除
的反向外键，也不因论文删除而删除全站定义。
