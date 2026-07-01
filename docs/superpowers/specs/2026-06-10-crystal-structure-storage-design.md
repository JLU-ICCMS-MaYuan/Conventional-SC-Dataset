# 晶体结构存储设计

## 1. 背景

当前系统已经围绕 `chemical_systems`、`superconductors`、`papers` 和 `superconductor_records` 建立了文献与超导数据点模型。`superconductor_records` 中已有 `pressure_gpa`、`space_group_symbol`、`space_group_number` 和 `crystal_structure` 等字段，但这些字段主要用于描述、筛选和展示超导记录，不适合保存 CIF 或 POSCAR 结构文件正文。

新增 ASE 晶体结构可视化后，需要为真实晶体结构建立独立存储能力。该能力应支持同一化学式、同一空间群在不同压强下保存不同结构，同时在页面展示时避免同一化学式和空间群下重复展示多个压强结构。

## 2. 目标

- 支持保存 CIF 和 POSCAR 两种晶体结构格式。
- 结构真实存储粒度为“化学式 + 空间群 + 压强”。
- 同一存储粒度下允许存在多个版本，默认使用最新审核通过版本。
- 可视化默认展示粒度为“化学式 + 空间群”，展示该组的代表结构。
- 保持 `superconductor_records` 继续承担超导物理数据点职责，避免把结构文件正文塞入记录表。

## 3. 非目标

- 不在本设计中支持更多结构格式，例如 XYZ、CIF 压缩包或 VASP 输出目录。
- 不改变现有元素检索、文献审核和首页图表的核心业务规则。
- 不要求一次性迁移历史数据中的 `crystal_structure` 字符串为真实结构文件。
- 不把 Alexandria 或 HTSC2025 的外部结构自动写入主业务表，除非后续导入流程明确执行。

## 4. 表设计

新增表名为 `superconductors_structures`。

建议核心字段：

| 字段 | 用途 |
|---|---|
| `id` | 结构主键 |
| `superconductor_id` | 关联 `superconductors.id`，用于确定化学式和元素组成 |
| `pressure_gpa` | 结构对应压强，是结构身份的一部分 |
| `space_group_symbol` | 空间群符号 |
| `space_group_number` | 空间群编号 |
| `structure_format` | 结构格式，只允许 `cif` 或 `poscar` |
| `structure_text` | 原始 CIF/POSCAR 文本 |
| `structure_hash` | 基于规范化结构内容计算的哈希，用于识别重复结构 |
| `review_status` | 结构审核状态：`pending`、`approved`、`rejected` |
| `is_default` | 同一化学式 + 空间群 + 压强下的默认版本 |
| `source_type` | 来源类型，例如 `paper_upload`、`admin_upload`、`import`、`alexandria`、`htsc2025` |
| `source_label` | 来源说明，例如 DOI、外部材料 ID 或导入批次 |
| `created_by_user_id` | 上传或导入发起用户，关联 `users.id` |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

不建议在该表中冗余保存 `chemical_formula` 和 `formula_normalized`。这两个字段已经由 `superconductor_id -> superconductors` 提供，查询代表结构时可通过 join 获取。

## 5. 与现有表的边界

`superconductors` 继续表示一个规范化化学式，是结构表的上级实体。

`superconductor_records` 继续表示论文或导入来源中的超导数据点，承载压强、Tc、稳定性、计算参数、图表展示标记等信息。该表中的 `crystal_structure` 仍可作为结构类型或空间群描述字段存在，不保存 CIF/POSCAR 正文。

`superconductors_structures` 表只负责真实结构文件、结构版本、结构来源和默认结构选择。它可以通过 `superconductor_id + space_group + pressure_gpa` 与一条或多条 `superconductor_records` 建立业务对应关系。

如果后续需要更强的一对一追踪，可在 `superconductor_records` 增加可空 `structure_id` 外键指向 `superconductors_structures.id`。该外键不是第一阶段必须项，因为当前需求强调结构可复用。

## 6. 唯一性与版本规则

结构的业务分组键为：

```text
superconductor_id + space_group_symbol/space_group_number + pressure_gpa
```

同一分组键下允许存在多个版本。版本处理规则：

- 新上传结构默认进入 `pending`。
- 管理员审核通过后，最新审核通过版本成为该分组的默认结构，即 `is_default=true`。
- 同一分组下旧的默认结构保留历史，但设置为 `is_default=false`。
- 审核拒绝的结构保留记录，但不参与默认展示。
- `structure_hash` 相同的结构可提示重复，但不强制拒绝，因为不同来源可能需要保留出处。

## 7. 代表结构展示规则

可视化入口默认按以下展示粒度折叠：

```text
superconductor_id + space_group_symbol/space_group_number
```

代表结构选择规则：

1. 只从 `review_status='approved'` 的结构中选择。
2. 优先选择 `is_default=true` 的结构。
3. 同一化学式和空间群下按 `pressure_gpa ASC` 排序。
4. 压强相同或缺少压强时按 `created_at DESC` 排序。
5. 返回第一条作为默认可视化结构。

这样可以满足“同一个空间群的同一个化学式，每个压强都存一个结构；展示时只展示该化学式和空间群的第一个结构”的需求。

## 8. API 设计

建议新增结构 API 分组：

```text
POST /api/structures/
GET  /api/structures/by-record/{record_id}
GET  /api/structures/representative?formula=...&space_group=...
GET  /api/structures/{structure_id}/raw
```

`POST /api/structures/` 用于上传 CIF/POSCAR。后端应读取 `structure_format` 和 `structure_text` 或上传文件内容，并使用 ASE 解析校验。解析失败时返回 400，不写入数据库。

`GET /api/structures/by-record/{record_id}` 用于从超导记录查找匹配结构。匹配顺序为：如果记录存在显式 `structure_id`，直接返回；否则按记录的 `superconductor_id + space_group + pressure_gpa` 查找默认结构。

`GET /api/structures/representative` 用于页面默认可视化展示。该接口按化学式和空间群返回代表结构。

`GET /api/structures/{structure_id}/raw` 用于下载或直接查看原始 CIF/POSCAR 文本，响应的 media type 可根据格式分别设置为 `chemical/x-cif` 或 `text/plain`。

## 9. 校验与元数据

上传时后端使用 ASE 做以下校验：

- 格式必须是 `cif` 或 `poscar`。
- 结构文本必须能被 ASE 解析。
- 解析得到的元素组成应能映射到目标 `superconductor`。
- 如果用户提供空间群字段，解析结果与用户字段不一致时应给出提示或进入待审核状态。
- 文件大小应设置上限，避免异常大文件影响接口。

解析成功后可计算并保存以下派生信息，第一阶段可以按需要选择是否落库：

- 原子数
- 元素列表
- 晶胞参数
- 体积
- 规范化结构哈希

## 10. 文档与导入导出影响

实现该能力时需要同步更新：

- `docs/business-paper-ingestion.md`：说明文献上传如何携带或关联晶体结构。
- `docs/business-overview.md`：补充晶体结构存储与可视化在模块关系中的位置。
- `backend/export_data.py` 和 `backend/import_data.py`：扩展 JSON 导入导出格式，加入 `superconductors_structures`。
- Alembic 迁移：创建新表并补充必要索引。

## 11. 测试建议

- 单元测试：CIF/POSCAR 格式校验、ASE 解析失败、哈希计算、默认结构选择。
- API 测试：上传结构、审核通过后默认结构切换、代表结构查询、原始结构下载。
- 回归测试：现有文献列表、组合页筛选、首页图表不受结构表新增影响。
- 导入导出测试：包含结构数据的 JSON 可完整导出并重新导入。

