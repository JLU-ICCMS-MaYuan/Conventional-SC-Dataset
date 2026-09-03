# 实施计划：引用图谱运行恢复与历史回填

**GitHub Issue**：[ #82](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/82)

**Spec**：[spec.md](spec.md)

## 实施顺序

1. 将 Go 管理员图谱标记路由参数统一为 `:id`，同步 handler 参数读取。
2. 在 `goserver/main_test.go` 增加同一 router 的注册回归测试。
3. 实现 `backend/scripts/backfill_citation_references.py`：显式选择目标、逐论文调用
   GROBID、逐论文持久化、汇总结果并以退出码报告失败。
4. 运行 Python、Go、前端定向测试和生产构建；提交代码与文档。
5. 受控执行开发库 Alembic 迁移，验证版本、表和 API 链路。
6. 验证 GROBID 后回填现有论文 `id=9`，再确认图谱 API 返回正确的孤立节点或真实边。

## 回填命令契约

```bash
python backend/scripts/backfill_citation_references.py --paper-id 9
python backend/scripts/backfill_citation_references.py --all-approved
python backend/scripts/backfill_citation_references.py --all-approved --dry-run
```

- `--dry-run` 只列出符合范围的论文及主 PDF 存在性，不调用 GROBID、不写数据库。
- 未指定目标时拒绝运行，避免不经意扫描全库。
- `--paper-id` 和 `--all-approved` 互斥。
- 实际运行时，一篇论文对应一次 GROBID 调用和一次独立数据库事务。

## 验证矩阵

| 风险 | 验证 |
| --- | --- |
| Gin 路由冲突再次导致启动 panic | 新的 Go 路由注册测试 + `go run` 临时健康检查 |
| 回填选错论文或重复写入 | Python 定向测试：范围、幂等性、失败隔离 |
| 迁移误连测试库 | 迁移前输出数据库名、版本和表；只允许目标为 `scwiki` |
| GROBID 不可用时产生假边 | mock GROBID 失败测试 + 实际命令非零退出 |
| Vite 仍代理到不可用服务 | `curl :5173/api/knowledge-graph/overview`，断言非超时 |
