# 快速验证：审核编辑页补齐超导性质并支持完全编辑

**GitHub Issue**：[#76](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/76)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)　**Plan**：[plan.md](plan.md)

## 前置条件

```bash
make start
make status      # 确认 frontend / goserver / python / mysql 在运行
```

以管理员账号登录，进入超级管理员或管理员工作台的论文列表。

**依赖前提**：

1. Issue #74 的 i18n 基建须已就位（新增文案走双语字典）。
2. 外键级联链迁移已应用。核对方式：

```bash
mysql -h 127.0.0.1 -P 3307 -e "
SELECT rc.CONSTRAINT_NAME, rc.TABLE_NAME, rc.UPDATE_RULE, rc.DELETE_RULE
FROM information_schema.REFERENTIAL_CONSTRAINTS rc
WHERE rc.CONSTRAINT_SCHEMA=DATABASE()
  AND rc.TABLE_NAME IN ('paper_files','paper_chunks','paper_evidences','material_states')"
```

**预期**：4 条外键 `UPDATE_RULE=CASCADE`（`fk_paper_files_paper_revision`、`fk_paper_chunks_file_revision`、`fk_paper_evidences_chunk_revision`、`fk_material_states_paper_revision`），全部 `DELETE_RULE=RESTRICT`；`fk_paper_chunks_paper_revision` 与 `fk_paper_evidences_paper_revision` 两条已不存在。

**注意**：元数据核对不足以证明级联正确——多条 CASCADE 作用于同一子列的冲突在建表期不报错，只在运行时抛 1452。必须执行场景 5 的实际升版验证。

**测试数据准备**：需要至少一篇 `pending` 论文与一篇 `approved` 论文，且各含 2 个以上材料状态、每个材料状态下有 Tc 与普通物性。可用现有 `papers.id = 9`（Hg 文献，已批准）作为升版验证对象——**注意该论文升版后会暂时从社区图表消失**，这是预期行为。

**既有失败用例**：`tests/07_researcher_community_forum/news-feed.test.tsx` 有一个用例在干净 `HEAD` 上同样失败（`docs/local-dev.md` 已记录），不计入本 Feature 回归。

## 场景 1：数据可见性（US1、契约 C3）

先验证预加载补齐——这是其余场景的前提。

1. 直接请求详情接口。
   ```bash
   curl -s -H "Authorization: Bearer <token>" \
     http://127.0.0.1:8080/api/admin/papers/9 | python -m json.tool | head -60
   ```
   **预期**：`material_states[]` 的每一项含非空的 `tc_results`、`properties`、`structures`（若该材料状态确有这些数据）。改动前这三个键为空数组。
2. 打开该论文的编辑弹窗。
   **预期**：全部材料状态卡片可见，每张含化学式、材料家族、元素种类数、材料维度、超导类型、晶系、空间群符号与群号、压强。
3. 展开某张卡片。
   **预期**：其下的 Tc 列表（数值、方法、区间、代表性标记）、普通物性列表（名称、原始值、单位）、结构附件预览区都可见。
4. 打开一篇综述论文（无材料状态）的编辑弹窗。
   **预期**：显示无材料状态的空态提示，不报错。

## 场景 2：上传校对页不回退（US5，重构回归）

组件抽取后立刻验证上传主路径——这是 P1 底线。

1. 打开一个解析完成的上传任务校对页。
   **预期**：材料状态卡片的字段、折叠交互、AI 建议展示、结构候选面板与重构前完全一致。
2. 材料状态数超过 2 张时观察默认折叠。
   **预期**：仅第一张展开，其余折叠（既有规则）。
3. 清空某个材料状态的化学式后提交。
   **预期**：错误横幅显示并定位到出错卡片，滚动到可见区域。
4. 运行既有测试。
   ```bash
   scripts/run-tests.sh frontend
   ```
   **预期**：`tests/01_decentralized_uploading/` 下 upload-task-editor-classification、upload-task-editor-layout、submit-validation-feedback 等用例全部通过（SC-008）。

## 场景 3：待审核论文原地编辑（US2）

1. 打开一篇 `pending` 论文的编辑弹窗，修改某材料状态的压强值。
2. 为该材料状态新增一条 Tc（数值 4.2、方法选实验测量）。
3. 删除某条普通物性。
4. 保存后重新打开弹窗。
   **预期**：三项改动全部持久生效。
5. 检查论文版本与状态。
   ```bash
   mysql -h 127.0.0.1 -P 3307 -e \
     "SELECT id, content_revision, approved_revision, review_status FROM papers WHERE id = <pending_id>"
   ```
   **预期**：`content_revision` 与保存前相同，`approved_revision` 为 NULL，`review_status` 仍为 `pending`（FR-012）。
6. 修改某材料状态使压强区间 min 大于 max，保存。
   **预期**：保存被拒绝并提示压强区间错误；重新打开弹窗，数据仍是上一次成功保存的状态，未被破坏（FR-020）。
7. 把某篇综述论文的材料状态全部删除后保存。
   **预期**：保存成功（综述论文允许无材料状态）。

## 场景 4：结构附件补传（US3）

1. 在编辑弹窗中为某材料状态上传一个合法 CIF 文件。
   **预期**：上传后通过校验，在该材料状态下可预览结构。
2. 上传一个内容损坏的 CIF。
   **预期**：提示校验失败的具体原因，未写入数据。
3. 删除某个已有结构附件并保存。
   **预期**：该结构不再关联到材料状态。
4. 确认候选未直接落库。
   **预期**：上传后（保存前）查询 `structure_models` 无新增行——候选随保存动作一并落库（契约 C2）。

## 场景 5：已批准论文升版重审（US4）

这是本 Feature 风险最高的场景，逐步核对。

1. 记录升版前状态。
   ```bash
   mysql -h 127.0.0.1 -P 3307 -e \
     "SELECT content_revision, approved_revision, review_status FROM papers WHERE id = 9;
      SELECT COUNT(*) AS files FROM paper_files WHERE paper_id = 9;
      SELECT COUNT(*) AS chunks FROM paper_chunks WHERE paper_id = 9;
      SELECT COUNT(*) AS evidences FROM paper_evidences WHERE paper_id = 9;
      SELECT COUNT(*) AS states FROM material_states WHERE paper_id = 9"
   ```
2. 打开该已批准论文的编辑弹窗。
   **预期**：界面在保存前明确告知保存将升版并退回待审核，期间论文不对外公开（FR-017）。
3. 修改某材料状态的 Tc 数值并保存。
   **预期**：保存成功，提示论文已退回待审核；响应含 `revision_bumped: true`。
4. 核对版本字段。
   **预期**：`content_revision` 递增 1、`approved_revision` 为 NULL、`review_status` 为 `pending`（FR-013、SC-003）。
5. 核对血缘数据的级联更新。
   ```bash
   mysql -h 127.0.0.1 -P 3307 -e \
     "SELECT paper_revision, COUNT(*) FROM paper_files WHERE paper_id = 9 GROUP BY paper_revision;
      SELECT paper_revision, COUNT(*) FROM paper_chunks WHERE paper_id = 9 GROUP BY paper_revision;
      SELECT paper_revision, COUNT(*) FROM paper_evidences WHERE paper_id = 9 GROUP BY paper_revision;
      SELECT paper_revision, COUNT(*) FROM material_states WHERE paper_id = 9 GROUP BY paper_revision"
   ```
   **预期**：四张表全部行的 `paper_revision` 已是新版本号，行数与步骤 1 记录相同；旧版本号下无残留行。这些更新由外键 `ON UPDATE CASCADE` 自动完成——服务端只执行了一条 `UPDATE papers`（FR-014、SC-004）。
6. 未登录访问社区页与探索页。
   **预期**：该论文的数据点不出现在图表与检索结果中（FR-015、US4 场景 3）。
7. 以非管理员身份访问该论文详情。
   **预期**：无权查看（US4 场景 4）。
8. 以管理员身份查看新版本详情。
   **预期**：正文文件、文本切片、证据锚点完整可用；RAG 对话仍能检索到该论文内容（FR-014、US4 场景 5）。
9. 核对审核事件。
   ```bash
   mysql -h 127.0.0.1 -P 3307 -e \
     "SELECT paper_revision, status, review_comment FROM paper_review_events WHERE paper_id = 9 ORDER BY id DESC LIMIT 3"
   ```
   **预期**：存在一条对应升版的记录，说明版本变更原因（FR-016）。
10. 重新批准该论文。
    **预期**：论文重新出现在社区图表与探索页；向量索引与知识图谱按新内容重建（SC-005、US4 场景 6）。
11. 核对 CHECK 约束。
    ```bash
    mysql -h 127.0.0.1 -P 3307 -e \
      "SELECT id, content_revision, approved_revision, review_status FROM papers WHERE id = 9"
    ```
    **预期**：重新批准后 `approved_revision = content_revision` 且状态为 `approved`，满足 `ck_papers_review_revision`（SC-009）。

## 场景 6：失败回滚（US4 场景 7、FR-018）

1. 构造一个会在重建阶段失败的请求（例如材料维度传非法枚举值）针对**已批准**论文。
   ```bash
   curl -s -X PUT -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{"paper_type":"experimental","material_states":[{"material":"Sn","material_dimensionality":"bogus_value","material_family":{"id":8,"name":"单质超导体"}}]}' \
     http://127.0.0.1:8000/api/rag/papers/9/scientific-draft
   ```
   **预期**：返回错误。
2. 核对论文状态。
   **预期**：`content_revision`、`approved_revision`、`review_status` 与请求前完全一致；论文**仍然对外公开**（SC-006）。
3. 核对科学数据。
   **预期**：材料状态、Tc、物性数量与内容与请求前一致，无部分删除的中间状态。
4. 核对血缘数据。
   **预期**：四张表的 `paper_revision` 均未变化——级联更新与主表更新在同一事务内一同回滚。

## 场景 7：两段保存的失败语义（FR-019）

1. 在编辑弹窗中同时修改论文标题（论文级）与某个 Tc 数值（科学数据）。
2. 用 DevTools 阻断第二个请求（科学数据端点）后保存。
   **预期**：提示明确指出论文信息已保存但超导性质保存失败，并告知只需重试科学数据部分；重新打开弹窗，标题改动保留，Tc 改动未生效。

## 场景 8：权限（FR-021、SC-007）

以普通用户 token 调用两个新端点。

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X PUT -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" -d '{"paper_type":"review","material_states":[]}' \
  http://127.0.0.1:8000/api/rag/papers/9/scientific-draft

curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer <user_token>" \
  -F "material_state_index=0" -F "file=@test.cif" \
  http://127.0.0.1:8000/api/rag/papers/9/structure-candidates
```

**预期**：两者均返回 403。

另验证 `rejected` 论文：调用 C1 端点。
**预期**：返回 409 `paper_status_not_editable`（[research.md](research.md) R10）。

## 自动化测试

```bash
scripts/run-tests.sh frontend
scripts/run-tests.sh go
scripts/run-tests.sh backend
"$PY_BIN/python" -m pytest tests -q
```

**预期**：全部通过（除前置条件中记录的既有失败用例）。

## 生产构建

```bash
cd frontend && npm run build
```

**预期**：`tsc -b` 无类型错误。共享组件的 props 类型与两个消费方的用法不一致时会在此暴露。
