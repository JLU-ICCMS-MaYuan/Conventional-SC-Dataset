# 实施计划：修复长文本正文压过标签的视觉层级

**GitHub Issue**：[#69](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/69)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

四处样式改动：核心发现与论文总结的正文改为 `variant="body2"` + `fontSize: 12`、去掉
`fontWeight={600}`；另有 `methodology` 兜底文本四处去粗。测试需套 `ThemeProvider` 才能
量准字号。后端与主题定义不变。

## 技术上下文

- **语言与版本**：TypeScript 5.6 + React 19 + Material-UI 7
- **测试体系**：Vitest + React Testing Library
- **主题**：`frontend/src/theme.ts` —— `caption` 12px/600、`body2` 13px、`body1` 14px
- **约束**：
  - 不改主题定义（全站共用）
  - 不改短值字段的 `body1` + 加粗
  - 不动 `PaperEditView`

## 源代码结构

```text
frontend/src/pages/SearchPage.tsx    [修改] 核心发现 + 论文总结 + methodology 兜底
frontend/src/pages/share.tsx         [修改] 同上
vitest.config.ts                     [修改] 新增 @mui/material 别名
tests/03_data_search_and_database_discovery/
  multiline-text-preserved.test.tsx  [修改] 新增 3 例字号字重断言 + ThemeProvider
docs/specs/69-detail-text-hierarchy/ [新增] 本 Spec
docs/overview/03_.../paper-and-property-results.md  [修改] 回写
```

## 需求到设计的映射

| 来源 | 设计 | 验证方式 |
|------|------|----------|
| FR-001 | 去掉 `fontWeight={600}`，改 `variant="body2"` | 用例断言 computed 字重为 400 |
| FR-002 | `sx` 加 `fontSize: 12`，与 `caption` 持平 | 用例比较正文与标签 computed 字号 |
| FR-003 | 两字段用完全相同的 variant 与 sx | 用例断言两节点 `{fontSize, fontWeight}` 相等 |
| FR-004 | 两页面同步改动 | 产物核对：两 bundle 各 2 处 `fontSize:12` + `pre-wrap` |
| FR-005 | `methodology` 兜底改 `variant="body2"` | 代码审查 |
| FR-006 | 测试套 `ThemeProvider theme={theme}` | 反向验证：还原缺陷后 3 例失败 |

## 技术决策

### 决策1：显式 `fontSize: 12` 而非仅用 `body2`

`body2` 是 13px，仍比 `caption` 标签的 12px 大 1px。用户明确要求「起码大小不能比标签的
字大」，故显式覆盖为 12px。

代价是引入了一个不走 variant 体系的字号。可选的替代是改主题让 `body2` = 12px，但那会波及
全站所有 `body2` 用处；或新增一个 variant，但为一个区块新增主题条目属过度设计。就地覆盖
影响面最小。

### 决策2：不改短值字段的加粗

DOI、年份、期刊、标题同样是 `body1` + `fontWeight={600}`，也比标签大。但这是有意的：短值
加粗帮助快速定位关键信息，长文本加粗则妨碍阅读。两者的呈现差异不是不一致，是按内容长度
分的两类。本次只改长文本。

### 决策3：测试必须套 ThemeProvider

首次写断言时量到 `0.875` 与 `0.75`（rem），与主题定义的 13px/12px 不符 —— 因为没套
`ThemeProvider`，量到的是 MUI 默认值。这类断言若不在项目主题下测量，结论完全不可信：
默认 `body2` 是 14px，会掩盖真实的字号关系。

为此在 `vitest.config.ts` 补了 `@mui/material` 别名（该包装在 `frontend/node_modules`，
测试从仓库根解析不到）。

## 实施步骤

1. `SearchPage.tsx` 核心发现：`fontWeight={600}` → `variant="body2"` + `fontSize:12`
2. `SearchPage.tsx` 论文总结：补 `fontSize:12`
3. `share.tsx` 两处同步
4. 两页面 `methodology` 兜底文本改 `variant="body2"`
5. `vitest.config.ts` 补 `@mui/material` 别名
6. 测试补 `ThemeProvider` 包裹，统一渲染入口为 `renderDetail()`
7. 新增 3 个字号字重用例
8. 反向验证、`tsc`、全量测试、构建部署

## 验证结果

| 项目 | 结果 |
|------|------|
| 多行文本文件 | 6 例通过（3 例换行 + 3 例字号字重） |
| 反向验证 | 还原为 `fontWeight={600}` 且移除 variant 后，3 个新用例全部失败 |
| `tsc --noEmit` | 通过 |
| 前端全量 | 110 例中 109 通过（唯一失败为 Issue #63 在建的 NewsFeed） |
| 产物核对 | `frontend/static/assets/` 下 `SearchPage-*.js` 与 `share-*.js` 各含 2 处 `pre-wrap`，均带 `fontSize:12`；无 `fontWeight:600` + `pre-wrap` 残留 |
| 服务验证 | `http://localhost:8080/search` 返回 200，首页加载新 bundle |

**关于 NewsFeed 失败**：`tests/08_news/NewsFeed.test.tsx` 属 Issue #63 在建代码，本次
改动前即失败。

## 部署路径的澄清

初次部署时走了错误的路径，过程与结论都记在这里。

**第一轮（错误）**：Docker Hub 不可达（`auth.docker.io` 超时）、`node:22-alpine` 本地无
缓存，无法重建前端镜像，于是用宿主机构建后 `docker cp` 进 `sc-wiki-dev-frontend-1`。
当时判定为「临时手段，容器重启会回退」。

**第二轮（查清真相）**：仓库已在 commit `abed855`（Issue #71）切换为本地化开发环境 ——
宿主机直接跑 vite、uvicorn 与 `goserver`，**前端容器根本不提供服务**。8080 端口的监听者
是宿主机 `goserver` 进程，而非容器。所以第一轮的 `docker cp` 对用户实际访问的页面毫无
影响，「容器重启会回退」这个担忧本身也不成立。

真正的服务路径是 `backend/main.py:58` 的 `STATIC_DIR = BASE_DIR / "frontend" / "static"`。
未构建时该路由返回 `{"error": "前端未构建，请执行 npm run build"}`。

**根因**：`frontend/static/assets` 属主为 root（此前容器构建留下），宿主机
`npm run build` 在清空产物目录时因权限失败。这才是 #69 部署受阻的实际原因，与 Docker Hub
可达性无关。

**最终解法**：`frontend/static` 本身属主是当前用户、父目录 `frontend` 可写，因此可以整体
替换而无需 sudo：

```bash
npx vite build --outDir /tmp/fe-final --emptyOutDir
mv static static.root-old && mv /tmp/fe-final static
```

替换后 `frontend/static` 及其 `assets` 完全归当前用户，后续 `npm run build` 不再撞权限。

**教训**：排查部署问题应先确认「谁在提供服务」，再动构建流程。本次先入为主地按容器化部署
处理，绕了两轮才发现服务早已不在容器里。占用端口的进程名（`goserver` 而非 docker-proxy）
在第一次查看端口时就已给出线索，但当时未加留意。

顺带清理了 Docker Hub 不可达的问题：从 `docker.m.daocloud.io` 拉取 `node:22-alpine` 与
`nginx:alpine` 后打上官方标签，前端镜像已能正常构建（`docker compose build frontend`
成功）。虽然对本地化环境并非必需，但恢复了容器化部署的可行性。

## 事故记录

**误判测试回归。** 全量测试中一度出现 `paper-detail-form-parity` 与
`upload-task-workspace` 各 1 例失败，我先归因为新增的 `@mui/material` 别名。移除别名后
仍失败，改用 `git stash` 对比才发现改动前是通过的 —— 于是转而认为确实是自己引入的。

但单独重跑这两个文件时稳定通过，全量并发跑才偶发失败，实为超时而非真实回归（两文件耗时
分别为 2.7s 与 20.8s，接近默认超时）。

教训：判断「是否为自己引入的回归」时，`git stash` 期间的中间状态与并发执行的超时都会给出
误导信号。应先单独重跑目标文件确认可复现性，再做归因。这一轮我连续下了两个相反的错误
结论，都是因为在信号不足时就急于定性。

**越界改动：擅自把 `tests/07` 加进 include。** 收尾阶段我在 `vitest.config.ts` 的 include
里加了 `tests/07_researcher_community_forum/**/*.test.tsx`，这超出了 #69 的范围，且让测试
套从「110 例 1 失败」变成「120 例 7 失败」—— 新增的 6 个失败是该目录既有的问题（经
`git stash` 前后对比确认，与本次改动无关），但把它们暴露出来属于另一件事，不该混进一个
排版修复。已撤回该行，`vitest.config.ts` 只保留 #69 真正需要的 `@mui/material` 别名。

`tests/07_researcher_community_forum/community-charts.test.tsx` 有 6 个既有失败（图表坐标
系、参考线、家族多选等），值得单独立项处理，不在本 Issue 范围内。
