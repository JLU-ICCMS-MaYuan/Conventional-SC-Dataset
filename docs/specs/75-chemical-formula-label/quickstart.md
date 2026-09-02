# 快速验证：材料状态「材料」字段改名为「化学式」

**GitHub Issue**：[#75](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/75)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)　**Plan**：[plan.md](plan.md)

## 前置条件

```bash
make start      # 启动全部服务
make status     # 确认 frontend / goserver / python 在运行
```

浏览器打开 `http://127.0.0.1:5173`，登录后进入 `/upload`。

**依赖前提**：Issue #74 的 i18n 基建与 `upload.ts`、`admin.ts` 字典须已就位，否则本 Feature 的标签取不到双语文案。

## 场景 1：上传校对页标签（US1）

1. 打开一个解析完成的上传任务，展开材料状态卡片。
   **预期**：首个输入框标签为「化学式」，不再是「材料」。
2. 切换界面语言为英文。
   **预期**：该标签为 `Chemical formula`。
3. 在该框填入 `LaH10`，保存草稿并在 DevTools Network 中检查请求体。
   **预期**：`material_states[0].material` 的值为 `LaH10`——字段名仍是 `material`，未改为 `chemical_formula`。
4. 确认相邻标签未被误改。
   **预期**：「材料家族」「材料维度」保持原文案（英文界面下为其各自英文译名），未变成化学式相关文案。

## 场景 2：校验文案与定位（US1、FR-007）

1. 新建含 3 个材料状态的草稿，清空第 3 个的化学式框，点击提交审核。
   **预期**：横幅提示「第 3 个材料状态缺少化学式」——序号前缀保留，后半句已改。
2. 观察页面滚动行为。
   **预期**：页面定位到第 3 个材料状态卡片并滚动到可见区域，该输入框显示错误态。
3. 直接检查后端响应。
   ```bash
   curl -s -X POST http://127.0.0.1:8000/api/rag/upload-tasks/<task_id>/submit \
     -H "Authorization: Bearer <token>" | python -m json.tool
   ```
   **预期**：`detail.code` 为 `state_material_required`，`detail.message` 匹配 `第 \d+ 个材料状态缺少化学式`。
4. 清空某个材料状态的「材料家族」而非化学式，提交。
   **预期**：提示仍为「第 N 个材料状态缺少材料家族」——该文案不在本 Feature 改动范围（FR-008）。

## 场景 3：管理员编辑页标签（US2）

1. 以管理员身份打开论文编辑弹窗，滚动到物性数据区。
   **预期**：对应输入框标签为「化学式 (material)」，括号内字段名保留。
2. 切换界面语言为英文。
   **预期**：该标签为 `Chemical formula (material)`。
3. 修改该框内容并保存，重新打开弹窗。
   **预期**：改动持久生效，行为与改名前一致。

## 场景 4：不改动项确认（FR-008、范围外事项）

1. 打开超管的图表组合编辑器，查看「添加自定义点」区域。
   **预期**：该输入框标签仍为「材料名」，**未**改为「化学式」。该字段是图表数据点显示标签，允许填 `LaH10 @ 200GPa` 这类带条件的内容（见 [research.md](research.md) R2）。
2. 在该框填入 `Nb3Sn (bulk)` 并添加数据点。
   **预期**：正常添加，图例显示该标签原文。
3. 确认数据库列名未变。
   ```bash
   mysql -h 127.0.0.1 -P 3307 -e "SHOW COLUMNS FROM superconductor_properties LIKE 'material_raw'"
   mysql -h 127.0.0.1 -P 3307 -e "SHOW COLUMNS FROM superconductors LIKE 'chemical_formula'"
   ```
   **预期**：两列均存在且未改名。
4. 确认无新增迁移。
   ```bash
   git status --short alembic/versions/
   ```
   **预期**：本 Feature 未新增迁移文件。

## 自动化测试

```bash
scripts/run-tests.sh frontend
scripts/run-tests.sh backend
"$PY_BIN/python" -m pytest tests -q
```

**预期**：全部通过。`tests/01_decentralized_uploading/submit-validation-feedback.test.tsx` 的 3 处文案断言已同步为「化学式」，且序号前缀断言保留——若前缀断言被一并删除，说明对 FR-007 耦合的保护失效，需退回修正。

**已知失败用例**：`tests/07_researcher_community_forum/news-feed.test.tsx` 有一个用例在干净 `HEAD` 上同样失败（`docs/local-dev.md` 已记录），不计入本 Feature 回归。

## 生产构建

```bash
cd frontend && npm run build
```

**预期**：`tsc -b` 无类型错误。若字典缺少新增键，此处会因类型不匹配而失败。
