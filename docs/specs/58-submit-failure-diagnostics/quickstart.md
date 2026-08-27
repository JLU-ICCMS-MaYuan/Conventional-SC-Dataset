# 验证路径：提交审核失败的可诊断性与必填定位

**GitHub Issue**：[#58](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/58)

**Spec**：[spec.md](spec.md)

## 前置条件

- 开发栈位于 `/home/mayuan/work/SC-Wiki-docker`，编排文件 `dev.yaml`，服务名 `python`、`frontend`、`mysql`、`redis`。
- 后端与前端改动生效都需重建镜像：Dockerfile 用 `COPY backend/ ./backend/` 把代码打进镜像，不是 bind mount，因此 `restart python` 不会加载工作区改动。
- **后端测试不能用 `exec -T python`**：镜像只安装 `docker/requirements.txt`（生产依赖，不含 pytest），根 `requirements.txt:51` 的 `pytest>=8.0` 不在镜像内；且 `exec` 进入的是镜像里的代码快照，不是工作区。宿主机也不能直接跑（缺 `fitz`、`redis` 等依赖）。正确做法是用一次性容器挂载仓库，见下方命令。
- 场景 1、2 依赖任务 `946c56c2a2854b2d8b8bba08518cba43`（ThH10，Redis 草稿 72 KB 完好，12 个 `##` 标题、最长 1389 字符）。该任务的 Redis 键 24 小时滑动过期，过期后需重新上传同一 PDF 复现。

## 自动化验证

后端（一次性容器挂载工作区，临时安装 pytest；容器随命令结束销毁，不污染运行栈）：

```bash
cd /home/mayuan/work/SC-Wiki-docker && docker compose -f dev.yaml run --rm --no-deps \
  -v /home/mayuan/code/SC-Wiki:/app -w /app python \
  sh -c 'pip install --quiet "pytest>=8.0" && python -m pytest backend/tests -q --ignore=backend/tests/test_concurrency.py'
```

`test_concurrency.py` 为环境依赖型脚本，按既有约定排除。只跑本 Feature 的两个文件时，把末尾替换为
`python -m pytest backend/tests/test_upload_jobs.py backend/tests/test_submit_error_contract.py -q`。

前端（在仓库目录执行，不是编排目录）：

```bash
cd /home/mayuan/code/SC-Wiki/frontend && npm run test:upload-ui && npx tsc --noEmit
```

预期：后端 109 通过；前端 8 文件 65 用例通过（既有基线 58 + 本 Feature 新增 7）；`tsc` 无输出。

## 场景 1：解析噪声不再阻断提交（US1，FR-001/FR-003，SC-001）

1. 重启后端：`docker compose -f /home/mayuan/work/SC-Wiki-docker/dev.yaml restart python`
2. 浏览器打开 `http://localhost:8080/upload`，展开 ThH10 任务的解析详情。
3. 点击「提交审核」。

**预期**：提交成功，页面跳转到 `/papers/:id`；横幅不再显示「提交审核失败」。

**核对**：

```bash
docker compose -f /home/mayuan/work/SC-Wiki-docker/dev.yaml logs --tail=200 python | grep -c "DataError"
```

预期输出 `0`（本次提交未产生新的 `DataError`）。

## 场景 2：被误判正文进入可检索内容（US1，FR-002，SC-002）

场景 1 提交成功后，取得该论文 id，核对三段被误判文字已进入 `paper_chunks.content`：

```bash
docker compose -f /home/mayuan/work/SC-Wiki-docker/dev.yaml exec -T mysql \
  sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scwiki -N -e "
    SELECT
      SUM(content LIKE \"%transition-metal hydrides are extremely promising%\"),
      SUM(content LIKE \"%structure prediction methods%\"),
      SUM(content LIKE \"%Detailed crystal structure of predicted phases%\"),
      MAX(CHAR_LENGTH(section_name))
    FROM paper_chunks WHERE paper_id = <上一步的 id>;" 2>/dev/null'
```

**预期**：前三列均 ≥ 1（三段探针文字都可检索到）；第四列 ≤ 500。

**修复前对照**：三列均为 0，且提交根本无法完成。

## 场景 3：后端异常给出可理解原因（US2，FR-004~FR-006，SC-004）

不便在生产路径人为制造异常时，以自动化契约测试为准（`backend/tests/test_submit_error_contract.py`）。需人工确认时：

1. 在 `python` 容器内临时构造一个必然抛未预期异常的路由并请求它。
2. 观察响应体。

**预期**：响应体为 `{"detail": {"code": "internal_error", "message": "<中文说明>"}}`；不含 `asyncmy`、`DataError`、表名列名、`INSERT`、`/app/backend/` 等内容。前端横幅显示该 `message` 而非「提交审核失败」。

**清理**：验证后移除临时路由。

## 场景 4：必填校验定位到字段（US3，FR-007~FR-010，SC-005）

1. 重建前端镜像：

```bash
cd /home/mayuan/work/SC-Wiki-docker && docker compose -f dev.yaml build frontend && docker compose -f dev.yaml up -d frontend
```

2. 打开任一 `ready` 任务的校对页，确保材料状态数量 >2（使默认折叠生效）。
3. 清空第 3 个材料状态的「材料」字段，同时清空论文「标题」。
4. 点击「提交审核」。

**预期**：

- 第 3 张材料状态卡片自动展开。
- 页面滚动到首个出错字段，该字段获得焦点。
- 出错字段显示红色错误态与说明文字。
- 横幅同时列出「标题不能为空」与第 3 个材料状态缺少材料两项，而非只报一条。
- 未发起提交请求（后端日志无该任务的 submit 记录）。

**修复前对照**：只显示一句「标题不能为空」，不滚动、不高亮、不展开卡片，第 3 张卡片的问题需修好标题后再次提交才会暴露。

## 场景 5：后端专属规则的定位与错误清除（US3，FR-010/FR-011）

1. 构造后端独有规则违反：某材料状态填写压强 min=300、max=200（前端无此校验，后端返回 400 `invalid_pressure_range`）。
2. 点击「提交审核」。

**预期**：横幅显示后端 `message`（含「第 N 个材料状态」）与错误码；对应卡片展开并滚动到位。

3. 修正为 min=200、max=300，再次提交。

**预期**：提交成功，全部错误态与横幅清除。

## 场景 6：既有行为无回归（SC-003、SC-006）

1. 用一篇标题正常（65–204 字符）的论文完成一次提交。

**预期**：提交成功；`paper_chunks` 的 `section_name` 为真实章节名（如 `RESULTS`），分段数量与修复前一致。

2. 用已存在的 DOI 提交。

**预期**：显示既有文案「该 DOI 已存在（论文 #N），没有创建重复记录。」，未被新的兜底逻辑覆盖。

3. 触发正文与附件不一致的提交。

**预期**：仍弹出既有确认对话框，确认后可继续提交。

## 验收对照

| 场景 | 覆盖 |
|---|---|
| 1 | FR-001、FR-003、SC-001 |
| 2 | FR-002、SC-002 |
| 3 | FR-004、FR-005、FR-006、SC-004 |
| 4 | FR-007、FR-008、FR-009、SC-005 |
| 5 | FR-010、FR-011 |
| 6 | SC-003、SC-006 |
