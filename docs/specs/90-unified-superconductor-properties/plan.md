# 实施计划：MaterialState 模块化物性与动态表单

**GitHub Issue**：[#90](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/90)

**日期**：2026-09-07

**Spec**：[spec.md](spec.md)

## 摘要

以 `MaterialState` 为科研数据主体，建立 `property_modules`、统一 `property_records` 和版本化
`form_definitions`。Tc 使用 `predicted_tc`、`measured_tc` 记录类型，固定核心列支持约束、搜索和图表，
方法扩展字段由 JSON Schema 驱动。计算和实验 Context 改名为 Conditions，并继续作为一次确定运行或
测量的关联节点。材料按论文 revision 独立保存，旧共享材料和分裂物性模型通过分阶段迁移收敛。

## 技术上下文

- **后端**：Python 3、FastAPI、SQLAlchemy、Pydantic、Alembic；Go 1.25、Gin、GORM。
- **前端**：React 19、TypeScript 5.6、Vite、Vitest。
- **数据库**：MySQL；Redis 只保存上传草稿，Qdrant/Neo4j 不作为物性权威存储。
- **Schema 校验**：Python 使用支持 JSON Schema 2020-12 所需子集的验证器；前端使用兼容验证器和
  项目组件生成控件。新增依赖前先确认现有依赖是否满足，避免引入两套校验器。
- **性能**：论文详情批量加载定义、模块、记录和 Conditions；Tc 图表走固定列与组合索引。
- **安全**：定义只允许超级管理员发布；Schema 不执行脚本；后端始终重新校验。

## 质量门

| 约束 | 设计响应 |
| --- | --- |
| MaterialState 是主体 | 全部模块、记录、Conditions、结构均使用同论文 revision 复合外键 |
| 论文内材料独立 | 材料唯一键限定在论文 revision，迁移拆分旧共享材料 |
| Tc 与相关物性不误配 | Conditions 表示一次确定执行，组级规则校验决定性输入 |
| 动态扩展不破坏历史 | 已发布定义不可变，记录绑定具体版本，升级显式执行 |
| 升级可以安全撤销 | 不可变升级事件保存前后快照，应用和回滚校验 revision、记录校验和与前序事件 |
| 核心查询可靠 | 核心字段固定列；JSON 只保存扩展字段 |
| Evidence 完整 | 使用统一证据连接，迁移缺口报告且不伪造 |
| MySQL 可恢复迁移 | 分阶段迁移，Contract 阶段独立执行 |
| 未实现设计不进入 Overview | Overview 只在实现、测试和迁移验证后更新 |

## 目标组件

```text
alembic/versions/
├── 20260907_issue90_expand_modular_property_schema.py
├── 20260907_issue90_copy_property_records.py
└── 20260907_issue90_contract_legacy_properties.py

backend/
├── models.py
├── ingest/
│   ├── property_modules.py
│   ├── form_definitions.py
│   └── scientific_drafts.py
├── services/
│   ├── form_definition_service.py
│   ├── property_record_upgrade_service.py
│   └── scientific_draft_rewrite.py
└── api/
    ├── form_definitions.py
    └── rag.py

goserver/
├── models/models.go
└── handlers/
    ├── papers.go
    └── stats.go

frontend/src/
├── lib/
│   ├── propertyModules.ts
│   └── formDefinitions.ts
├── components/
│   ├── MaterialStatesEditor.tsx
│   ├── PropertyModuleEditor.tsx
│   └── SchemaDrivenRecordForm.tsx
└── pages/AdminPaperEditPage.tsx
```

三个迁移文件使用上面的稳定文件名；实现时必须把 Expand 的 `down_revision` 接到届时实际 Alembic head，
Copy 和 Contract 依次连接，不得从当前文档日期推断过期 head。

## 数据与接口策略

1. `property_modules` 只保存模块实例和顺序，不保存物性值。
2. `property_records` 保存所有记录核心字段、定义版本和 `payload_json`。
3. `property_records` 使用两个互斥的 Conditions 复合外键；CHECK 强制 Tc 类型与外键类型一致。
4. `form_definitions` 保存定义、`identity_rules` 和 `group_rules`；发布操作做权限、版本递增、校验和和审计检查。
5. `property_record_definition_events` 保存定义升级与回滚的前后快照和并发校验依据。
6. `calculation_conditions`、`experimental_conditions` 保留各自固定条件字段和扩展 JSON；键使用类型前缀，
   但不根据内容自动合并。
7. API 输出 MaterialState 顶层 Conditions 和模块数组，记录用 `condition_key` 关联。
8. 前端读取定义生成控件；Python 使用同一版本校验；Go 只读取已验证数据并执行专用查询。

## 实施阶段

### 阶段 1：固定契约与失败测试

建立四模块、三类记录、Conditions 归组、定义 v1/v2、论文内两份 LaH10 和旧数据迁移 fixture。

### 阶段 2：Expand

新增目标表、固定列、外键、Tc CHECK/唯一键/索引和初始定义种子；旧表继续服务生产读取。

### 阶段 3：定义服务与校验器

实现定义读取、发布、停用、校验和、JSON Schema 校验和组级规则。前后端共享 fixture 验证一致性。

### 阶段 4：Copy 与 Reconcile

在影子材料表拆分论文内材料，复制 Conditions、Tc、普通物性和 Evidence。目标材料直接采用论文内唯一
键；旧材料表与 MaterialState 引用暂不变。生成逐项对账及异常报告，不删除旧数据。

### 阶段 5：最终增量复制与停写

进入约定维护窗口，阻止全部科学数据写入并排空在途事务；保留只读访问。同步 Copy 开始后新增、修改及
删除的论文完整 revision 图，
再次逐项对账，并记录可恢复的旧模型检查点。对账失败时解除停写并继续使用旧读写路径。

### 阶段 6：Read switch

停写期间按[迁移契约](contracts/persistence-mapping.md#分阶段迁移)更名影子材料表、重连状态和外键，
这段 DDL 期间显式暂停科学读取。随后先把详情、探索、社区、搜索和图表切换到目标模型，比较新旧结果、
验证查询计划并执行冒烟验收。任一读取不一致时完成反向恢复后才解除维护，目标模型仍不接受新写入。

### 阶段 7：Write switch、Observe 与 Contract

读取验收通过后，在同一维护窗口内把上传和管理员编辑切换到模块化契约，再解除停写。观察期内完成
定义升版与回滚、审核、删除和旧缓存兼容验证；确认无旧写入后，用独立迁移退役旧表和旧列。
切写后只采用目标模型恢复路径，不直接回退到已过期的旧表；具体顺序和数据保护要求以迁移契约为准。

### 阶段 8：文档与 Issue 收尾

按实际落地行为更新 Overview，记录迁移证据并完成 Issue Documentation Impact。

## 需求映射

| 需求 | 设计组件 | 验证 |
| --- | --- | --- |
| FR-001–FR-006 | 模块和统一记录 | 模块增删及四种值类型往返测试 |
| FR-007–FR-012 | Conditions 身份规则与 Tc 固定约束 | 两组 Tc 配对、重复运行、错配和代表唯一测试 |
| FR-013–FR-019 | FormDefinition、升级事件与动态表单 | v1/v2、发布不可变、升级回滚、前后端一致性测试 |
| FR-020–FR-022 | 论文内材料 | 双论文 LaH10 隔离与搜索测试 |
| FR-023–FR-030 | 目标 Schema 与分阶段迁移 | 隔离 MySQL 对账、切换、恢复和图表回归 |
| FR-031–FR-033 | 本地结构、权限和错误 | 跨 revision 拒绝、发布权限和错误路径测试 |
| FR-034–FR-035 | 全栈验证与文档 | 测试套件、构建、Quickstart 和 Overview |

## 必要复杂度

| 设计 | 必要原因 |
| --- | --- |
| 模块容器 | 新模块不需要修改 MaterialState 顶层字段集合 |
| 固定核心列 + JSON | 同时满足统计查询和方法字段扩展 |
| 不可变定义版本 | 新字段发布不改变历史记录语义 |
| Conditions 组级规则 | 防止同一材料状态下多组 Tc 与参数错配 |
| 两个互斥 Conditions 外键 | 让数据库直接约束记录关联的 Conditions 类型和 revision |
| 定义升级事件 | 在不改写审计历史的前提下支持预览、并发保护和回滚 |
| 分阶段迁移 | MySQL DDL 和历史数据切换需要可恢复稳定点 |
| 有界停写窗口 | 保证先切读再切写时没有复制后的旧写入遗漏或新数据不可见窗口 |

不引入可执行插件系统、完整物性本体或通用规则语言。首批规则只覆盖当前明确的四模块、Tc 方法和
Conditions 组合。
