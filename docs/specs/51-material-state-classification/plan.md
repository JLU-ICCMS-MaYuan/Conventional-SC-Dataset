# 实施计划：材料状态多维分类目录与统一审核

**Issue**：[#51](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/51)

## 摘要

在现有条件化科学数据模型上增加材料家族和结构家族目录、别名、建议、证据和审计；Python 上传链路把 LLM/旧草稿名称确定性归一到每个材料状态并持久化，Go 管理链路提供目录读取、材料状态分类编辑、建议审核和超级管理员治理。前端以共享 MUI `Autocomplete` 统一上传、管理员审核和论文详情的中文分类体验。

## 技术上下文

- **后端**：Python 3、FastAPI、SQLAlchemy 2 async、Alembic、MySQL；Go 1.25、Gin、GORM。
- **前端**：React 19、TypeScript 5.6、MUI 7、Vite 5、Vitest/Testing Library。
- **现有主路径**：Python 负责上传任务、LLM 草稿和科学实体提交；Go 负责公开论文、管理员审核和超级管理员工作台。
- **数据边界**：分类属于 `material_states` 当前论文 revision；正式搜索和图表调用方本轮不切换。
- **兼容边界**：旧草稿只读转换；旧数据库迁移默认 dry-run，不自动操作生产库。

## 质量门

| 来源 | 约束 | 设计响应 | 状态 |
| --- | --- | --- | --- |
| Issue #51 / FR-001–007 | 多维分类且不得按元素猜家族 | 明确目录、字段和服务器端元素计算 | 通过 |
| Issue #51 / FR-008–013 | 数据库候选、权限和审计 | Go 目录/治理 API + 事务审计 | 通过 |
| Issue #45 / FR-001–002 | 后台保留证据作用域 | 内部证据保留 scope，普通 DTO 删除引用材料 | 通过 |
| Issue #46 / 数据模型 | 新数据写入 MaterialState 主路径 | Python 持久化直接写新表，拒绝旧 KeyProperty 分类 | 通过 |
| Issue #50 / 空间群边界 | 结构家族不能替代空间群 | 两套字段和关系独立 | 通过 |
| AGENTS.md | Issue/Spec 双向关联、简体中文、自动提交 | #51 和本目录双向链接，全部文档中文 | 通过 |
| PRODUCT.md / design.md | 生产力工具、Material 组件、状态透明 | 共享 MUI 组件和明确 pending/error 状态 | 通过 |

## 实施架构

### 1. Schema 与共享约束

新增 Alembic revision `20260825_0012_material_state_classification.py`，创建目录、别名、材料状态关联、建议、证据和审计表，为 `material_states` 增加三个字段、seed 初始目录，并从目标 Schema 删除 `papers.referenced_materials`。SQLAlchemy 与 GORM 模型同步。

数据库负责外键、枚举 Check、别名唯一和唯一主结构家族；应用层负责维度与处理结果 FK 一致性、合并事务和角色权限。

### 2. Python 上传和归一化

新增 `backend/services/classification_catalog.py`，集中实现名称规范化、目录加载、别名解析、旧值白名单、草稿选择校验和元素种类数计算。上传分段/汇总契约改为每个材料状态输出材料家族、结构家族和材料维度；引用工作候选只保留内部作用域。

`GET draft` 在返回前转换旧顶层 `sc_type` 并移除旧字段；`PUT draft` 和 submit 拒绝旧字段。提交事务写入正式关系或待审核建议、分类证据，不把未审核名称写成目录项，也不写论文级引用材料。

### 3. Go 目录与管理员治理

新增 `goserver/handlers/classifications.go`：

- 公开读取启用目录；
- 管理员读取/映射建议和更新论文当前 revision 的材料状态分类；
- 超级管理员治理目录、批准建议和读取审计；
- 论文批准前检查材料家族、元素种类数和未解决建议。

旧 `key_properties.superconductor_type` 从管理员更新白名单和 UI 移除，不再作为新分类写入路径。

### 4. 前端共享交互

新增 `frontend/src/lib/classifications.ts` 和 `frontend/src/components/ClassificationAutocomplete.tsx`。组件加载数据库目录，用规范名与别名精确定位，使用 `freeSolo` 表达待确认名称，并覆盖加载、失败、空目录、正式选择和待审核状态。

上传编辑器把论文级分类移到每个材料状态，增加材料维度、元素种类数和结构家族；管理员审核和论文详情使用相同类型与中文显示。超级管理员工作台增加分类目录治理面板，不新增独立视觉体系。

### 5. 迁移与兼容

Alembic 只建立目标 Schema 和 seed，不从当前新库猜测历史类型。`backend/scripts/migrate_material_classifications.py` 接受显式旧数据库连接，默认 dry-run；按 `paper_id + superconductor_id + pressure` 唯一匹配并输出 applied/skipped/ambiguous/conflict 报告，只有 `--apply` 才写入。

旧草稿兼容以再次保存为退出条件；新请求不长期接受旧格式。

### 6. 文档收敛

在 #23、#45、#46 和 #50 的冲突文档顶部加入后续修订说明，不改写其历史完成记录。实现和验证完成后使用项目 Overview 维护流程更新数据模型、PDF 摄入和管理员治理当前事实。

## 源代码结构

```text
backend/
├── api/rag.py
├── ingest/scientific_drafts.py
├── ingest/upload_jobs.py
├── models.py
├── services/classification_catalog.py
├── scripts/migrate_material_classifications.py
└── tests/

goserver/
├── handlers/admin.go
├── handlers/classifications.go
├── handlers/classifications_test.go
├── main.go
└── models/models.go

frontend/src/
├── components/ClassificationAutocomplete.tsx
├── components/ClassificationGovernancePanel.tsx
├── components/UploadTaskEditor.tsx
├── components/PaperEditView.tsx
├── lib/classifications.ts
├── lib/paperProcessing.ts
├── pages/AdminPage.tsx
└── pages/SuperAdminPage.tsx

alembic/versions/
└── 20260825_0012_material_state_classification.py
```

## 测试策略

- **Python 单元/契约**：规范化向量、目录/别名解析、元素数量、旧草稿转换、旧格式拒绝、引用作用域过滤。
- **Python 集成**：提交事务生成 MaterialState、Proposal、Evidence 和结构家族关联；待确认论文可提交但不能批准。
- **Schema**：fresh MySQL 表、外键、Check、seed、唯一主项、upgrade/downgrade 元数据。
- **Go**：公开目录输出、管理员/超级管理员权限、别名冲突、建议终态、合并事务、审计和批准门。
- **前端**：数据库候选展开、别名定位、待确认状态、目录失败、每状态分类、结构多选和中文显示。
- **端到端**：旧草稿读取保存、AI 中文名归一、上传提交、管理员映射、论文批准。

## 风险与控制

- **跨语言规范化漂移**：Python/Go 共用固定输入输出测试向量，目录唯一性由数据库兜底。
- **双写旧字段**：新 API 明确拒绝 `sc_type`，Go 管理员白名单删除兼容字段。
- **未确认数据被批准**：批准动作在同一数据库事务检查当前 revision 分类完整性。
- **目录合并破坏历史**：禁止物理删除被引用项；合并迁移关系、设置目标并追加审计。
- **工作树并发修改**：逐文件检查当前 diff，只暂存本 Feature 文件，不包含 `.agents/skills`、`.gitignore` 或 `.vite/` 等已有更改。

## 不必要复杂度说明

本 Feature 不建设通用分类树、搜索筛选、压力等级、模糊匹配或完整结构本体。两套目录及共享前端选择组件足以覆盖确认需求；建议和审计属于正式目录可治理的必要复杂度。
