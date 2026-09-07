# 研究记录：MaterialState 模块化物性与动态表单

## 1. 当前事实

- 当前材料按规范组成在全库复用；`superconductors.composition_key` 和 `formula_normalized` 是全局唯一。
- 当前 Tc 位于 `tc_results`，其他物性位于 `superconductor_properties`，lambda、omega_log、mu_star
  仍可位于计算 Context 字段。
- 前端表单固定编码 Tc 方法与字段，Schema version 只用于上传缓存兼容，不是表单定义版本。
- Tc 图表直接查询 `tc_results`，迁移后必须保留等价固定字段和索引。
- Conditions 改名和本文全部目标均未实现，不能写入 Overview 作为当前事实。

## 2. 决策：MaterialState 挂载模块

**决策**：API 使用 `property_modules[]`，模块由稳定 `module_code` 区分。首批注册四个模块。

**理由**：若把每个模块做成 `MaterialState` 的固定顶层字段，每增加模块都要修改 API 类型和所有调用方；
统一模块容器更符合“按需插拔”，同时仍能让 UI 按模块展示。

**边界**：这里的“插件”是数据定义和组件注册，不是下载并执行第三方代码。新增模块需要受控注册和
发布定义，不能绕过后端校验。

## 3. 决策：统一 PropertyRecord 物理存储

**决策**：新建 `property_records` 统一保存 Tc 和其他物性。固定列保存核心查询字段，`payload_json`
保存受版本化 Schema 约束的扩展字段。

**理由**：模块和记录类型都需要动态扩展。如果上层统一、底层仍为每种记录分表，则每个新增记录类型
仍要开发专用映射、证据表和查询。统一记录表能让扩展主要落在定义层，同时 Tc 的值、方法、代表标记
继续使用固定列和数据库索引。

**备选方案**：保留 `tc_results` 专用表，只统一 API。该方案迁移风险较低，但长期保留两套结果存储、
证据连接和映射分支，与本次 Schema 驱动扩展目标不一致，因此不采用。

**拒绝方案**：把计算、实验和所有方法字段都塞进一张宽表。Conditions 继续独立，方法特有字段进入
受校验 JSON，避免大量固定空列。

## 4. 决策：Conditions 是一次确定执行

**决策**：`calculation_conditions` 与 `experimental_conditions` 分别表示一次计算运行和一次实验测量。
来自同一次过程的多条记录共享 `condition_key`。

**理由**：仅按软件、网格或实验方法判断“同一条件”会错误合并不同输入参数的结果。mu_star=0.10 与
0.15 即使其他设置一致，也必须是两次不同的 Conditions。

**组级校验**：定义的 `group_rules` 可声明同组唯一输入、互斥记录和必要配套关系。后端在完整材料状态
上校验，前端只负责提前提示。

## 5. 决策：Tc 记录类型与具体方法分离

**决策**：`record_type` 使用 `predicted_tc` 或 `measured_tc`，`method_code` 保存具体预测或测量方法。

**理由**：预测/测量决定 Conditions 大类，具体方法决定动态字段。常规/非常规超导分类不参与单条 Tc
的字段选择。

例如：

```text
predicted_tc + allen_dynes -> 计算 Conditions + Allen-Dynes 扩展字段
measured_tc + resistivity  -> 实验 Conditions + 电阻测量判据字段
```

## 6. 决策：不可变版本化 FormDefinition

**决策**：`FormDefinition` 使用 `definition_key + version` 标识，发布后不可变，并用 `target_kind`
区分模块、物性记录和两类 Conditions。JSON Schema 管数据规则，UI Schema 管控件和顺序，组级规则
管同一 Conditions 下多条记录的组合。

**理由**：若直接修改现有定义，历史记录会在没有数据变化时突然变成非法。记录绑定具体版本后，新旧
定义可以并存，升级也能成为明确、可审计的动作。

**安全边界**：只支持声明式 Schema 子集，不执行表达式代码或远程脚本。超级管理员发布定义，后端是
最终校验权威。

**备选方案**：所有方法字段继续硬编码。它的约束简单，但每次扩展都需要发版，无法满足用户目标。

## 7. 决策：论文内材料所有权

**决策**：`ChemicalSystem` 和 `Superconductor` 归属于论文 revision，唯一约束缩小到论文 revision。

**理由**：业务希望每篇论文保留自己研究的 LaH10 记录和解释，修改论文 A 不影响论文 B。跨论文搜索
使用规范化化学式和组成聚合，不使用共享主键。

**迁移影响**：旧共享材料需按实际引用它的论文 revision 复制，并重连 MaterialState。只给表增加
`paper_id` 而不拆旧共享行不能满足隔离要求。

## 8. 决策：结构限定为论文内引用

**决策**：本 Feature 只要求记录可选引用同论文 revision、同 MaterialState 的 `StructureModel`。

**理由**：此前 #90 增加的跨论文规范结构身份与动态物性表单不是同一个交付目标，也与“不自动跨论文
共享材料”的新边界不一致。跨论文结构查重或推荐需要独立 Feature 重新定义科学等价和生命周期。

## 9. 决策：分阶段迁移

**决策**：采用 Expand、Copy、Reconcile、Read switch、Write switch、Observe、Contract 七阶段。

**理由**：MySQL DDL 不能可靠地与所有数据回填一起整体事务回滚。先复制和对账、后切换、最后删旧表，
可以在每个稳定点恢复，也能先比较新旧查询结果。

对账不能只比较总行数，还要比较论文 revision、材料状态、记录类型、数值、单位、Conditions、Evidence
和代表 Tc。缺失 Evidence 进入报告，不伪造。

## 10. 已知风险

- 动态 Schema 过强会成为另一种编程语言，因此必须限制关键字和规则表达能力。
- JSON 扩展字段不适合频繁统计；字段成为核心查询条件时必须迁移为固定列。
- 论文内复制材料会增加记录数，但换来清晰的数据所有权；跨论文搜索需要依赖规范化索引。
- 模块分类可能存在交叉语义；同一事实只能存一条，UI 通过关联展示，不能复制权威值。
- 当前 #90 涉及模型、迁移、表单、详情和图表，实施必须按阶段完成，不能一次删掉旧表。
