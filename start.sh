#!/bin/bash

set -e

echo "======================================="
echo "🚀 启动脚本"
echo "======================================="
echo "当前时间: $(date)"
echo "工作目录: $(pwd)"
echo "PORT环境变量: ${PORT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ -z "$DATABASE_URL" ]; then
    export DATABASE_URL="mysql+pymysql://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4"
fi
echo "DATABASE_URL: $DATABASE_URL"
echo "======================================="

echo "迁移并初始化数据库..."
echo "======================================="

"$PYTHON_BIN" -m alembic upgrade head
"$PYTHON_BIN" -m backend.init_db

exec "$PYTHON_BIN" -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
