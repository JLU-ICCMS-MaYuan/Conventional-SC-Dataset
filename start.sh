#!/bin/bash

echo "======================================="
echo "🚀 启动脚本"
echo "======================================="
echo "当前时间: $(date)"
echo "工作目录: $(pwd)"
echo "PORT环境变量: ${PORT}"
echo "DATABASE_URL: ${DATABASE_URL:-使用 backend/database.py 默认 MySQL 地址}"
echo "======================================="

PYTHON_BIN="${PYTHON_BIN:-python3}"

# 检查data目录。本地开发默认使用项目内 data/，云平台可通过 DATA_DIR 覆盖。
DATA_DIR="${DATA_DIR:-data}"
if [ -d "$DATA_DIR" ]; then
    echo "✅ $DATA_DIR 目录存在"
    ls -la "$DATA_DIR"
else
    echo "❌ $DATA_DIR 目录不存在"
    mkdir -p "$DATA_DIR"
    echo "✅ 已创建 $DATA_DIR 目录"
fi

echo "======================================="
echo "迁移并初始化数据库..."
echo "======================================="

# 创建/升级表结构，然后初始化周期表元素数据
"$PYTHON_BIN" -m alembic upgrade head
"$PYTHON_BIN" -m backend.init_db

# 启动服务器 (Railway会自动设置PORT环境变量)
exec "$PYTHON_BIN" -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
