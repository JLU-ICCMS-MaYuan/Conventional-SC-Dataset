# 快速验收：上传任务分层清理与待审核快照生命周期

## 1. 运行专项测试

```bash
cd /home/mayuan/code/SC-Wiki
pytest -q \
  tests/01_decentralized_uploading/test_issue35_cleanup_lifecycle.py \
  tests/01_decentralized_uploading/test_issue35_duplicate_contract.py
```

预期：提交、审核、到期、幂等、MySQL fail-closed 和 duplicate 契约全部通过。

## 2. 运行上传回归

```bash
pytest -q tests/01_decentralized_uploading
```

预期：全部测试通过，无正式文件误删。

## 3. 迁移旧状态

```bash
python -m backend.scripts.migrate_upload_task_states
python -m backend.scripts.migrate_upload_task_states --apply
python -m backend.scripts.migrate_upload_task_states
```

预期：首次 dry-run 列出旧任务；apply 只更新目标状态；第二次 dry-run 待迁移数量为 0。

## 4. 提交清理验收

提交一个包含正文和附件的 ready 任务后验证：

- Redis state、draft 和用户索引成员不存在；
- 处理 RQ Job 不存在；
- `review_artifacts/{task_id}` 只剩精简 `result.json`；
- `upload_PDFs/{task_id}`、组合 Markdown 和分文件 Markdown 仍存在；
- Paper、PaperFile、PaperChunk 和 PaperEvidence 可查询。

再次提交同一 task_id，预期返回相同 paper_id。

## 5. 审核清理验收

- pending 时管理员能读取快照；
- pending 决定不删除；
- approved/rejected 事务成功后快照删除；
- 人工制造 revision 不一致时读取返回 409；
- 删除接口重复调用保持成功。

## 6. 未提交到期验收

分别构造 failed、duplicate、cancelled，运行到期清理后验证任务目录、两类 Markdown、
review_artifacts、RQ Job 和 duplicate candidate 均不存在。模拟数据库异常和永久认领时，
上述正式文件保持存在且清理被延期。

## 7. 部署验证

先确认开发 MySQL 已执行 #33 Schema 迁移，`papers.content_revision` 以及 `paper_files`、
`paper_chunks`、`paper_evidences` 的 `paper_revision` 字段存在。随后重建 Python API 与 Worker，
核对镜像、契约版本和 Redis 旧状态数量。部署代码必须对应 Git 可复现工作树；若仍包含未提交
diff 或数据库仍停留在旧 Schema，明确报告部署未完成，不关闭 Issue。
