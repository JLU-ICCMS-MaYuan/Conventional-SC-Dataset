# 端到端验证：论文物理删除

**Feature**：[spec.md](spec.md) ｜ **契约**：[contracts/paper-deletion.md](contracts/paper-deletion.md)

## 前置条件

- dev 栈运行中（compose 文件在仓库外：`~/work/SC-Wiki-docker/dev.yaml`）
- 已有 `superadmin` 账号
- 改动 Go 代码后必须重建镜像；镜像不挂载源码，改文件不会生效

```bash
cd ~/work/SC-Wiki-docker
docker compose -f dev.yaml build goserver python
docker compose -f dev.yaml up -d goserver python worker
# 重启被 nginx 代理的服务后必须重启 nginx：
# 它只在启动时解析一次 upstream 主机名，容器换 IP 后会一直 502
docker compose -f dev.yaml restart frontend
```

## 步骤 1：上线前在真实 MySQL 演练删除顺序

**不可跳过**。单元测试用 SQLite，无法完全代表 MySQL 的复合外键行为。
把 `<ID>` 换成目标论文 id，整段在事务内执行并回滚，不改动数据：

```sql
START TRANSACTION;
DELETE FROM tc_result_evidences WHERE paper_id=<ID>;
DELETE FROM structure_model_evidences WHERE paper_id=<ID>;
DELETE FROM superconductor_property_evidences WHERE paper_id=<ID>;
DELETE FROM tc_results WHERE paper_id=<ID>;
DELETE FROM superconductor_properties WHERE paper_id=<ID>;
DELETE FROM calculation_contexts WHERE paper_id=<ID>;
DELETE FROM experimental_contexts WHERE paper_id=<ID>;
UPDATE structure_models SET parent_structure_id=NULL WHERE paper_id=<ID> AND parent_structure_id IS NOT NULL;
DELETE FROM structure_models WHERE paper_id=<ID>;
DELETE FROM material_state_structure_families WHERE material_state_id IN (SELECT id FROM material_states WHERE paper_id=<ID>);
DELETE FROM material_states WHERE paper_id=<ID>;
DELETE FROM paper_evidences WHERE paper_id=<ID>;
DELETE FROM paper_chunks WHERE paper_id=<ID>;
DELETE FROM paper_files WHERE paper_id=<ID>;
DELETE FROM paper_review_events WHERE paper_id=<ID>;
DELETE FROM papers WHERE id=<ID>;
ROLLBACK;
```

**预期**：无 `Error 1451`。若报错，说明外键依赖已变化，需重新查
`information_schema.KEY_COLUMN_USAGE` 并同步修正 `cascadeDeleteInDB` 与 plan.md。

## 步骤 2：调用真实 API 删除

```bash
TOKEN=$(curl -sS -X POST http://localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"<超管邮箱>","password":"<密码>"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -sS -i -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/admin/papers/<ID>
```

**预期**：`HTTP 200` 且 `{"message":"已删除"}`。

## 步骤 3：验证全库无残留（SC-001）

不要只抽查几张表。遍历所有含 `paper_id` 的表：

```sql
SELECT CONCAT('SELECT "', TABLE_NAME, '" t, COUNT(*) n FROM ', TABLE_NAME,
              ' WHERE paper_id=<ID> HAVING n>0 UNION ALL ')
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA='scwiki' AND COLUMN_NAME='paper_id';
```

把结果拼成一条查询执行（末尾 `UNION ALL` 换成 `;`）。

**预期**：零行返回。

再确认共享目录数据未被牵连：

```sql
SELECT COUNT(*) FROM superconductors;  -- 应与删除前一致
```

## 步骤 4：验证外部清理（需已发布的论文）

`pending` 论文从未发布到 Qdrant/Neo4j，两库本就为空，**测不出清理是否真的生效**，
只能覆盖「目标不存在时不误报失败」。要完整验证，需一篇已 `approved` 且已发布的论文：

```bash
# Qdrant
docker compose -f dev.yaml exec -T python python -c "
from backend.rag.vectordb import _get_client, COLLECTION_NAME
from qdrant_client.models import Filter, FieldCondition, MatchValue
print(_get_client().count(collection_name=COLLECTION_NAME,
  count_filter=Filter(must=[FieldCondition(key='paper_id', match=MatchValue(value='<ID>'))]),
  exact=True).count)"

# Neo4j
docker compose -f dev.yaml exec -T python python -c "
from backend.rag.tools.neo4j import _driver
with _driver().session() as s:
    print(s.run('MATCH (p:Paper {paper_id:<ID>}) RETURN count(p) AS n').single()['n'])"
```

**预期**：两者均为 `0`。

## 步骤 5：前端交互

1. 以超管登录，进入超级管理员工作台
2. 点击「论文审核」卡片
3. 单篇删除：点垃圾桶图标 → 确认 → 论文从列表消失
4. 批量删除：勾选多篇 → 「批量删除」→ 确认
   - 全部成功提示「批量删除完成」
   - 部分失败提示「N 篇删除失败（ID: ...），其余已删除」
     （后端返回 `206`，前端按 `failed_ids` 判定，不可仅凭 `response.ok`）
5. 刷新页面确认已删除的论文不再出现

## 自动化测试

```bash
# Go：含外键强制开启下的级联删除用例
docker run --rm -v "$PWD/goserver":/app -v go-mod-cache:/go/pkg/mod -w /app \
  -e GOPROXY=https://goproxy.cn,direct golang:1.25 go test ./...

# 前端
cd frontend && npx vitest run --config ../vitest.config.ts
```
