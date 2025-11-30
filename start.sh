#!/bin/bash

# 初始化数据库
python -m backend.init_db

# 启动服务器 (Railway会自动设置PORT环境变量)
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
