# 实施计划：论文附件晶体结构提取

**GitHub Issue**：[#49](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/49)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

在 #46 的新科学草稿和提交主链路上增加结构候选子流程：扩展上传文件契约；对原生 CIF/POSCAR
执行 ASE 读取；对 PDF 文本和可恢复表格提取结构字段；用 pymatgen 做确定性空间群展开和
原胞/惯用胞派生；用 ASE 统一校验和 CIF/POSCAR 写出；将候选、来源和用户确认状态放入草稿；
提交时只把已确认候选写入 #32 的 `StructureModel` 和 Evidence 连接；前端继续用 3Dmol.js，
默认展示惯用胞并提供四种导出组合。

## 技术上下文

- **语言与版本**：Python 3.12、TypeScript/React 18、MySQL 8.4、Redis/RQ
- **主要依赖**：FastAPI、SQLAlchemy 2、PyMuPDF、ASE >= 3.22、pymatgen >= 2023.9、MUI、3Dmol.js、pytest、Vitest
- **数据存储**：原始文件与 Markdown 保存在文件系统；候选保存在 Redis 草稿和审核快照；正式结构、Evidence 与论文 revision 保存在 MySQL
- **测试体系**：`backend/tests` pytest；`tests/01_decentralized_uploading` 前端/上传集成；隔离 MySQL Alembic 与 Go ORM 测试
- **目标平台**：Docker Compose Web 服务与 RQ Worker；浏览器端 3Dmol.js
- **性能目标**：结构候选处理按文件和候选线性增长；单篇论文不发起外部材料数据库请求；公开导出只读取已批准当前 revision
- **约束**：依赖 #46；不迁移旧结构表；原始文件不可变；论文级审核是唯一公开边界；不包含 OCR/图片识别
- **规模范围**：单上传任务一个正文和多个附件；每篇论文可有数十个材料状态和结构候选

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| `AGENTS.md` | 简体中文 Spec；不读取 Journal；修改后只提交本任务文件 | 所有产物中文；本 Feature 不涉及 Journal；提交时按路径暂存 | 通过 |
| #24 | 正文与附件属于同一上传任务，证据保留文件和页码 | 候选来源引用 `file_id`、角色、页码和表格/quote | 通过 |
| #32 | 科学实体绑定论文 revision，Evidence 不跨 revision | 提交服务重用 `StructureModel` 与连接表外键 | 通过 |
| #46 | 新草稿使用 `material_states[]`，旧契约只在边界兼容 | 候选挂在材料状态引用下，不写旧 `KeyProperty` | 通过 |
| #49 | 缺失/冲突不猜测，用户确认后才入库 | `blocked/needs_review` 状态和提交前二次校验 | 通过 |
| 权限 | approved 当前 revision 才公开 | 预览和导出共用论文权限与 revision 检查 | 通过 |

## Feature 文档结构

```text
docs/specs/49-pdf-crystal-structure-extraction/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/structure-candidates-api.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
backend/ingest/upload_contracts.py       # 文件后缀和任务 DTO
backend/ingest/upload_jobs.py            # 每文件抽取、候选编排和草稿合并
backend/ingest/pdf_extractor.py          # 可搜索文本/表格证据入口
backend/ingest/structure_extractor.py    # 新增：字段识别、候选构造和来源定位
backend/services/structure_candidates.py # 新增：ASE 校验、标准化、等价比较和导出
backend/services/scientific_drafts.py    # #46 事务写入扩展
backend/api/upload_tasks.py              # 草稿读写和确认操作
backend/api/papers.py                    # approved 结构预览/导出权限门
backend/models.py                        # 复用 #32 目标实体和 Evidence 关系
frontend/src/components/UploadTaskEditor.tsx       # 候选确认和导出控制
frontend/src/components/StructureViewer3D.tsx       # 默认惯用胞预览
frontend/src/components/StructureCandidatePanel.tsx # 新增：候选证据与状态
frontend/src/lib/paperProcessing.ts                 # DTO/schema 版本
backend/tests/test_structure_candidates.py          # 新增：结构领域单测
backend/tests/test_upload_jobs.py                   # 上传编排回归
backend/tests/test_structures_api.py                # 权限/导出 API
tests/01_decentralized_uploading/structure-candidates.test.tsx # 新增：前端流程
```

## 结构选择

PDF 机械提取保持现有来源文件和页码边界；结构识别独立为 `structure_extractor.py`，避免把
晶体学规则塞进通用论文字段提示词。`structure_candidates.py` 是唯一结构科学边界，负责
ASE/pymatgen 组合、容差、四种派生输出和失败语义。上传编排只负责调用、合并和保存草稿；API
不复制解析或权限规则。公开结构路由复用现有论文权限函数，不暴露 Redis 或服务器路径。

## 需求到设计映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001–FR-003 / US1 | `upload_contracts.py`、`structure_candidates.py` | 附件契约、合法/非法 ASE 夹具 |
| FR-004–FR-010 / US2 | `pdf_extractor.py`、`structure_extractor.py` | 完整坐标、Wyckoff 展开、缺失/冲突测试 |
| FR-005、FR-017、FR-020 / US2 | 候选条件键与等价合并器 | 多压力、多来源和冲突夹具 |
| FR-011、FR-021 / US4 | 标准化与导出服务 | 四组合重新读取和等价测试 |
| FR-013–FR-016 / US3 | 草稿 DTO、#46 scientific draft writer | 前端确认、事务回滚集成 |
| FR-022–FR-023 / US5 | 论文结构预览/下载 API | approved/pending/rejected 权限矩阵 |
| FR-018–FR-019 | 错误 DTO 与全链路测试 | 文件级错误、回归和 E2E |

## 阶段与依赖

1. 先冻结候选 DTO、状态、容差、标准化策略和 API 契约。
2. 扩展附件契约及结构科学服务，完成原生附件和派生输出。
3. 接入 PDF 结构证据抽取与对称展开，完成多结构合并。
4. 接入 #46 草稿、前端确认和 3Dmol.js 默认惯用胞预览。
5. 接入 #46 单事务正式写入及 approved 公开预览/导出。
6. 执行单测、上传集成、隔离 MySQL、前端回归、quickstart 和文档回写。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|---|---|---|
| 候选与来源集合 | PDF 与附件可能重复或冲突，必须合并但不丢证据 | 一个来源一条结构会重复入库或丢失冲突 |
| pymatgen 对称展开 + ASE 校验 | Wyckoff 操作不能手写，ASE 是现有读写边界 | LLM 直接生成 CIF 无法证明科学一致 |
| 原胞/惯用胞双表示 | 用户预览识别和 VASP 计算的需求不同 | 只保留一种表示会损失互操作性或原始语义 |
| 草稿确认与事务写入分离 | 解析可失败且候选需人工确认，正式库必须原子提交 | 解析阶段直接写库会污染审核数据 |
