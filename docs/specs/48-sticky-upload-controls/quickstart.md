# 快速验收：固定主导航与上传解析收起操作

## 前置条件

- 当前目录为仓库根目录。
- `frontend/node_modules` 已安装。
- 不需要后端或数据库即可运行确定性组件测试。

## 1. 运行前端回归测试

```bash
npm --prefix frontend run test:upload-ui
```

预期：身份导航和上传工作区全部测试通过；其中导航测试验证主导航 sticky 契约，上传测试验证常驻按钮通过真实页面状态路径收起详情并保留本地文件。

## 2. 运行生产构建

```bash
npm --prefix frontend run build
```

预期：TypeScript 编译和 Vite 构建成功。若仓库现有 `frontend/static` 权限阻止清空，使用不覆盖正式目录的等价构建：

```bash
cd frontend
npx tsc -b
npx vite build --outDir /tmp/scwiki-issue48-build
```

## 3. 浏览器桌面验收

1. 以 1366×768 或更大视口打开 `/upload` 并登录。
2. 展开一条存在长解析证据的任务。
3. 向下滚动超过一个视口高度。
4. 确认左侧导航仍在顶部栏下方，当前解析任务操作栏及“收起解析”仍在视口内。
5. 点击“收起解析”，确认详情关闭且上传区待上传文件仍存在。

## 4. 响应式验收

分别以 375px、768px、1366px 宽度检查：

- 页面没有由新增 sticky 元素造成的横向滚动。
- 长文件名不会挤掉“收起解析”按钮。
- 顶部 App Bar 不遮挡导航或操作栏。
