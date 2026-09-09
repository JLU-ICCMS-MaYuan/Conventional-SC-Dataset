# 数据表关系图

## 目标关系

Mermaid ER 图的“基数”表示法，采用乌鸦脚记法：
o = 0，可选
| = 1
{ 或 } = 多
```mermaid
erDiagram
    A ||--o{ B : "关联"
    material_states ||--o{ property_modules : "按需挂载模块"
```
每条 B 必须属于一个 A (每个物性模块必须属于一个材料状态)
一条 A 可以没有 B，也可以拥有多条 B (一个材料状态可以有零个或多个物性模块)



```mermaid
erDiagram
    A |o--o{ B : "关联"
    structure_models |o--o{ property_records : "可选本论文结构"
```
每条 B 可以不关联 A，最多关联一个 A (一条 property_record 可以不指定结构，也可以指定一个 structure_model)
一条 A 可以没有 B，也可以关联多条 B (一个 structure_model 可以不被任何物性记录引用，也可以被多条物性记录引用)




```mermaid
erDiagram
    papers ||--o{ chemical_systems : "论文版本包含元素体系"
    papers ||--o{ superconductors : "论文版本包含材料"
    chemical_systems ||--o{ superconductors : "体系包含具体组成"
    superconductors ||--o{ material_states : "材料具有研究状态"

    material_states ||--o{ structure_models : "具有本论文结构"
    material_states ||--o{ property_modules : "按需挂载模块"

    material_states ||--o{ material_state_structure_families : "标注结构家族"
    structure_families ||--o{ material_state_structure_families : "被材料状态采用"

    property_modules ||--o{ property_records : "包含平级记录"
    form_definitions ||--o{ property_records : "按版本解释和校验"
    form_definitions ||--o{ property_definition_promotion_events : "保存管理员提升来源"
    property_records ||--o{ property_record_definition_events : "记录升级与回滚"
    structure_models |o--o{ property_records : "可选本论文结构"

    property_records ||--o{ property_record_evidences : "引用原文证据"
    paper_evidences ||--o{ property_record_evidences : "支持科学事实"
```



```mermaid
erDiagram
    papers ||--o{ chemical_systems : "论文版本包含元素体系"
    papers ||--o{ superconductors : "论文版本包含材料"
    chemical_systems ||--o{ superconductors : "体系包含具体组成"
    superconductors ||--o{ material_states : "材料具有研究状态"

    material_states ||--o{ structure_models : "具有本论文结构"
    material_states ||--o{ property_modules : "按需挂载模块"

    material_states ||--o{ material_state_structure_families : "标注结构家族"
    structure_families ||--o{ material_state_structure_families : "被材料状态采用"

    property_modules ||--o{ property_records : "包含平级记录"
    form_definitions ||--o{ property_records : "按版本解释和校验"
    form_definitions ||--o{ property_definition_promotion_events : "保存管理员提升来源"
    property_records ||--o{ property_record_definition_events : "记录升级与回滚"
    structure_models |o--o{ property_records : "可选本论文结构"

    property_records ||--o{ property_record_evidences : "引用原文证据"
    paper_evidences ||--o{ property_record_evidences : "支持科学事实"

    structure_models ||--o{ structure_model_evidences : "引用结构证据"
    paper_evidences ||--o{ structure_model_evidences : "支持结构信息"
```



```mermaid
erDiagram
    papers ||--o{ chemical_systems : "paper_id + paper_revision"
    papers ||--o{ superconductors : "paper_id + paper_revision"
    chemical_systems ||--o{ superconductors : "同一论文版本"
    superconductors ||--o{ material_states : "同一论文版本"

    material_states ||--o{ structure_models : "同一论文版本"
    material_states ||--o{ property_modules : "同一论文版本"
    property_modules ||--o{ property_records : "同一论文版本"

    structure_models |o--o{ property_records : "可选同版本结构"

    paper_files ||--o{ paper_chunks : "同一论文版本"
    paper_chunks ||--o{ paper_evidences : "同一论文版本"

    paper_evidences ||--o{ property_record_evidences : "支持科学事实"
    paper_evidences ||--o{ structure_model_evidences : "支持结构信息"

    form_definitions ||--o{ property_modules : "定义版本"
    form_definitions ||--o{ property_records : "定义版本"
```



```mermaid
erDiagram
    papers ||--o{ chemical_systems : "研究哪些元素体系"
    papers ||--o{ superconductors : "收录哪些材料组成"
    chemical_systems ||--o{ superconductors : "体系下区分具体组成"
    superconductors ||--o{ material_states : "按压力温度等区分研究状态"

    material_states ||--o{ structure_models : "保存具体晶体结构"
    material_states ||--o{ property_modules : "按性质类别挂载模块"
    property_modules ||--o{ property_records : "收录测量预测及其他物性结果"
    structure_models |o--o{ property_records : "结果可关联具体结构"

    material_states ||--o{ material_state_structure_families : "登记结构家族及主分类"
    structure_families ||--o{ material_state_structure_families : "提供结构家族分类"

    papers ||--o{ paper_files : "保存主论文与附件"
    paper_files ||--o{ paper_chunks : "解析为正文片段"
    paper_chunks ||--o{ paper_evidences : "定位原文摘录与证据"

    property_records ||--o{ property_record_evidences : "关联结果或字段的证据"
    paper_evidences ||--o{ property_record_evidences : "提供科学结果的原文依据"

    structure_models ||--o{ structure_model_evidences : "关联结构证据"
    paper_evidences ||--o{ structure_model_evidences : "提供结构信息的原文依据"

    form_definitions ||--o{ property_modules : "定义模块结构与展示规则"
    form_definitions ||--o{ property_records : "定义结果字段条件参数及校验规则"

    property_records ||--o{ property_record_definition_events : "留存定义升级与回滚快照"
    form_definitions ||--o{ property_definition_promotion_events : "留存提升为全站定义的来源快照"
```



```mermaid
flowchart TD
    papers["papers<br/>论文"]
    chemical_systems["chemical_systems<br/>元素体系"]
    superconductors["superconductors<br/>材料组成"]
    material_states["material_states<br/>研究状态"]
    structure_models["structure_models<br/>具体晶体结构"]
    property_modules["property_modules<br/>当前状态的一个物性模块"]

    subgraph property_records["property_records：同一模块下的三条记录（示意）"]
        record_1["记录 1：预测 Tc<br/>数值、方法、计算条件、参数"]
        record_2["记录 2：测量 Tc<br/>数值、方法、实验条件"]
        record_3["记录 3：超导能隙<br/>数值、单位、方法及适用条件"]
    end

    papers -->|"研究哪些元素体系"| chemical_systems
    papers -->|"收录哪些材料组成"| superconductors
    chemical_systems -->|"体系下区分具体组成"| superconductors
    superconductors -->|"按压力温度等区分研究状态"| material_states

    material_states -->|"保存具体晶体结构"| structure_models
    material_states -->|"按性质类别挂载模块"| property_modules
    property_modules -->|"module_id 关联"| record_1
    property_modules -->|"module_id 关联"| record_2
    property_modules -->|"module_id 关联"| record_3
    structure_models -.->|"各条结果可关联具体结构"| property_records

    material_states -->|"登记结构家族及主分类"| material_state_structure_families
    structure_families -->|"提供结构家族分类"| material_state_structure_families

    papers -->|"保存主论文与附件"| paper_files
    paper_files -->|"解析为正文片段"| paper_chunks
    paper_chunks -->|"定位原文摘录与证据"| paper_evidences

    property_records -->|"各条记录分别关联结果或字段的证据"| property_record_evidences
    paper_evidences -->|"提供科学结果的原文依据"| property_record_evidences

    structure_models -->|"关联结构证据"| structure_model_evidences
    paper_evidences -->|"提供结构信息的原文依据"| structure_model_evidences

    form_definitions -.->|"定义模块结构与展示规则"| property_modules
    form_definitions -.->|"各条记录分别绑定定义版本"| property_records

    property_records -->|"留存各条记录的定义升级与回滚快照"| property_record_definition_events
    form_definitions -.->|"提升事件记载目标定义键及版本"| property_definition_promotion_events
```



```mermaid
flowchart TB
    subgraph MAIN["① 科研数据主线"]
        direction LR
        P["papers<br/>论文"]
        C["chemical_systems<br/>元素体系"]
        S["superconductors<br/>材料组成"]
        M["material_states<br/>研究状态"]
        ST["structure_models<br/>具体晶体结构"]

        P -->|"研究哪些元素体系"| C
        C -->|"区分具体组成"| S
        P -->|"收录材料组成"| S
        S -->|"按压力、温度等区分"| M
        M -->|"保存具体结构"| ST
    end

    subgraph PROP["② 物性模块与结果"]
        direction TB
        PM["property_modules<br/>当前状态下的一个物性模块"]

        subgraph PR["property_records · 同一张表中的三条记录（示意）"]
            direction LR
            R1["记录 1：预测 Tc<br/>数值、方法<br/>本条计算条件与参数"]
            R2["记录 2：测量 Tc<br/>数值、方法<br/>本条实验条件"]
            R3["记录 3：超导能隙<br/>数值、单位、方法<br/>本条适用条件"]
        end

        PM -->|"module_id"| R1
        PM -->|"module_id"| R2
        PM -->|"module_id"| R3
    end

    subgraph CLASS["③ 结构家族分类"]
        direction LR
        SF["structure_families<br/>结构家族词典"]
        MSF["material_state_structure_families<br/>状态与结构家族的关联<br/>登记主分类"]

        SF -->|"提供分类"| MSF
    end

    subgraph SOURCE["④ 文件、原文与证据"]
        direction TB

        subgraph TEXT["原文追溯链"]
            direction LR
            F["paper_files<br/>主论文与附件"]
            CH["paper_chunks<br/>正文片段"]
            E["paper_evidences<br/>原文摘录与位置"]

            F -->|"解析"| CH
            CH -->|"定位原文依据"| E
        end

        subgraph LINKS["证据关联"]
            direction LR
            RE["property_record_evidences<br/>结果或字段与证据的关联"]
            SE["structure_model_evidences<br/>结构与证据的关联"]
        end

        E -->|"支持科学结果"| RE
        E -->|"支持结构信息"| SE
    end

    subgraph DEF["⑤ 表单定义与演进审计"]
        direction LR
        FD["form_definitions<br/>版本化表单定义"]
        DE["property_record_definition_events<br/>记录定义升级与回滚快照"]
        PE["property_definition_promotion_events<br/>提升为全站定义的来源快照"]

        FD -.->|"提升事件记载目标定义键与版本"| PE
    end

    M -->|"按性质类别挂载"| PM
    M -->|"登记结构家族"| MSF
    ST -.->|"每条结果可选关联"| PR

    P -->|"保存文件"| F
    PR -->|"各条记录分别关联证据"| RE
    ST -->|"关联结构证据"| SE

    FD -.->|"模块结构与展示规则"| PM
    FD -.->|"各条记录的字段、条件、参数及校验规则"| PR
    PR -->|"各条记录的定义变更留痕"| DE

    classDef main fill:#eaf2ff,stroke:#6488ba,color:#172b4d
    classDef property fill:#e8f5ef,stroke:#57977a,color:#173d2c
    classDef evidence fill:#fff5e5,stroke:#bd914c,color:#59401b
    classDef definition fill:#f2ecfa,stroke:#9577b3,color:#412d58
    classDef classification fill:#f1f3f5,stroke:#89939e,color:#303840

    class P,C,S,M,ST main
    class PM,R1,R2,R3 property
    class F,CH,E,RE,SE evidence
    class FD,DE,PE definition
    class SF,MSF classification
```



```mermaid
erDiagram
    direction TB

    papers ||--o{ chemical_systems : "研究元素体系"
    chemical_systems ||--o{ superconductors : "区分材料组成"
    papers ||--o{ superconductors : "收录材料组成"
    superconductors ||--o{ material_states : "区分压力温度等研究状态"

    material_states ||--o{ property_modules : "挂载物性模块"
    property_modules ||--o{ property_records : "包含多条记录"
    material_states ||--o{ structure_models : "保存晶体结构"
    structure_models |o--o{ property_records : "结果可关联结构"

    property_modules {
        bigint id PK "模块主键"
        bigint material_state_id FK "所属材料状态"
        varchar module_code "例如：超导性质"
        int display_order "展示顺序"
    }

    property_records {
        bigint id PK "记录主键"
        bigint module_id FK "所属模块"
        varchar record_type "预测Tc、测量Tc或其他性质"
        varchar property_code "科学量代码"
        decimal value_number "规范数值"
        varchar canonical_unit "规范单位"
        varchar method_code "方法"
        json payload_json "本条记录的条件与参数"
    }

    material_states ||--o{ material_state_structure_families : "登记分类及主分类"
    structure_families ||--o{ material_state_structure_families : "提供结构家族"

    papers ||--o{ paper_files : "保存主论文与附件"
    paper_files ||--o{ paper_chunks : "解析正文片段"
    paper_chunks ||--o{ paper_evidences : "定位原文证据"

    property_records ||--o{ property_record_evidences : "关联结果或字段证据"
    paper_evidences ||--o{ property_record_evidences : "提供结果依据"

    structure_models ||--o{ structure_model_evidences : "关联结构证据"
    paper_evidences ||--o{ structure_model_evidences : "提供结构依据"

    form_definitions ||--o{ property_modules : "绑定模块定义版本"
    form_definitions ||--o{ property_records : "定义字段条件参数及校验"

    property_records ||--o{ property_record_definition_events : "留存升级与回滚快照"
    form_definitions ||--o{ property_definition_promotion_events : "提升事件记载目标定义"
```



图中的 `papers` 关系实际使用 `paper_id + paper_revision`。每条子记录都属于明确论文版本；图为便于  
阅读省略复合外键列。

## 从论文到物性的理解方式

```text
论文 A
└── H-La
    └── LaH10
        └── 170 GPa 状态
            ├── 结构等状态资料
            ├── 超导性质模块
            │   ├── 预测 Tc-A：250 K，Allen-Dynes
            │   │   ├── 本条 Conditions：k/q 网格、各自展宽、软件等
            │   │   ├── 本条参数：λ=2.2，ωlog=1100 K，μ*=0.10
            │   │   └── 本条证据、预留分组与新增字段
            │   ├── 预测 Tc-B：220 K，Allen-Dynes
            │   │   ├── 本条 Conditions：k/q 网格、各自展宽、软件等
            │   │   ├── 本条参数：λ=2.2，ωlog=1100 K，μ*=0.15
            │   │   └── 本条证据、预留分组与新增字段
            │   └── 测量 Tc：结果、方法、本条实验 Conditions、判据、证据
            └── 电子性质模块
                └── DOS 及其完整资料

论文 B
└── H-La
    └── LaH10                 # 与论文 A 的 LaH10 主键不同
        └── 170 GPa 状态
```

以上数字用于示意归属，不是论文数据或公式验算。A/B 条件和参数可重复；修改 A 不改变 B。

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

模块内部记录平级，每条记录内部可以分组。预测 Tc 把它采用的 μ*、λ、ωlog 放在自己的参数分组中，  
Conditions 放在自己的条件分组中；它们存入同一 `property_records.payload_json`，没有输入关系表。  
独立报告的其他物性仍可单独录入，但不会自动与 Tc 参数联动。

导出以一个 MaterialState 为单位，打包材料、状态、结构、各模块完整记录、证据和所用定义内容。  
用户下载后即可理解每条 Tc，不需要再导出关系表自行拼接。

## 定义与记录版本

```text
FormDefinition(predicted_tc, v1) <- 历史记录 A
FormDefinition(predicted_tc, v2) <- 新记录 B
```

v2 发布后不会改写 v1 或记录 A。只有显式升级操作才会把 A 转换并重新绑定到 v2。

自定义性质可以使用已发布通用模板随论文审核保留。管理员提升时发布独立的全站普通性质定义，并保存  
来源快照；不改写原 PropertyRecord，不创建跨论文共享记录。来源以审计快照保留，不使用阻止论文删除  
的反向外键，也不因论文删除而删除全站定义。




| 数据表 | 行数 | 一行表示什么 | 关键字段 |
|---|---:|---|---|
| `papers` | 1 | 一篇论文及其当前内容版本 | `doi`、`title`、`journal`、`year`、`authors`、`abstract`、`content_revision`、`approved_revision`、`review_status` |
| `chemical_systems` | 1 | 当前论文版本中的一个元素体系 | `paper_id`、`paper_revision`、`system_key`、`elements_list`、`element_count` |
| `superconductors` | 1 | 当前论文版本中的一种材料组成 | `chemical_system_id`、`chemical_formula`、`formula_normalized`、`composition_key`、`isotope_signature`、`composition`、`element_ratio` |
| `material_states` | 1 | 材料在特定压力、温度、结构分类等条件下的研究状态 | `superconductor_id`、`state_key`、压力、温度、磁场、`state_kind`、空间群、维度、晶系 |
| `structure_models` | 1 | 一个状态下的一份具体晶体结构 | `material_state_id`、`parent_structure_id`、`structure_format`、`structure_text`、`cell_parameters`、体积、原子数、计算方法 |
| `property_modules` | 1 | 某个状态下的一个物性模块 | `material_state_id`、`module_key`、`module_code`、`definition_key`、`definition_version`、`display_order` |
| `property_records` | 1 | 模块中的一条科学结果 | `module_id`、`record_type`、`property_code`、数值、单位、方法、判据、`payload_json`、定义版本 |