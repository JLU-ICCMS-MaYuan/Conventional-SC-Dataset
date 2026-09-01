# 快速验证：全站中英文界面切换，数据层统一英文

**GitHub Issue**：[#74](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/74)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)　**Plan**：[plan.md](plan.md)

本文件给出端到端验证路径。每步含预期结果，可逐条核对。不复制实现代码。

## 前置条件

```bash
make start      # 启动全部服务，过程中自动执行 Alembic 迁移
make status     # 确认 frontend / goserver / python / mysql 均在运行
```

浏览器打开 `http://127.0.0.1:5173`。

**本 Feature 无数据库迁移**。六个叙述字段沿用现有列，只是内容语言从中文变为英文；分类目录的 `name_zh` / `name_en` 列本就存在。因此无需迁移前置检查。

已确认的库内现状（实施前实测）：`alembic_version` 指向 `add_kg_title`，`papers.knowledge_graph_title` 为 `varchar(200)`，库中共 1 篇论文且其六个叙述字段均为中文。

**既有失败用例**：`tests/07_researcher_community_forum/news-feed.test.tsx` 有一个用例在干净 `HEAD` 上同样失败（`docs/local-dev.md` 已记录）。收尾验证时该失败不得计入本 Feature 引入的回归。

## 场景 1：语言切换与持久化（US1）

1. 首次访问（清空 `localStorage` 后刷新）。
   **预期**：界面为简体中文；顶栏头像左侧出现 `CH / EN` 控件，`CH` 高亮。
2. 点击 `EN`。
   **预期**：当前页面导航、按钮、表单标签、提示语立即变为英文；无页面刷新、无重新登录、Network 面板无新增请求。
3. 刷新页面。
   **预期**：仍为英文，`EN` 高亮。
4. 检查 `localStorage`。
   **预期**：`sc-wiki.language` 的值为 `en`。
5. 用读屏或 DevTools 检查控件。
   **预期**：容器有 `role="group"` 与 `aria-label`；`EN` 按钮 `aria-pressed="true"`，`CH` 为 `false`；两按钮均可 Tab 聚焦并有可见焦点环。
6. 在 DevTools 中禁用 `localStorage`（或用隐私模式），再点击切换。
   **预期**：不白屏、不报错；当前会话内语言切换仍生效。

## 场景 2：英文界面全站巡检（US1、SC-001）

依次访问：`/news`、`/search`、`/knowledge`、`/share`、`/upload`、`/rag`、`/tc-predict`、`/account`，以及管理员的工作台各标签页。

**预期**：界面文案无中日韩字符。允许出现中文的位置仅两类：

- 论文原文内容（`title`、`abstract`、作者名、化学式）。
- 已明确标注的降级内容（分类家族回退的中文名）。

打开主要对话框逐一核对：登录注册、论文编辑、审核、用户权限、更名、快讯录入、图表组合编辑。

**预期**：对话框标题、字段标签、按钮、校验提示均为英文。

## 场景 3：枚举与分类家族名（US2）

1. 英文界面下打开 `/upload` 的校对页，展开材料维度、晶系、Tc 方法、论文类型、超导类型下拉。
   **预期**：选项文本为英文。
2. 选择任一选项并保存草稿，检查请求体。
   **预期**：提交的枚举值与中文界面下完全一致（如 `three_dimensional`），未被英文标签替换。
3. 查看某个由 seed 提供的材料家族（如「氢基超导体」）。
   **预期**：显示 `Hydrogen-based superconductor`。
4. 查看用户自建的家族（如「单质超导体」，`name_en` 为空）。
   **预期**：显示中文名「单质超导体」而非空白；该家族仍可正常选择与提交。
5. 直接请求目录接口。
   ```bash
   curl -s http://127.0.0.1:8080/api/classification-catalogs | head -c 400
   ```
   **预期**：每项同时含 `name`、`name_zh`、`name_en`，且 `name === name_zh`。
## 场景 4：论文叙述字段为英文（US3、FR-014）

1. 打开任意论文详情，中文界面下查看总结、核心发现、研究驱动力、研究方法、关键词、图谱标题。
   **预期**：六个字段内容为英文。
2. 切换为英文界面，查看同一篇论文。
   **预期**：六个字段内容与中文界面下完全相同——这些字段不随界面语言变化。
3. 检查接口响应。
   ```bash
   curl -s http://127.0.0.1:8080/api/papers/9 | python -m json.tool | grep -E 'summary|key_finding|knowledge_graph_title'
   ```
   **预期**：字段键名与改动前一致，无 `*_en` 键、无 `narrative_en_sync` 对象。

## 场景 5：解析产出英文（US3）

1. 上传一篇新的英文 PDF，等待解析完成进入校对页。
   **预期**：六个叙述字段的内容为英文。
2. 查看某篇原文未交代研究驱动力的论文解析结果。
   **预期**：`research_motivation` 为空，未凭空生成内容。
3. 提交草稿后查询数据库。
   ```bash
   mysql -h 127.0.0.1 -P 3307 -e "SELECT summary, key_finding FROM papers ORDER BY id DESC LIMIT 1"
   ```
   **预期**：内容为英文，无中日韩字符。

## 场景 6：存量数据转换（US4）

1. 转换前记录现状。
   ```bash
   mysql -h 127.0.0.1 -P 3307 -e "SELECT id, LEFT(summary,40), LEFT(knowledge_graph_title,40) FROM papers"
   ```
   **预期**：`papers.id=9` 的字段为中文；`knowledge_graph_title` 显示为 `é¦–æ¬¡...` 形式的双重编码损坏。
2. 执行转换脚本。
   ```bash
   "$PY_BIN/python" -m backend.scripts.convert_narrative_to_english
   ```
   **预期**：输出处理数、成功数、跳过数与失败清单。
3. 核对结果。
   **预期**：六个字段为英文，无中日韩字符；`knowledge_graph_title` 的编码损坏已被英文内容覆盖修复。
4. 确认空字段未被填充。
   **预期**：转换前为空的字段仍为空。
5. 验证通过后删除脚本。
   ```bash
   rm backend/scripts/convert_narrative_to_english.py backend/tests/test_narrative_backfill.py
   git status --short backend/scripts/
   ```
   **预期**：脚本已删除，代码库中无一次性转换工具残留（FR-017、SC-008）。

## 场景 7：管理员编辑叙述字段（US5）

1. 以管理员身份打开论文编辑弹窗。
   **预期**：六个叙述字段以单栏形式呈现英文内容，均可编辑。
2. 修改 `summary` 并保存，重新打开。
   **预期**：改动持久生效。
3. 修改 `knowledge_graph_title` 并保存，重新打开。
   **预期**：改动持久生效。**这是本 Feature 修复的既有缺陷**——该字段此前不在 Go 的 `paperUpdateFields` 与 `PatchPaper` 白名单内，编辑会被静默丢弃（接口返回 200 但数据未保存）。
4. 直接验证接口层。
   ```bash
   curl -s -X PUT -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
     -d '{"knowledge_graph_title":"Test KG Title"}' \
     http://127.0.0.1:8080/api/admin/papers/9
   mysql -h 127.0.0.1 -P 3307 -e "SELECT knowledge_graph_title FROM papers WHERE id=9"
   ```
   **预期**：数据库中的值已更新为 `Test KG Title`。

## 场景 8：手工快讯（US7、FR-020）

1. 以超级管理员身份打开快讯管理，新建一条快讯。
   **预期**：标题与摘要为单个输入位，提示说明以英文填写；无中英双栏。

## 自动化测试

```bash
scripts/run-tests.sh frontend   # Vitest
scripts/run-tests.sh go         # go test ./...
scripts/run-tests.sh backend    # pytest backend/tests
"$PY_BIN/python" -m pytest tests -q   # 仓库根测试目录
```

**预期**：全部通过，除 `tests/07_researcher_community_forum/news-feed.test.tsx` 的既有失败用例（与本 Feature 无关，见前置条件）。

**基线**：实施前记录的基线为前端 128 通过 / 1 失败、Go 全部 ok、后端 pytest 116 通过。

**新测试目录警告**：若新增了测试目录，必须同步登记到 `vitest.config.ts` 的 `include` 白名单，否则该目录用例被静默跳过——不报错、不计数。本 Feature 的测试落在已登记目录内。

## 生产构建

```bash
cd frontend && npm run build
```

**预期**：`tsc -b` 无类型错误。英文字典缺键会在此暴露——字典类型由中文字典推导，英文侧缺键即类型不匹配（已实测验证：删除英文一个键会报 `Property 'confirm' is missing`）。
