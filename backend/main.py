"""
FastAPI主应用 — 超导文献数据库网站后端服务 (React SPA 版)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.api import elements, compounds, papers, admin, auth_routes, tc_predict, alexandria, htsc2025, structures, rag

app = FastAPI(
    title="超导文献数据库 API",
    description="Conventional Superconductor Dataset",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(elements.router)
app.include_router(compounds.router)
app.include_router(papers.router)
app.include_router(auth_routes.router)
app.include_router(admin.router)
app.include_router(tc_predict.router)
app.include_router(alexandria.router)
app.include_router(htsc2025.router)
app.include_router(structures.router)
app.include_router(rag.router)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

# React SPA 入口
INDEX_HTML = STATIC_DIR / "index.html"


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "superconductor-dataset"}


# 所有非 API 路径 → React SPA（前端路由接管）
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("static/") or full_path.startswith("assets/"):
        return {"error": "not found"}
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return {"error": "前端未构建，请执行 npm run build"}


if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=False)
