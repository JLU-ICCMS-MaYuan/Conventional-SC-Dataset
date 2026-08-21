# 快速验收：全新空库的单代论文血缘

## 前置条件

- 只使用可销毁的隔离空 MySQL 8.4。
- `DATABASE_URL` 不得指向两个现有数据库。
- 数据库初始无业务数据。
- `0006` 是用户名 revision，#33 使用其后的 `0007`。

## 1. 运行静态模型测试

```bash
cd /home/mayuan/code/SC-Wiki
python3 -m pytest \
  tests/02_maintenance_and_verification/test_issue33_paper_lineage.py -q
cd goserver
go test ./models -run PaperLineage
```

预期：论文 revision、main 生成列、Chunk 唯一、Evidence 组合外键和 Review Event 外键契约通过。

## 2. 从完全空库升级

```bash
cd /home/mayuan/code/SC-Wiki
alembic upgrade head
alembic current
```

预期：

- `0005` 修改 `paper_chunks` 时该表已存在；
- 迁移链只有一个 head；
- `papers`、`paper_files`、`paper_chunks`、`paper_evidences`、
  `paper_review_events` 达到目标列和约束；
- `papers.source_file_path` 不存在。

## 3. 文件和 Chunk 约束

验证：

1. 草稿无 main 可以保存。
2. 同论文首个 main 可保存，第二个 main 被拒绝。
3. 非法 role 被拒绝。
4. 同文件重复 `chunk_index` 被拒绝。
5. 不同文件相同 `chunk_index` 可保存。
6. Chunk 的论文/revision 与 File 不一致时被拒绝。

## 4. Evidence 与审核事件约束

验证：

1. Evidence 必须提供有效 `paper_chunk_id`。
2. Evidence 跨论文或跨 revision 时被拒绝。
3. Evidence 含 quote、章节和页码快照，不含重复归属列。
4. Review Event 必须引用有效论文和审核者，并保存被审核 revision 的历史快照。
5. revision 1 审核后可把论文升至 revision 2，旧事件仍保留且不随当前 revision 改写。
6. 孤立事件写入和有审核事件论文的物理删除均被拒绝。

## 5. 现有数据 guard

仅在另一可销毁测试库中插入任意论文或文件记录，再尝试目标 revision。

预期：迁移在重构 DDL 前失败，明确说明该 revision 只支持空业务库。

## 6. 空库可逆性与回归

```bash
alembic downgrade 20260821_0006
alembic upgrade head
python3 -m pytest tests/02_maintenance_and_verification -q
cd goserver && go test ./...
git diff --check
```

预期：只在空测试库完成。没有隔离 MySQL 时必须报告集成测试未执行，不能用 SQLite 结果替代。

## 7. 后续业务验收边界

RAG/Qdrant 集成 Issue 必须另外验证：

- 重分块开始即整篇 `pending`；
- 旧当前代删除后才递增 revision，并在同一 MySQL 事务中写入全部新当前代；
- MySQL 只剩当前 Evidence/Chunk；
- Qdrant 先删旧 points 后写当前 revision；
- 搜索、RAG 和审核 Evidence 使用同一 revision；
- 重建完成后重新审核一次整篇论文。
