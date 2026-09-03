# 验证指南：News 页面品牌信息与三列独立资讯流

**GitHub Issue**：[ #83](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/83)

## 前置条件

- 已在仓库根目录安装前端依赖，`frontend/node_modules` 可用。
- 本地可运行前端开发服务器；如验证真实资讯数据，Go API 已提供 `/api/news/feed`。

## 自动化验证

在仓库根目录执行：

```bash
npx vitest run --config vitest.config.ts tests/03_data_search_and_database_discovery/news-page-layout.test.tsx
npm --prefix frontend run build
```

预期结果：三列初始各请求自己的 `kind` 且 `page_size=5`；点击一栏的分页不改变其他栏；双语 Hero 文案、删除入口、详情抽屉和失败/空状态均通过断言；生产构建无 TypeScript 或 Vite 错误。

## 浏览器验收

1. 启动前端开发服务器并打开 `/news`，将浏览器视口设为 1440×900。
2. 在英文界面确认 `Superconduct Wiki`、指定英文机构署名、英文简介和 `Start Exploring`；确认不再显示 `AI Literature Assistant` 或三张功能卡。
3. 切换中文，确认对应的中文品牌、机构署名、简介和“开始探索”。
4. 点击 `Start Exploring / 开始探索`，确认地址变为 `/search`。
5. 确认 News、Preprints、Articles 三栏各最多 5 条，其各自的 `Next` 按钮均无需滚动即可看到。
6. 点击任意一栏的 `Next`，确认只有该栏换页；点击任一条目，确认详情抽屉和原文链接仍可用。
7. 将视口缩窄至移动宽度，确认列纵向排列、没有横向滚动条，详情抽屉仍可操作。

## 完成信号

- 自动化测试和生产构建通过。
- 浏览器中的 1440×900 与窄屏验收均满足上述步骤。
- 实施后再更新 `docs/overview/news.md`，并在 Issue #83 的 Documentation Impact 中记录证据。
