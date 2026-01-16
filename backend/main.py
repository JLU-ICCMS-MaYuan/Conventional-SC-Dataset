"""
FastAPI主应用
超导文献数据库网站后端服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.api import elements, compounds, papers, admin, auth_routes

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

# 注册API路由
app.include_router(elements.router)
app.include_router(compounds.router)
app.include_router(papers.router)
app.include_router(auth_routes.router)  # 认证API
app.include_router(admin.router)  # 管理员API

# 挂载静态文件目录
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

# 如果静态文件目录存在，挂载它
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# 根路径：返回首页
@app.get("/")
def read_root():
    """返回主页"""
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "超导文献数据库 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# 元素周期表页面
@app.get("/periodic-table")
def periodic_table_page():
    """返回元素周期表页面"""
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"error": "页面不存在"}


# 元素组合页面
@app.get("/compound/{element_symbols}")
def compound_page(element_symbols: str):
    """返回元素组合页面"""
    compound_file = TEMPLATES_DIR / "compound.html"
    if compound_file.exists():
        return FileResponse(compound_file)
    return {"error": "页面不存在"}


# 管理员注册页面
@app.get("/admin/register")
def admin_register_page():
    """返回管理员注册页面"""
    register_file = TEMPLATES_DIR / "admin_register.html"
    if register_file.exists():
        return FileResponse(register_file)
    return {"error": "页面不存在"}


# 统一登录页面
def _serve_login_page():
    login_file = TEMPLATES_DIR / "login.html"
    if login_file.exists():
        return FileResponse(login_file)
    return {"error": "页面不存在"}


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
    """返回用户注册页面"""
    register_file = TEMPLATES_DIR / "user_register.html"
    if register_file.exists():
        return FileResponse(register_file)
    return {"error": "页面不存在"}


# 管理员审核面板
@app.get("/admin/dashboard")
def admin_dashboard_page():
    """返回管理员审核面板"""
    dashboard_file = TEMPLATES_DIR / "admin_dashboard.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return {"error": "页面不存在"}


# 超级管理员审批面板
@app.get("/admin/superadmin")
def superadmin_dashboard_page():
    """返回超级管理员审批面板"""
    superadmin_file = TEMPLATES_DIR / "superadmin_dashboard.html"
    if superadmin_file.exists():
        return FileResponse(superadmin_file)
    return {"error": "页面不存在"}


# 我审核的文献页面（可选）
@app.get("/admin/my-reviews")
def admin_my_reviews_page():
    """返回我审核的文献页面"""
    # 暂时重定向到审核面板
    dashboard_file = TEMPLATES_DIR / "admin_dashboard.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return {"error": "页面不存在"}


# 全局文献管理页面（新增）
@app.get("/admin/papers")
def admin_papers_page():
    """返回全局文献管理页面"""
    papers_file = TEMPLATES_DIR / "admin_papers.html"
    if papers_file.exists():
        return FileResponse(papers_file)
    return {"error": "页面不存在"}


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

    # 自动初始化数据库
    try:
        from backend.init_db import init_database
        print("正在初始化数据库...")
        init_database()
        print("✓ 数据库初始化完成")
    except Exception as e:
        print(f"⚠️  数据库初始化失败: {e}")
        print("应用将继续启动，但可能无法正常工作")

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
