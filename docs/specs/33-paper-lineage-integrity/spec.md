# Feature 规格：全新空库的单代论文文件、Chunk 与 Evidence

**GitHub Issue**：[#33](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/33)

**创建日期**：2026-08-21

**状态**：已确认，实施中

## 背景与目标

`papers`、`paper_files`、`paper_chunks`、`paper_evidences` 和 `paper_review_events` 分别承担
论文主档、原始文件、检索切片、证据快照和审核事件，职责不同，应继续分表。当前问题是文件
路径存在两个权威来源、Evidence 没有稳定 Chunk 外键、Chunk 可出现多代漂移，以及审核事件
缺少论文外键。

本 Feature 只为全新空 MySQL 建立目标 Schema，并同步 SQLAlchemy/GORM。每篇论文在数据库、
RAG、搜索和审核证据中只保留同一当前代，不保存历史 Chunk 内容。两个现有数据库及其历史
文件、Chunk、Evidence 和审核事件不迁入、不回填、不修改。

## 用户场景与验收

### 用户故事 1：论文文件只有一个权威来源（优先级：P1）

维护者希望正文、补充材料和附件都从 `paper_files` 读取，不再让论文主表保存另一个路径。

**优先级理由**：文件身份是 Chunk、Evidence 和重新解析的共同根节点。

**独立验收**：目标 Schema 不含 `papers.source_file_path`；所有文件路径来自
`paper_files.stored_path`。草稿可暂时没有正文，可提交和可审核论文恰好一个 `role=main` 文件。

**验收场景**：

1. **假如**论文处于草稿阶段，**当**尚未上传正文，**那么**允许暂时没有 `main` 文件。
2. **假如**论文准备提交或审核，**当**验证文件清单，**那么**必须恰好一个 `main` 文件。
3. **假如**尝试为同一论文保存第二个 `main` 文件，**当**写入数据库，
   **那么**唯一约束拒绝该写入。

### 用户故事 2：RAG、搜索和 Evidence 使用同一代 Chunk（优先级：P1）

研究者希望搜索命中的文本、RAG 回答依据和审核时看到的 Evidence 永远来自论文同一当前代，
避免一个系统引用旧 Chunk、另一个系统引用新 Chunk。

**优先级理由**：多代并存会增加存储并让后台代码无法确定哪一代是权威。

**独立验收**：每个文件的当前 Chunk 以 `(paper_file_id, chunk_index)` 唯一；Evidence 必须
直接引用当前 Chunk；MySQL 和 Qdrant 都只保留论文当前 revision 的内容。

**验收场景**：

1. **假如**论文完成首次分块，**当**保存 Chunk 和 Evidence，
   **那么**二者属于同一 `paper_id + paper_revision`。
2. **假如**同一论文的不同文件都从 `chunk_index=0` 开始，**当**写入，
   **那么**各文件切片互不冲突。
3. **假如**Evidence 引用另一论文或旧 revision 的 Chunk，**当**写入，
   **那么**数据库拒绝关联。

### 用户故事 3：重新分块整体替换并重新审核（优先级：P1）

维护者重新分块时，希望旧 Chunk、旧 Evidence 和旧向量全部被当前代替换，不保留两个版本，
同时避免旧审核自动批准新内容。

**优先级理由**：重新分块会改变审核定位和检索内容，旧批准不能继续覆盖新一代。

**独立验收**：重新分块在一个受控流程中使论文 revision 递增并回到 `pending`，事务替换
MySQL Evidence/Chunk，删除论文旧 Qdrant points 后重建当前代；随后整篇论文重新审核。

**验收场景**：

1. **假如**论文已批准，**当**重新分块开始，**那么**论文立即失去公开资格并回到 `pending`。
2. **假如**MySQL 当前代替换失败，**当**事务回滚，**那么**不会留下新旧混合的 Chunk/Evidence。
3. **假如**MySQL 替换成功但向量重建失败，**当**查询公开内容，
   **那么**论文仍为 `pending`，不会公开不完整索引。
4. **假如**新索引完成并经管理员再次批准，**当**公开搜索或 RAG，
   **那么**只使用新批准 revision。

### 用户故事 4：审核事件具有稳定论文归属（优先级：P1）

管理员希望每次审核事件都明确记录审核的论文 revision，论文删除不能带走审计历史。

**优先级理由**：审核事件是一次整篇论文审核的证据，也是贡献统计的来源。

**独立验收**：审核事件必须引用有效论文和审核者，并把被审核 revision 保存为不可变历史
快照；`paper_review_events.paper_id` 使用 `ON DELETE RESTRICT`，历史 revision 不与论文
当前 revision 建立组合外键。

**验收场景**：

1. **假如**管理员审核论文当前 revision，**当**保存事件，
   **那么**事件记录该 revision 和审核决定。
2. **假如**事件引用不存在的论文，**当**写入，
   **那么**数据库拒绝。
3. **假如**论文已有审核事件，**当**尝试物理删除论文，
   **那么**数据库拒绝删除。
4. **假如**revision 1 已产生审核事件，**当**删除旧当前代内容并把论文升至 revision 2，
   **那么**升版成功且 revision 1 的审核事件仍完整保留。

### 用户故事 5：从空库建立完整血缘约束（优先级：P1）

维护者希望真正从空 MySQL 升级到 head，避免 SQLite `create_all()` 掩盖缺表。

**独立验收**：fresh Alembic 链在 `0005` 前已建立 `paper_chunks`；空库升级成功并得到目标五表
关系。已有业务数据的数据库触发空库 guard，不执行迁移或清理。

### 边界与异常场景

- 五张论文表保持独立，不通过 JSON 或合表简化。
- `paper_files.stored_path` 是唯一文件路径来源；目标模型不含旧路径兼容。
- 同一论文当前代最多一个 `main`；“至少一个”由提交/审核事务门检查。
- Evidence 继续保存 `field_path`、quote、章节和页码快照，不能只动态读取 Chunk。
- 不同文件的 `chunk_index` 可各自从 0 开始。
- Chunk、Evidence 和 Qdrant points 不保留多代内容；revision 只用于检测一致性。
- 审核事件不可修改；更正通过新增事件表达。
- 两个现有数据库的任何异常或孤儿数据均不在本 Feature 处理。

## 需求

### 功能需求

- **FR-001**：系统必须保持 `papers`、`paper_files`、`paper_chunks`、
  `paper_evidences` 和 `paper_review_events` 五表独立。
- **FR-002**：正式文件路径的唯一来源必须是 `paper_files.stored_path`；目标 `papers`
  不得包含 `source_file_path`。
- **FR-003**：`paper_files.role` 只允许 `main/supplementary/attachment`；同一论文当前代
  最多一个 `main`，可提交或可审核时必须恰好一个。
- **FR-004**：论文必须具有递增 `content_revision` 和可空 `approved_revision`；
  只有当前 revision 被批准时才可公开。
- **FR-005**：`paper_files`、`paper_chunks` 和 `paper_evidences` 必须属于明确且一致的
  `paper_id + paper_revision`。
- **FR-006**：`paper_chunks.paper_file_id` 必填；每个文件的
  `(paper_file_id, chunk_index)` 必须唯一。
- **FR-007**：`paper_evidences.paper_chunk_id` 必填，并以组合外键保证 Evidence、Chunk、
  Paper 和 revision 一致。
- **FR-008**：Evidence 必须保留 `field_path`、quote、章节、页码和创建时间快照；
  不再重复保存 `paper_file_id` 或 `chunk_index`。
- **FR-009**：每篇论文只保留当前一代 Chunk/Evidence；不得把 revision 作为允许多代内容
  并存的唯一键。
- **FR-010**：重新分块必须在一个 MySQL 事务内先使整篇论文 `pending` 并清空批准，按外键
  依赖顺序删除旧当前代 Evidence、科学内容、Chunk 和 File，再递增 revision 并写入新当前代；
  失败时不得留下新旧混合状态。
- **FR-011**：Qdrant 重建必须先按 `paper_id` 删除旧 points，再写入带当前 revision 的
  points；搜索和 RAG 只接受与 MySQL 当前 revision 一致的 points。
- **FR-012**：向量重建完成前论文不得恢复公开；重分块后必须重新执行一次整篇审核。
- **FR-013**：`paper_review_events.paper_id` 必须外键指向 `papers.id` 且
  `ON DELETE RESTRICT`；`reviewer_user_id` 同样必须有效。
- **FR-014**：每个审核事件必须记录被审核的 `paper_revision` 历史快照，但该字段不要求
  等于论文当前 revision；状态只允许 `pending/approved/rejected`，`request_id` 保持幂等唯一。
- **FR-015**：数据库必须阻止跨论文、跨 revision 的文件—Chunk—Evidence 关系。
- **FR-016**：Alembic 必须从完全空 MySQL 升级到单一 head；不得依赖
  `Base.metadata.create_all()` 补表。
- **FR-017**：本 Feature 的目标 revision 必须只接受空业务库；检测到已有业务数据时中止，
  不迁移、不回填、不删除。
- **FR-018**：SQLAlchemy、GORM、Alembic 和 MySQL 必须对五表的列、类型、外键、唯一约束
  和索引保持一致。

### 关键实体

- **论文主档**：出版元数据、当前 revision 与论文级审核状态。
- **论文文件**：当前 revision 的正文、补充材料或附件，是路径唯一来源。
- **文本切片**：当前 revision 中由一个文件产生的检索文本块。
- **字段证据**：直接引用当前 Chunk 的原文审核快照。
- **审核事件**：记录一次整篇论文 revision 审核的不可变事件。
- **Qdrant point**：MySQL Chunk 的可重建索引投影，不是第二个内容版本来源。

## 成功标准

- **SC-001**：目标 Schema 中 `papers.source_file_path` 列数量为 0，文件路径读取来源为
  `paper_files.stored_path`。
- **SC-002**：同一论文第二个 `main` 文件的数据库拒绝率为 100%；提交/审核时无 main 或
  多 main 的业务门拒绝率为 100%。
- **SC-003**：新 Evidence 的有效 `paper_chunk_id` 覆盖率为 100%，跨论文或跨 revision
  关联的数据库拒绝率为 100%。
- **SC-004**：每个文件的重复 `chunk_index` 写入拒绝率为 100%，不同文件相同编号可保存。
- **SC-005**：重分块完成后 MySQL Chunk、Evidence 与 Qdrant points 只存在当前 revision，
  旧代内容数量为 0。
- **SC-006**：重分块后的论文在重新审核前公开命中数为 0。
- **SC-007**：审核事件孤立写入和有审核事件论文的物理删除均被数据库拒绝。
- **SC-008**：隔离空 MySQL `alembic upgrade head` 成功，Python/Go 模型和 Schema 专项测试
  全部通过且不连接现有数据库。

## 假设与依赖

- #23 已确定论文审核状态为 `pending/approved/rejected`，#26 已确定提交清单恰好一个 main。
- #32 使用本 Feature 的论文 revision 和 Evidence 作为科学内容审核边界。
- 当前只落地空库 Schema 和 ORM；RAG/Qdrant 事务编排、API 切换和历史迁移进入后续 Issue。
- MySQL 是权威内容库，Qdrant 只保存可重建索引投影。

## 范围外事项

- 迁移两个现有数据库中的文件、Chunk、Evidence、审核事件或 Qdrant points。
- 保留或查询历史 Chunk/Evidence 内容版本。
- 在本次 Schema 落地中实现上传、RAG、搜索或审核 API 的业务切换。
- 修改分块算法、Embedding 模型或 Qdrant collection 结构。
- 合并五张论文表或物理删除历史数据库中的异常数据。

## 澄清记录

### 2026-08-21

- 问：五张论文表是否合并？→ 答：不合并，保持不同职责。
- 问：文件路径权威来源是什么？→ 答：只使用 `paper_files.stored_path`。
- 问：一篇论文需要几个 main 文件？→ 答：草稿可无；提交和审核时恰好一个。
- 问：RAG、搜索和审核 Evidence 是否可以使用不同代 Chunk？→ 答：不可以；只保留同一当前代。
- 问：重新分块如何处理批准？→ 答：整篇退回 `pending`，替换当前代并重建索引后重新审核。
- 问：历史数据是否迁入？→ 答：不迁入；本次只建立全新空库。
- 问：Q13/Q14 原题干不可恢复时如何处理？→ 答：不重复询问，按已确认的单代事务替换、
  `ON DELETE RESTRICT` 审计边界和空库原则保守实现。
