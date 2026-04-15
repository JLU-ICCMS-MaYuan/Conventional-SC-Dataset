#!/bin/bash

echo "======================================="
echo "🚀 启动脚本"
echo "======================================="
echo "当前时间: $(date)"
echo "工作目录: $(pwd)"
echo "PORT环境变量: ${PORT}"
echo "======================================="

# 检查data目录
if [ -d "/app/data" ]; then
    echo "✅ /app/data 目录存在"
    ls -la /app/data
else
    echo "❌ /app/data 目录不存在"
    mkdir -p /app/data
    echo "✅ 已创建 /app/data 目录"
fi

echo "======================================="
echo "初始化数据库..."
echo "======================================="

# 初始化数据库
python -m backend.init_db

# 启动服务器 (Railway会自动设置PORT环境变量)
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
