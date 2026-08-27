"""
FastAPI主应用 — 超导文献数据库网站后端服务 (React SPA 版)
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from backend.api import kg, rag, structures, tc_predict, upload_tasks


logger = logging.getLogger(__name__)

app = FastAPI(
    title="超导文献数据库 API",
    description="Conventional Superconductor Dataset",
    version="1.0.0"
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未捕获异常统一返回结构化错误体。

    Starlette 默认对未捕获异常返回纯文本 Internal Server Error，前端取不到 detail，
    只能回退「提交审核失败」这类无信息量文案。这里沿用 _upload_error 的 {code, message}
    契约，使前端始终能展示可理解原因。

    异常原文不进入响应体：实测原文形如
    `(asyncmy.errors.DataError) (1406, "Data too long for column 'section_name' at row 1")`，
    含表名、列名与驱动细节，对用户无意义且泄漏内部结构；完整信息只写服务端日志。
    """
    logger.exception("未处理异常：%s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": {
            "code": "internal_error",
            "message": "服务器内部错误，请稍后重试；如持续失败请联系管理员并提供操作时间",
        }},
    )

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(tc_predict.router)
app.include_router(structures.router)
app.include_router(rag.router)
app.include_router(upload_tasks.router)
app.include_router(kg.router)
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
