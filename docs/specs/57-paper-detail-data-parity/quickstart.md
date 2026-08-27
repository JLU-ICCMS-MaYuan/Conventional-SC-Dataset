# 验收指引：论文详情数据一致性

**Feature**：[spec.md](spec.md)

**日期**：2026-08-27

## 前置条件

- dev 栈位于 `/home/mayuan/work/SC-Wiki-docker`，compose 文件 `dev.yaml`，服务名 `goserver`、`frontend`。
- **Go 与前端改动生效都需重建镜像**：代码经 `COPY` 打进镜像而非 bind mount，`restart` 不会加载工作区改动。
- **Go 测试需要 gcc 与预热模块缓存**：本机无 `go`；`golang:1.25` 无法联网拉模块；`scwiki-goserver-test-runner` 缺 gcc 而 `go-sqlite3` 需要 cgo。使用 `scwiki-auth-test-cgo:latest`（同时具备两者）。
- 论文 4（DOI 10.1073/pnas.1704505114）是验收基准数据，其 `review_status='pending'`，需以上传者或管理员身份查看。

## 自动化门槛

```bash
docker run --rm -v /home/mayuan/code/SC-Wiki/goserver:/src -w /src \
  -e GOPROXY=off -e CGO_ENABLED=1 \
  scwiki-auth-test-cgo:latest sh -c 'go test ./... -count=1'
```

不要加 `-e GOFLAGS=-mod=mod`：它会顺带改写 `go.mod` 的 `// indirect` 标记，在工作树里留下与本次任务无关的变更。

```bash
cd /home/mayuan/code/SC-Wiki/frontend && npm run test:upload-ui && npx tsc --noEmit
```

预期：Go 四个包（`scwiki/server`、`handlers`、`middleware`、`models`）全部 `ok`；前端既有用例全通过；`tsc` 无输出。

修复前基线：Go 四包同样全绿——既有测试对本 Feature 的缺陷完全无感（`TestPublicQueriesRequireApprovedPapers` 用 `DryRun` 只断言 SQL 文本含 `review_status`，对「表不存在」无感知）。因此新增测试必须用真实插入，见 [research.md](research.md) D8。

## 部署

```bash
cd /home/mayuan/work/SC-Wiki-docker && docker compose -f dev.yaml build goserver frontend \
  && docker compose -f dev.yaml up -d goserver frontend
```

## 场景 1：Tc 与计算上下文可见（US1，FR-001/FR-002，SC-001）

```bash
docker compose -f /home/mayuan/work/SC-Wiki-docker/dev.yaml exec -T mysql \
  sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scwiki -N -e "
    SELECT tc_value_k FROM tc_results WHERE paper_id=4;
    SELECT lambda_ep, mu_star FROM calculation_contexts WHERE paper_id=4 AND lambda_ep IS NOT NULL;" 2>/dev/null'
```

预期输出 `274.00000000`、`2.56000000 0.10000000`。

浏览器以上传者或管理员身份打开论文 4 详情，或直接请求接口。

**预期**：响应的 `material_states[0].tc_results` 含 `tc_value_k=274`；`calculation_contexts` 含 `lambda_ep=2.56`、`mu_star=0.1`（另有 1 条全 NULL 的记录，同样返回）。

**修复前对照**：两个键都不存在，Tc 与 λ 无从显示。

## 场景 2：压强区间与空间群可见（US1，FR-003/FR-004，SC-002）

**预期**：`material_states[0]` 含 `pressure_value_gpa=250`、`pressure_min_gpa=200`、`pressure_max_gpa=null`、`pressure_raw="above 200 GPa"`、`reported_space_group_symbol="Fm-3m"`、`reported_space_group_number=225`。

**关键**：`pressure_max_gpa` 必须是 `null` 而非 0 —— 这是 #54 确立的单臂区间语义，「无上限」不等于「上限为 0」。

**修复前对照**：材料状态只有 9 个字段，#54 的入库成果对用户完全不可见。

## 场景 3：物性名称非空且无恒零值字段（US1/US2，FR-005/FR-006，SC-001/SC-003）

**预期**：`key_properties[0].name` 为 `thermodynamic stability`（非空字符串），`value_number=200`、`unit="meV/atom"`。

响应中**不得出现**以下键：`superconductor_id`、`name_note`、`pressure_gpa`、`temperature_k`、`condition_json`、`is_primary`、`superconductor_type`、`article_type`、`source_label`、`structure_text`、`structure_format`。

**判定恒零值的方法**：改动库中该物性的 `name_raw` 后重新请求，`name` 应随之变化。若某字段无论库中如何变化都保持同一值，即为恒零值字段。

**修复前对照**：`name` 恒为空字符串，`pressure_gpa`/`temperature_k` 恒 null，`is_primary` 恒 false。

**已知数据事实**：`value_raw` 为 `"0"` 而 `value_number` 为 200，两者不一致。这是写入侧历史数据问题（属范围外），接口如实返回两者，不是本 Feature 的缺陷。

## 场景 4：记录搜索不再恒空（US3，FR-007/FR-008，SC-004）

```bash
curl -s -X POST http://localhost:8080/api/papers/search/records \
  -H 'Content-Type: application/json' -d '{"elements":[],"limit":5}'
```

```bash
docker compose -f /home/mayuan/work/SC-Wiki-docker/dev.yaml logs --tail=100 goserver 2>&1 \
  | grep -c "key_properties' doesn't exist"
```

**预期**：第二条命令输出 `0`（不再查询已废弃的表）。

**关于非空结果**：当前 dev 库 `review_status='approved'` 计数为 0，因此结果仍会是空数组——这是数据状态而非缺陷。「返回非空结果」由 Go 测试内构造已批准数据验证；如需在 dev 环境确认，先审核通过一篇论文再重试。

**修复前对照**：日志每次请求都报 `Error 1146: Table 'scwiki.key_properties' doesn't exist`，且 `SearchPage` 依赖该接口，用户看到的搜索恒为空。

## 场景 5：管理员物性修改能落库（US3，FR-009，SC-005）

1. 以管理员身份打开论文审核页，修改某物性的名称（`name_raw`）与数值。
2. 保存后重新读取该物性。

**预期**：修改已生效。提交的 payload 只含真实列字段。

**修复前对照**：新建路径经 `gorm:"-"` 静默丢弃，更新路径会拼出不存在的列名；管理员以为改了，实际未落库。

## 场景 6：既有行为无回归（FR-010，SC-006）

1. **权限**：匿名请求论文 4（`pending`）应仍被拒绝；上传者与管理员可看。#56 确立的逐篇鉴权不因新增数据段而改变。
2. **图表分组编辑**：`ChartGroupEditor` 中物性条目的压强与类型应显示真实值而非空，布局不变。
3. **分享页**：物性表格的数值、单位、条件列正常显示，布局不变。
4. **空数据论文**：无 Tc 结果的论文，`tc_results` 为 `[]`，页面不报错、不显示异常空行。

## 验收对照

| 场景 | 覆盖 |
|---|---|
| 1 | FR-001、FR-002、SC-001 |
| 2 | FR-003、FR-004、SC-002 |
| 3 | FR-005、FR-006、SC-001、SC-003 |
| 4 | FR-007、FR-008、SC-004 |
| 5 | FR-009、SC-005 |
| 6 | FR-010、SC-006 |
