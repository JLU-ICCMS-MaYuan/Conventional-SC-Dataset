# 技术研究：论文级 Material family 多选分类

**GitHub Issue**：[#79](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/79)

**日期**：2026-09-02

## R1：使用版本化关联表

- **决策**：新增 `paper_material_families(paper_id, paper_revision, material_family_id)`。
- **理由**：保留目录外键和多对多查询能力；复合外键绑定论文当前 revision，并可沿 #76 的 `ON UPDATE CASCADE` 升版。
- **备选方案**：在 `papers` 增加 JSON 数组；拒绝，因为无法保证目录引用完整性。仅用 `paper_id`；拒绝，因为分类将脱离现有科学数据版本约束。
- **证据**：`material_states`、`paper_files` 等实体已经使用 `(paper_id, paper_revision)` 绑定当前内容版本。

## R2：迁移先聚合后删除旧列

- **决策**：以 `SELECT DISTINCT paper_id, paper_revision, material_family_id FROM material_states WHERE material_family_id IS NOT NULL` 回填关联，再删除 `material_states.material_family_id`。
- **理由**：相同项自然去重，不同项全部保留，且不需要修改审核状态。
- **备选方案**：只保留第一项或将冲突论文退回 pending；均已被产品决策否定。
- **证据**：现有测试明确存在同论文多个状态对应不同 family。

## R3：降级遇到多 family 时拒绝

- **决策**：downgrade 先恢复状态列；若任一论文关联多个 family，则抛出错误并保留新表，不执行破坏性降级；至多一项时再回填每个状态并删除关联表。
- **理由**：旧模型每个状态只能承载一个 family，无法准确恢复论文级多个 family 的归属。
- **备选方案**：任选第一项复制到所有状态；拒绝，因为会静默丢失 family。
- **证据**：项目已有迁移在无法安全恢复旧约束时拒绝 downgrade 的模式。

## R4：草稿契约使用 `paper.material_families[]`

- **决策**：上传草稿放在既有 `paper` 对象；管理员科学草稿请求在顶层使用同名 `material_families[]`，材料状态不含 `material_family`。
- **理由**：上传表单的 Paper type 已在 `paper` 对象；管理员端接口当前将 `paper_type` 作为校验上下文放在科学草稿顶层，继续沿用其结构。
- **备选方案**：在每个状态复制论文列表；拒绝，因为重新制造多个事实来源。
- **证据**：`UploadTaskEditor` 直接维护 `draft.paper.paper_type`，`MaterialStatesEditor` 被两条编辑路径共享。

## R5：批准时一次解析整篇论文的 family

- **决策**：Go 批准请求接受论文级列表，按目录 ID/别名/新名称逐项解析、去重后整体替换 `paper_material_families`，分类快照也保存论文级列表。
- **理由**：目录创建只能发生在批准事务中；整体替换与当前科学数据审核语义一致。
- **备选方案**：提交时由 Python 创建正式目录；拒绝，违反现有审核门槛。
- **证据**：#51 当前由 `applyPaperClassifications` 在批准事务中创建目录和快照。

## R6：AI 汇总阶段聚合状态候选

- **决策**：提示词目标契约直接生成论文级 `material_families[]`；兼容已有或缓存模型输出时，把各状态 `material_family` 提取、去重到论文级并从状态中删除。
- **理由**：新请求走主契约，有限兼容防止在部署切换期间丢失已有候选。
- **备选方案**：永久保留状态级输入；拒绝，会让旧所有权继续扩散。
- **证据**：现有上传管线已有显式归一化阶段和契约版本控制。

## R7：复用现有多选自动完成组件

- **决策**：在 `UploadTaskEditor` 和 `AdminPaperEditPage` 的论文级区域，以 `ClassificationAutocomplete multiple` 编辑列表；从 `MaterialStatesEditor` 删除单选控件和“复制到同材料状态”的 family 逻辑。
- **理由**：KISS/DRY；现有组件已处理目录搜索、双语显示和自由输入。
- **备选方案**：新增专用 MaterialFamilyMultiSelect；拒绝，功能重复。
- **证据**：More type labels 已使用同一组件的多选模式。

## R8：统计把 family 作为论文级筛选标签

- **决策**：family 条件使用 `EXISTS` 查询论文关联；命中后返回该论文全部材料结果。无 family 条件时不连接关联表。
- **理由**：新模型不再保存具体状态到 family 的归属；`EXISTS` 可以支持论文多标签，同时避免关联表 JOIN 使未筛选总计重复。
- **备选方案**：按 family JOIN 后对结果去重；拒绝，因为聚合和分页更容易产生重复。继续保留状态级映射；拒绝，违反已确认的数据所有权。
- **证据**：用户确认 Material family 是论文级筛选标签，同论文可命中多个标签。
