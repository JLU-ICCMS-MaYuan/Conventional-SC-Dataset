"""
数据库配置模块
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# 数据库文件路径，支持通过环境变量自定义持久化卷位置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(BASE_DIR, "data")


def _pick_existing_path(directory: str, candidates: list[str], default_name: str) -> str:
    base_path = Path(directory)
    for name in candidates:
        candidate = base_path / name
        if candidate.exists():
            return candidate.as_posix()
    return (base_path / default_name).as_posix()


METADATA_DATABASE_PATH = os.environ.get("METADATA_DATABASE_PATH")
IMAGE_DATABASE_PATH = os.environ.get("IMAGE_DATABASE_PATH")

if not METADATA_DATABASE_PATH:
    legacy_database_path = os.environ.get("DATABASE_PATH")
    if legacy_database_path:
        METADATA_DATABASE_PATH = legacy_database_path
    else:
        METADATA_DATABASE_PATH = _pick_existing_path(
            DEFAULT_DATA_DIR,
            ["hydride_literature.db"],
            "hydride_literature.db",
        )

if not IMAGE_DATABASE_PATH:
    IMAGE_DATABASE_PATH = _pick_existing_path(
        DEFAULT_DATA_DIR,
        [
            "hydride_literature_images.db",
            "superconductor_images.db",
        ],
        "hydride_literature_images.db",
    )

# AI筛选数据库路径
AI_METADATA_DATABASE_PATH = os.environ.get("AI_METADATA_DATABASE_PATH") or os.path.join(
    DEFAULT_DATA_DIR, "hydride_literature_ai.db"
)
AI_IMAGE_DATABASE_PATH = os.environ.get("AI_IMAGE_DATABASE_PATH") or os.path.join(
    DEFAULT_DATA_DIR, "hydride_literature_image_ai.db"
)

# 兼容旧代码保留 DATABASE_PATH 名称，指向 metadata DB
DATABASE_PATH = METADATA_DATABASE_PATH

for path in (METADATA_DATABASE_PATH, IMAGE_DATABASE_PATH,
             AI_METADATA_DATABASE_PATH, AI_IMAGE_DATABASE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)

METADATA_DATABASE_URL = f"sqlite:///{METADATA_DATABASE_PATH}"
IMAGE_DATABASE_URL = f"sqlite:///{IMAGE_DATABASE_PATH}"
AI_METADATA_DATABASE_URL = f"sqlite:///{AI_METADATA_DATABASE_PATH}"
AI_IMAGE_DATABASE_URL = f"sqlite:///{AI_IMAGE_DATABASE_PATH}"

# 创建数据库引擎
metadata_engine = create_engine(
    METADATA_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
image_engine = create_engine(
    IMAGE_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
ai_metadata_engine = create_engine(
    AI_METADATA_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
ai_image_engine = create_engine(
    AI_IMAGE_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# 创建Session类
MetadataSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=metadata_engine)
ImageSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=image_engine)
AIMetadataSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ai_metadata_engine)
AIImageSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ai_image_engine)

# 创建基类
MetadataBase = declarative_base()
ImageBase = declarative_base()

# 兼容旧导入
engine = metadata_engine
SessionLocal = MetadataSessionLocal
Base = MetadataBase


def get_db():
    """获取主数据库会话"""
    db = MetadataSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_image_db():
    """获取图片数据库会话"""
    db = ImageSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_ai_db():
    """获取AI筛选数据库会话"""
    db = AIMetadataSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_ai_image_db():
    """获取AI筛选图片数据库会话"""
    db = AIImageSessionLocal()
    try:
        yield db
    finally:
        db.close()
