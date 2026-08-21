# 技术研究：全新空库的单代论文血缘

## 决策 1：保留五表职责边界

**决策**：不合并 `papers`、`paper_files`、`paper_chunks`、`paper_evidences` 和
`paper_review_events`。

**理由**：五表分别是主实体、原始文件、可重建文本、证据快照和不可变审核事件，行粒度和
生命周期不同。

## 决策 2：`paper_files.stored_path` 是唯一文件路径来源

**决策**：目标 `papers` 不含 `source_file_path`，全部正文和附件路径只存于 `paper_files`。

**理由**：一篇论文可以有多个文件，单路径字段无法表达真实基数，双写又必然漂移。

## 决策 3：草稿可无 main，提交/审核恰好一个

**决策**：数据库以生成列唯一约束保证同论文至多一个 main；提交和审核事务检查至少一个。

**理由**：跨行“至少一个”不能由普通 CHECK 表达，但“至多一个”可以由 MySQL 唯一约束可靠保护。

## 决策 4：只保留当前一代 Chunk 和 Evidence

**决策**：`paper_revision` 用于一致性检查，不进入允许多代并存的唯一键。重新分块删除并替换
论文当前 Evidence/Chunk。

**理由**：用户明确反对多代存储，认为会扩大存储并使后台代码混乱。

**备选方案**：历史 Evidence 固定旧 Chunk。拒绝，因为 RAG、搜索和审核会同时存在多个权威代。

## 决策 5：Evidence 直接引用 Chunk 并保留快照

**决策**：`paper_evidences.paper_chunk_id` 必填，同时保留 quote、章节和页码；
不再重复保存 `paper_file_id + chunk_index`。

**理由**：稳定外键防止编号漂移，快照保留审核时看到的原文。

## 决策 6：组合外键保护论文 revision

**决策**：文件、Chunk、Evidence 均携带 `paper_id + paper_revision`，通过组合外键阻止串线。

**理由**：Python、Go 和脚本都可能写库，只靠某一服务层校验不够。

## 决策 7：重新分块先失效批准，再替换索引

**决策**：重分块开始即递增 `content_revision`、清空 `approved_revision` 并回到 `pending`；
MySQL 在事务内替换，Qdrant 先删除论文旧 points 再写新 points。

**理由**：旧批准不能覆盖新的证据定位；向量失败时保持 pending 可阻止半成品公开。

## 决策 8：审核事件记录 revision 且限制删除

**决策**：`paper_review_events` 记录 `paper_revision`；论文和审核者外键均使用限制删除语义，
事件更正通过追加而非修改。

**理由**：审核事件承担审计与贡献统计，不能因论文删除消失，也不能失去被审核版本。

## 决策 9：Schema 与物理文件处理分开

**决策**：本 Feature 当前只建立空库 Schema 和 ORM；文件写入、Qdrant 编排与 API 在后续
集成 Issue 实现。

**理由**：用户明确当前只负责 MySQL 表重构；把应用切换混入会扩大本次范围。

## 决策 10：修复 fresh Alembic 链而非依赖 `create_all`

**决策**：在 `0005` 修改 `paper_chunks` 前，由基础 migration 明确创建该表；新增 #33 revision
只处理目标论文血缘约束。

**理由**：SQLite/开发时 `create_all()` 会掩盖 Alembic 缺表，真实空 MySQL 必须独立成功。
