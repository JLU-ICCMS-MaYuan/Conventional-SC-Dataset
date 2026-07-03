# SC-Wiki 前端/后端 UI 原型

此目录包含完工后应有的 UI 展示和假后端，用于**纯 UI 调试和设计讨论**。

## 目录

- `frontend_example/index.html` — 静态 HTML 展示全部页面（周期表、AI 助手、点子卡片、化合物页）
- `backend_example/server.py` — Mock FastAPI 返回假数据，模拟流式 SSE 响应

## 启动

```bash
# 假后端
cd plans/backend_example
pip install -r requirements.txt
uvicorn server:app --port 8001 --reload

# 前端直接用浏览器打开
open frontend_example/index.html
```
