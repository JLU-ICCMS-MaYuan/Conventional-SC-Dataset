# Python 后端
FROM python:3.12-slim

WORKDIR /app

# 安装编译依赖 → pip install → 清理编译器（减小镜像体积）
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY docker/requirements.txt .
COPY requirements-news.txt .
RUN pip install --no-cache-dir -r requirements.txt -r requirements-news.txt \
    && apt-get purge -y build-essential gcc g++ cpp binutils \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# 复制后端代码
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
