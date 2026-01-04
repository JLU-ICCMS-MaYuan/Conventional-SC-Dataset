"""
Pydantic数据模型
用于API的输入输出验证
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re


# ============= 元素相关 =============

class ElementBase(BaseModel):
    symbol: str
    name: str
    name_zh: Optional[str] = None
    atomic_number: int


class ElementResponse(ElementBase):
    id: int

    class Config:
        from_attributes = True


# ============= 元素组合相关 =============

class CompoundCreate(BaseModel):
    element_symbols: List[str] = Field(..., description="元素符号列表，如 ['Y', 'Ba', 'Cu', 'O']")

    @validator('element_symbols')
    def validate_elements(cls, v):
        if not v or len(v) == 0:
            raise ValueError("至少需要选择一个元素")
        # 去重并排序
        unique_sorted = sorted(set(v))
        return unique_sorted


class CompoundResponse(BaseModel):
    id: int
    element_symbols: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============= 文献相关 =============

class PaperCreate(BaseModel):
    """创建文献的输入模型"""
    doi: str = Field(..., description="DOI标识符")
    element_symbols: List[str] = Field(..., description="相关元素符号列表")

    # 必填分类字段
    article_type: str = Field(..., description="文章类型: theoretical 或 experimental")
    superconductor_type: str = Field(..., description="超导体类型: conventional, unconventional, unknown")

    # 可选字段
    chemical_formula: Optional[str] = Field(None, description="化学式")
    crystal_structure: Optional[str] = Field(None, description="晶体结构类型")
    contributor_name: Optional[str] = Field("匿名贡献者", description="贡献者姓名")
    contributor_affiliation: Optional[str] = Field("未提供单位", description="贡献者单位")
    notes: Optional[str] = Field(None, description="备注说明")

    @validator('doi')
    def validate_doi(cls, v):
        # DOI格式验证：10.xxxx/xxxxx
        doi_pattern = r'^10\.\d{4,}/[\S]+$'
        if not re.match(doi_pattern, v.strip()):
            raise ValueError("DOI格式无效，正确格式如：10.1038/nature12345")
        return v.strip()

    @validator('article_type')
    def validate_article_type(cls, v):
        allowed_types = ['theoretical', 'experimental']
        if v not in allowed_types:
            raise ValueError(f"文章类型必须是: {', '.join(allowed_types)}")
        return v

    @validator('superconductor_type')
    def validate_superconductor_type(cls, v):
        allowed_types = ['conventional', 'unconventional', 'unknown']
        if v not in allowed_types:
            raise ValueError(f"超导体类型必须是: {', '.join(allowed_types)}")
        return v

class PaperData(BaseModel):
    # 数据字段
    pressure: float = Field(..., description="压强 (GPa)")
    tc: float = Field(..., description="超导温度 Tc (K)")
    lambda_val: Optional[float] = Field(None, description="λ (lambda)")
    omega_log: Optional[float] = Field(None, description="ω_log")
    n_ef: Optional[float] = Field(None, description="N(E_F)")
    class Config:
        from_attributes = True # 这让 Pydantic 能处理 SQLAlchemy 对象

class PaperResponse(BaseModel):
    """文献响应模型"""
    data: List[PaperData] = []
    id: int
    compound_id: int
    doi: str
    title: str
    authors: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    citation_aps: Optional[str] = None
    citation_bibtex: Optional[str] = None
    article_type: str
    superconductor_type: str
    chemical_formula: Optional[str] = None
    crystal_structure: Optional[str] = None
    contributor_name: str
    contributor_affiliation: str
    notes: Optional[str] = None

    created_at: datetime
    image_count: int = 0  # 截图数量
    # 审核相关字段
    review_status: str = "unreviewed"
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    reviewer_name: Optional[str] = None  # 审核人姓名（需要从关联查询获取）

    class Config:
        from_attributes = True


class PaperDetail(PaperResponse):
    """文献详情模型（包含截图）"""
    element_symbols: str


# ============= 截图相关 =============

class ImageResponse(BaseModel):
    """截图响应模型"""
    id: int
    paper_id: int
    image_order: int
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============= 搜索和过滤 =============

class PaperSearchParams(BaseModel):
    """文献搜索参数"""
    keyword: Optional[str] = Field(None, description="关键词（标题、摘要、作者、化学式）")
    year_min: Optional[int] = Field(None, description="最小年份")
    year_max: Optional[int] = Field(None, description="最大年份")
    journal: Optional[str] = Field(None, description="期刊名称")
    crystal_structure: Optional[str] = Field(None, description="晶体结构类型")
    review_status: Optional[str] = Field(None, description="审核状态：reviewed(已审核), unreviewed(未审核)")
    sort_by: Optional[str] = Field("created_at", description="排序字段：created_at, year")
    sort_order: Optional[str] = Field("desc", description="排序顺序：asc, desc")
    limit: Optional[int] = Field(50, ge=1, le=200, description="返回数量限制")
    offset: Optional[int] = Field(0, ge=0, description="偏移量")


# ============= 导出相关 =============

class ExportFormat(BaseModel):
    """导出格式"""
    format: str = Field(..., description="导出格式：aps, bibtex")
    paper_ids: List[int] = Field(..., description="要导出的文献ID列表")

    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['aps', 'bibtex']
        if v.lower() not in allowed_formats:
            raise ValueError(f"不支持的导出格式，仅支持: {', '.join(allowed_formats)}")
        return v.lower()


# ============= 通用响应 =============

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
