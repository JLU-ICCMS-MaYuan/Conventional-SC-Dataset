# 前端渐进式 React 迁移设计

日期：2026-06-22
状态：待实现

## 目标

将 SC-Wiki 前端从纯 HTML/Jinja + 原生 JS 渐进迁移到 React，优先处理交互性强的页面（RAG 对话、化合物搜索、管理后台），简单页面保持 Jinja。

## 范围

### 迁移到 React（分 3 阶段）

| 阶段 | 页面 | 原文件 |
|------|------|--------|
| 1 | RAG 对话页 | `rag.html` + `rag.js`（~400 行 JS） |
| 2 | 化合物搜索页 | `compound.html` + `compound_page.js`（~2500 行 JS） |
| 3 | 管理后台 | `admin_papers.html` + `admin_papers.js`（~1000 行 JS） |

### 保持 Jinja

首页/周期表、登录、注册、Tc 预测、管理员面板

## 技术栈

- Vite 5 + React 18 + TypeScript
- react-router-dom（路由）
- react-bootstrap（保持 Bootstrap 5 外观）
- React Context（认证状态管理）

## 目录结构

```
frontend_test/
├── vite.config.ts          # proxy /api → :8000
├── package.json
├── index.html
├── tsconfig.json
└── src/
    ├── main.tsx
    ├── App.tsx             # 路由入口
    ├── context/
    │   └── AuthContext.tsx  # 认证状态
    ├── pages/
    │   ├── RagPage.tsx      # 阶段 1
    │   ├── CompoundPage.tsx # 阶段 2
    │   └── AdminPapers.tsx  # 阶段 3
    ├── components/
    │   ├── NavBar.tsx        # 导航栏
    │   └── ChatMessage.tsx   # RAG 对话消息
    └── lib/
        └── api.ts            # fetch 封装，统一处理 401/503
```

## 开发工作流

```
# 终端 1：FastAPI 后端（端口 8000）
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 终端 2：Vite 开发服务器（端口 5173 或自定义）
cd frontend_test && npm run dev

# 浏览器访问：http://localhost:5173/rag
# Vite proxy 将 /api/* 转发到 localhost:8000
```

## 生产部署

```bash
cd frontend_test && npm run build
# 输出到 frontend_test/dist/
# FastAPI 挂载静态文件时指向 dist/ 即可
```

## 认证

`AuthContext` 从 `localStorage` 读取 token/user，替代 `auth_state.js`。每次 API 请求自动附带 `Authorization: Bearer <token>`。

## 不做的事

- 不改后端 API 接口
- 不改数据库结构
- 不引入全局状态管理库（Redux/Zustand）
- 不用 SSR
- 不移除 Bootstrap 样式，只做组件化封装

## 测试

- 每个 React 页面在 Vite 开发环境下手动验证
- 后端 API 测试保持不变
