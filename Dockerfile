FROM python:3.11-slim

# 强制重新构建（清除缓存）
ARG CACHEBUST=1

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据目录（Volume会挂载到这里）
RUN mkdir -p /app/data

# 复制并设置启动脚本权限
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 注意：不在构建时初始化数据库，而是在应用启动时初始化（见backend/main.py的startup事件）
# 这样可以确保数据库创建在Volume挂载后的持久化存储中

# 暴露端口（Railway会通过PORT环境变量动态指定）
EXPOSE 8000

# 直接启动uvicorn，host必须是0.0.0.0才能被Railway访问
# CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["/app/start.sh"]