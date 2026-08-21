# 空库论文血缘与单代完整性契约

## 空库边界

1. 本 Feature 只为全新空 MySQL 建立 Schema。
2. 两个现有数据库及历史文件、Chunk、Evidence、审核事件和 Qdrant points 不迁入。
3. 检测到现有业务数据时，目标 revision 必须在破坏性 DDL 前失败。
4. 不提供历史映射、兼容读取、双写、回填或收缩观察窗口。

## 文件权威契约

1. 唯一正式路径来源是 `paper_files.stored_path`。
2. 目标 `papers` 不含 `source_file_path`。
3. 文件角色只允许 `main/supplementary/attachment`。
4. 同一论文最多一个 main；提交和审核时必须恰好一个。
5. 同一路径或 SHA-256 不作为跨论文合并依据。

## 单代 Chunk 契约

1. `paper_chunks.paper_file_id` 必填。
2. `(paper_file_id, chunk_index)` 唯一，不以 revision 放宽。
3. File、Chunk 和 Paper 必须属于同一 revision。
4. MySQL、搜索、RAG 和 Qdrant 只使用论文当前 revision。
5. revision 是一致性标记，不是保留多代内容的版本键。

## Evidence 契约

1. `paper_evidences.paper_chunk_id` 必填。
2. Evidence、Chunk 和 Paper 必须属于同一 revision。
3. Evidence 保留 quote、章节、页码和字段路径快照。
4. Evidence 不重复保存 File 或 chunk index 归属。
5. 跨论文、跨 revision 或失效 Chunk 引用必须被数据库拒绝。

## 重新分块契约

1. 在一个 MySQL 事务内先清空 `approved_revision` 并置 `pending`，暂不递增 revision。
2. 同一事务按外键依赖顺序删除旧当前代 Evidence 连接、科学内容、Evidence、Chunk 和 File。
3. 旧当前代删除完成后，仍在同一事务内递增 revision 并写入全部新当前代内容。
4. 不保留旧 Chunk/Evidence 内容作为历史版本。
5. Qdrant 必须先删除该论文旧 points，再写入带当前 revision 的新 points。
6. 任一阶段失败时论文保持 `pending`；重建完成后必须重新审核整篇论文。
7. 公开查询不得读取 revision 不匹配或索引不完整的内容。

## Review Event 契约

1. 每个事件必须引用有效论文和审核者，并记录被审核 revision 的历史快照。
2. `paper_id`、`reviewer_user_id` 均为 `ON DELETE RESTRICT`。
3. 状态只允许 `pending/approved/rejected`。
4. `request_id` 保持唯一幂等。
5. 事件不可原位修改或级联删除；更正通过追加事件。
6. `paper_revision` 不与论文当前 revision 建立组合外键，论文升版不得修改或删除旧事件。

## ORM 与验证契约

- fresh Alembic 在 `0005` 前必须已经创建 `paper_chunks`。
- Alembic、SQLAlchemy、GORM 与 MySQL 的列、空值、外键和索引一致。
- SQLite 测试不能替代空 MySQL `upgrade head`。
- 当前落地只实现 Schema/ORM；RAG/Qdrant 编排由后续集成 Issue 按本契约实现。
