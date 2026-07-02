"""
FastAPI主应用
超导文献数据库网站后端服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.api import elements, compounds, papers, admin, auth_routes, tc_predict, alexandria, htsc2025, structures, rag

# 创建FastAPI应用
app = FastAPI(
    title="超导文献数据库 API",
    description="Conventional Superconductor Dataset - 基于元素周期表的超导文献管理系统",
    version="1.0.0"
)

# 配置CORS（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip 压缩（对 Alexandria 大 JSON 响应尤其重要）
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册API路由
app.include_router(elements.router)
app.include_router(compounds.router)
app.include_router(papers.router)
app.include_router(auth_routes.router)  # 认证API
app.include_router(admin.router)  # 管理员API
app.include_router(tc_predict.router)  # Tc 预测 API
app.include_router(alexandria.router)  # Alexandria 数据库 API
app.include_router(htsc2025.router)  # HTSC-2025 数据集 API
app.include_router(structures.router)  # 晶体结构 API
app.include_router(rag.router)  # RAG 代理 API

# 挂载前端构建目录
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_BUILD_DIR = BASE_DIR / "frontend_build"

if (FRONTEND_BUILD_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_BUILD_DIR / "assets")), name="assets")


def _serve_spa():
    index_file = FRONTEND_BUILD_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"error": "前端构建产物不存在，请先运行 cd frontend && npm run build"}


@app.get("/favicon.svg")
def favicon():
    icon_file = FRONTEND_BUILD_DIR / "favicon.svg"
    if icon_file.exists():
        return FileResponse(icon_file)
    return {"error": "favicon 不存在"}


@app.get("/icons.svg")
def icons():
    icon_file = FRONTEND_BUILD_DIR / "icons.svg"
    if icon_file.exists():
        return FileResponse(icon_file)
    return {"error": "icons 不存在"}


# 根路径：返回首页
@app.get("/")
def read_root():
    """返回 React 前端入口"""
    return _serve_spa()


@app.get("/elements")
def elements_page():
    return _serve_spa()


# 元素周期表页面
@app.get("/periodic-table")
def periodic_table_page():
    return _serve_spa()


# 元素组合页面
@app.get("/compound/{element_symbols}")
def compound_page(element_symbols: str):
    return _serve_spa()


# 管理员注册页面
@app.get("/admin/register")
def admin_register_page():
    return _serve_spa()


# 统一登录页面
def _serve_login_page():
    return _serve_spa()


@app.get("/admin/login")
def admin_login_page():
    """返回管理员登录页面"""
    return _serve_login_page()


# 用户登录页面
@app.get("/login")
def user_login_page():
    """返回用户登录页面"""
    return _serve_login_page()


# 用户注册页面
@app.get("/register")
def user_register_page():
    return _serve_spa()


# 管理员审核面板
@app.get("/admin/dashboard")
def admin_dashboard_page():
    return _serve_spa()


# 超级管理员审批面板
@app.get("/admin/superadmin")
def superadmin_dashboard_page():
    return _serve_spa()


# 我审核的文献页面（可选）
@app.get("/admin/my-reviews")
def admin_my_reviews_page():
    return _serve_spa()


# 全局文献管理页面（新增）
@app.get("/admin/papers")
def admin_papers_page():
    return _serve_spa()


@app.get("/admin/users")
def admin_users_page():
    return _serve_spa()


@app.get("/tc-pre")
def tc_prediction_page():
    return _serve_spa()


@app.get("/rag")
def rag_page():
    return _serve_spa()


@app.get("/merged")
def merged_page():
    return _serve_spa()


# 健康检查端点
@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "service": "superconductor-dataset"}


# 启动信息
@app.on_event("startup")
async def startup_event():
    """应用启动时自动初始化数据库"""
    print("=" * 60)
    print("🚀 正在启动超导文献数据库服务...")
    print("=" * 60)
    from backend.init_db import initialize_sqlite_database

    initialize_sqlite_database()

    print("=" * 60)
    print("✅ 超导文献数据库服务启动成功！")
    print("=" * 60)
    print("📚 API文档: http://localhost:8000/docs")
    print("🌐 主页面: http://localhost:8000")
    print("🔬 元素周期表: http://localhost:8000/periodic-table")
    print("=" * 60)


if __name__ == "__main__":
    import uvicorn
    import os

    # Railway 和其他云平台会通过 PORT 环境变量指定端口
    # 本地开发时默认使用 8000
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # 生产环境禁用自动重载
    )
