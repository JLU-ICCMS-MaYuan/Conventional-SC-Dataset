"""
数据库配置模块
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 数据库文件路径，支持通过环境变量自定义持久化卷位置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.environ.get("DATABASE_PATH") or os.path.join(BASE_DIR, "data", "superconductor.db")

# 确保data目录存在
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# SQLite数据库连接字符串
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 创建数据库引擎
# check_same_thread=False 允许多线程访问（仅SQLite需要）
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# 创建Session类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话的依赖函数
    用于FastAPI的依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
