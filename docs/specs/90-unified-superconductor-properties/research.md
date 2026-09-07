# 研究记录：MaterialState 模块化物性与动态表单

## 1. 当前事实

- 当前材料按规范组成在全库复用；`superconductors.composition_key` 和 `formula_normalized` 是全局唯一。
- 当前 Tc 位于 `tc_results`，其他物性位于 `superconductor_properties`，lambda、omega_log、mu_star
  仍可位于计算 Context 字段。
- 前端表单固定编码 Tc 方法与字段，Schema version 只用于上传缓存兼容，不是表单定义版本。
- Tc 图表直接查询 `tc_results`，迁移后必须保留等价固定字段和索引。
- Conditions 改名和本文全部目标均未实现，不能写入 Overview 作为当前事实。

**证据**：`backend/models.py` 当前定义全局唯一的 `ChemicalSystem`/`Superconductor`、两类 Context、
`TcResult` 与 `SuperconductorProperty`；`goserver/handlers/stats.go` 直接查询 `tc_results`；
`docs/overview/02_Decentralized_Maintenance_and_Verification/domain-model-and-schema.md` 记录相同现状。

## 2. 决策：MaterialState 挂载模块

**决策**：API 使用 `property_modules[]`，模块由稳定 `module_code` 区分。首批注册四个模块。

**理由**：若把每个模块做成 `MaterialState` 的固定顶层字段，每增加模块都要修改 API 类型和所有调用方；
统一模块容器更符合“按需插拔”，同时仍能让 UI 按模块展示。

**边界**：这里的“插件”是数据定义和组件注册，不是下载并执行第三方代码。新增模块需要受控注册和
发布定义，不能绕过后端校验。

**备选方案**：继续为每类物性增加 `MaterialState` 顶层字段。该方案初始简单，但每个模块都会修改
上传、管理、详情和 Go 契约，不满足 Issue 的按需扩展目标。

**证据**：当前 `frontend/src/components/MaterialStatesEditor.tsx` 与 `backend/ingest/scientific_drafts.py`
分别固定理解各科学字段，现有变更触点已跨 Python、Go 和前端。

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

**证据**：`backend/models.py` 的 `TcResult` 已有稳定查询列和专用约束，而
`SuperconductorProperty` 提供通用数值表达；目标模型需要同时保留这两类能力。

## 4. 决策：Conditions 是一次确定执行

**决策**：`calculation_conditions` 与 `experimental_conditions` 分别表示一次计算运行和一次实验测量。
来自同一次过程的多条记录共享 `condition_key`。

**理由**：仅按软件、网格或实验方法判断“同一条件”会错误合并不同输入参数的结果。mu_star=0.10 与
0.15 即使其他设置一致，也必须是两次不同的 Conditions。

**组级校验**：Conditions 自身绑定定义版本；该定义的 `group_rules` 可声明同组唯一输入、互斥记录和
必要配套关系。后端在完整材料状态上校验，前端只负责提前提示。记录定义不重复持有跨记录规则，避免
同组记录使用不同定义版本时出现规则来源冲突。

**身份规则**：Conditions 定义的 `identity_rules` 声明决定性 Conditions 字段、输入物性、normalizer
与 cardinality。同一键内出现两个规范值时拒绝；键由用户确认的运行或测量产生，不从内容计算，输入
相同的重复运行不会被合并。

**备选方案**：把规范内容哈希直接作为 `condition_key`。该方案会合并输入相同的重复运行，丢失“这是
两次执行”的事实，因此只把规范化用于同组冲突校验，不用于身份生成。

**证据**：Issue #90 要求不同决定性输入建立不同 Conditions，同时允许一个 Conditions 关联多条性质；
`backend/models.py` 当前已经用 Context 实体而不是参数哈希表达一次运行或测量。

## 5. 决策：Tc 记录类型与具体方法分离

**决策**：`record_type` 使用 `predicted_tc` 或 `measured_tc`，`method_code` 保存具体预测或测量方法。

**理由**：预测/测量决定 Conditions 大类，具体方法决定动态字段。常规/非常规超导分类不参与单条 Tc
的字段选择。

例如：

```text
predicted_tc + allen_dynes -> 计算 Conditions + Allen-Dynes 扩展字段
measured_tc + resistivity  -> 实验 Conditions + 电阻测量判据字段
```

**备选方案**：继续用一个 `tc_method` 同时表达预测/测量大类和具体方法。该方案会让每个新增方法重复
携带 Conditions 类型分支，因此保留两个正交字段并由定义约束其组合。

**证据**：Issue #84 已修复 `tc_method=experimental` 与计算 Context 残留，说明大类、具体方法和
Conditions 类型必须在同一校验入口保持一致。

## 6. 决策：不可变版本化 FormDefinition

**决策**：`FormDefinition` 使用 `definition_key + version` 标识，发布后不可变，并用 `target_kind`
区分模块、物性记录和两类 Conditions。JSON Schema 管数据规则，UI Schema 管控件和顺序，组级规则
管同一 Conditions 下多条记录的组合。

**理由**：若直接修改现有定义，历史记录会在没有数据变化时突然变成非法。记录绑定具体版本后，新旧
定义可以并存，升级也能成为明确、可审计的动作。

**安全边界**：只支持声明式 Schema 子集，不执行表达式代码或远程脚本。常规定义管理由超级管理员
执行，自定义性质提升由管理员按第 10 节直接发布；后端是最终校验权威。

**备选方案**：所有方法字段继续硬编码。它的约束简单，但每次扩展都需要发版，无法满足用户目标。

**定义身份**：方法特有定义把方法代码写入 `definition_key`，例如
`record.superconductive_properties.predicted_tc.allen_dynes`。版本只用于同一方法定义的演进，避免把
Allen-Dynes v2 与 Eliashberg v1 放进同一个版本序列。

**升级与回滚**：升级预览返回目标快照和校验和，应用保存不可变前后快照；回滚创建反向事件。两种写入
都校验论文 revision、当前记录校验和和前序事件，防止覆盖后续编辑。

**备选方案**：原地覆盖记录定义版本且只写操作日志。该方案无法可靠恢复被转换或清除的字段，也无法
判断回滚是否会覆盖后续修改，因此不采用。

**证据**：#90 要求旧记录保持原定义版本且升级显式执行；现有论文编辑已经以 content revision 管理
并发和历史，定义升级必须服从同一边界。

## 7. 决策：论文内材料所有权

**决策**：`ChemicalSystem` 和 `Superconductor` 归属于论文 revision，唯一约束缩小到论文 revision。

**理由**：业务希望每篇论文保留自己研究的 LaH10 记录和解释，修改论文 A 不影响论文 B。跨论文搜索
使用规范化化学式和组成聚合，不使用共享主键。

**迁移影响**：旧共享材料需按实际引用它的论文 revision 复制，并重连 MaterialState。只给表增加
`paper_id` 而不拆旧共享行不能满足隔离要求。
复制使用论文内唯一约束的两张影子材料表，避免撞到旧材料表的全局唯一键；停写切换时才更名并显式
重连外键。影子表与旧新 ID 映射是本次迁移暂存物，不增加第二套长期材料身份。

**备选方案**：保留全局材料主键并增加论文关联表。该方案仍让材料本体的修改和删除跨论文传播，与
Issue 确认的论文内所有权不一致。

**证据**：`backend/models.py` 当前对 `composition_key` 和 `formula_normalized` 使用全局唯一约束，
`MaterialState` 直接引用共享 `superconductors.id`，迁移必须复制实体才能改变所有权。

## 8. 决策：结构限定为论文内引用

**决策**：本 Feature 只要求记录可选引用同论文 revision、同 MaterialState 的 `StructureModel`。

**理由**：此前 #90 增加的跨论文规范结构身份与动态物性表单不是同一个交付目标，也与“不自动跨论文
共享材料”的新边界不一致。跨论文结构查重或推荐需要独立 Feature 重新定义科学等价和生命周期。

**备选方案**：建立全局规范结构身份并允许不同论文引用。该方案需要候选匹配、等价判定、来源失效和
跨论文生命周期规则，超出当前 Issue。

**证据**：当前 Issue 的范围外事项明确排除跨论文结构推荐；`StructureModel` 已由同 revision 复合
外键归属于 `MaterialState`。

## 9. 决策：分阶段迁移

**决策**：采用 Expand、Copy、Reconcile、Read switch、Write switch、Observe、Contract 七阶段。
在 Read switch 前进入有界停写窗口，完成最终增量 Copy 与 Reconcile；读取验证通过后立即切写并解除
停写。旧写入路径不会通过兼容视图长期写入新表。

**理由**：MySQL DDL 不能可靠地与所有数据回填一起整体事务回滚。先复制和对账、后切换、最后删旧表，
可以在每个稳定点恢复，也能先比较新旧查询结果。

对账不能只比较总行数，还要比较论文 revision、材料状态、记录类型、数值、单位、Conditions、Evidence
和代表 Tc。缺失 Evidence 进入报告，不伪造。

**备选方案**：复制完成后保持旧写入开放并直接先切读。该方案会让复制后的新写入只存在于旧模型，
新读取看不到这些数据；临时双写又会扩大一致性风险，因此通过停写隔离切换过程。非事务 DDL 期间
返回明确维护错误，依照检查点恢复；不宣称所有切换步骤构成单个数据库事务。

**证据**：Issue #90 明确要求 Read switch 先于 Write switch，且禁止长期双写；MySQL DDL 与数据回填
不能作为一个整体事务回滚。

## 10. 决策：自定义性质保留与管理员直接提升

**决策**：用户在现有模块通过已发布通用模板录入自定义性质，随论文审核保留；管理员可以独立决定
将已批准的自定义性质直接提升为全站通用定义，无需超级管理员二次批准。

**理由**：论文里的新性质不应被系统词表的完整程度阻塞。数据保留与全站字段复用是两个动作，管理员
已有论文科学事实审核职责，可以确认定义名称、类型、单位和模块并留下审计。

**方案**：复用 `PropertyRecord` 和 `FormDefinition`，只增加论文内 custom_property_key、核心字段 Schema
以及提升事件，不引入独立提案审批系统。提升通过服务端受限模板发布普通物性定义，源记录继续绑定原
自定义模板；常规定义管理和历史版本升级继续使用已有超级管理员权限。

**备选方案**：要求先发布完整全站定义才能批准自定义记录，会阻塞论文贡献；要求提升经过超级管理员
二次审批，与用户确认的权限相悖；任意 JSON 键直接写入扩展字段则无法保证类型、单位和前后端一致。

**证据**：本轮用户明确确认“管理员就能决定是否进一步提升为全站通用性质定义”；
`backend/api/auth_routes.py` 的 `_is_admin` 已将 admin 与 superadmin 纳入管理员集合，
`docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md` 记录既有论文审核边界。
本节是待实现设计，不能提前写入 Overview。

## 11. 已知风险

- 动态 Schema 过强会成为另一种编程语言，因此必须限制关键字和规则表达能力。
- JSON 扩展字段不适合频繁统计；字段成为核心查询条件时必须迁移为固定列。
- 论文内复制材料会增加记录数，但换来清晰的数据所有权；跨论文搜索需要依赖规范化索引。
- 模块分类可能存在交叉语义；同一事实只能存一条，UI 通过关联展示，不能复制权威值。
- 当前 #90 涉及模型、迁移、表单、详情和图表，实施必须按阶段完成，不能一次删掉旧表。
