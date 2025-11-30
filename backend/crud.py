"""
数据库CRUD操作
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from backend import models, schemas


# ============= 元素相关操作 =============

def get_all_elements(db: Session) -> List[models.Element]:
    """获取所有元素"""
    return db.query(models.Element).order_by(models.Element.atomic_number).all()


def get_element_by_symbol(db: Session, symbol: str) -> Optional[models.Element]:
    """根据元素符号获取元素"""
    return db.query(models.Element).filter(models.Element.symbol == symbol).first()


def get_elements_by_symbols(db: Session, symbols: List[str]) -> List[models.Element]:
    """根据元素符号列表获取多个元素"""
    return db.query(models.Element).filter(models.Element.symbol.in_(symbols)).all()


# ============= 元素组合相关操作 =============

def get_or_create_compound(db: Session, element_symbols: List[str]) -> models.Compound:
    """
    获取或创建元素组合
    element_symbols: 元素符号列表，如 ['Y', 'Ba', 'Cu', 'O']
    """
    # 排序并连接元素符号（如 "Ba-Cu-O-Y"）
    sorted_symbols = sorted(set(element_symbols))
    compound_key = "-".join(sorted_symbols)

    # 查找是否已存在
    compound = db.query(models.Compound).filter(
        models.Compound.element_symbols == compound_key
    ).first()

    if compound:
        return compound

    # 创建新的元素组合
    compound = models.Compound(element_symbols=compound_key)
    db.add(compound)
    db.flush()  # 获取ID但不提交

    # 获取元素对象
    elements = get_elements_by_symbols(db, sorted_symbols)

    # 创建关联
    for element in elements:
        compound_element = models.CompoundElement(
            compound_id=compound.id,
            element_id=element.id
        )
        db.add(compound_element)

    db.commit()
    db.refresh(compound)
    return compound


def get_compound_by_symbols(db: Session, element_symbols: List[str]) -> Optional[models.Compound]:
    """根据元素符号获取元素组合"""
    sorted_symbols = sorted(set(element_symbols))
    compound_key = "-".join(sorted_symbols)
    return db.query(models.Compound).filter(
        models.Compound.element_symbols == compound_key
    ).first()


def check_compound_has_papers(db: Session, element_symbols: List[str]) -> bool:
    """检查元素组合是否有文献"""
    compound = get_compound_by_symbols(db, element_symbols)
    if not compound:
        return False
    paper_count = db.query(models.Paper).filter(
        models.Paper.compound_id == compound.id
    ).count()
    return paper_count > 0


# ============= 文献相关操作 =============

def create_paper(
    db: Session,
    compound_id: int,
    doi: str,
    title: str,
    article_type: str,
    superconductor_type: str,
    authors: Optional[str] = None,
    journal: Optional[str] = None,
    volume: Optional[str] = None,
    pages: Optional[str] = None,
    year: Optional[int] = None,
    abstract: Optional[str] = None,
    citation_aps: Optional[str] = None,
    citation_bibtex: Optional[str] = None,
    chemical_formula: Optional[str] = None,
    crystal_structure: Optional[str] = None,
    contributor_name: str = "匿名贡献者",
    contributor_affiliation: str = "未提供单位",
    notes: Optional[str] = None
) -> models.Paper:
    """创建文献记录"""
    paper = models.Paper(
        compound_id=compound_id,
        doi=doi,
        title=title,
        article_type=article_type,
        superconductor_type=superconductor_type,
        authors=authors,
        journal=journal,
        volume=volume,
        pages=pages,
        year=year,
        abstract=abstract,
        citation_aps=citation_aps,
        citation_bibtex=citation_bibtex,
        chemical_formula=chemical_formula,
        crystal_structure=crystal_structure,
        contributor_name=contributor_name,
        contributor_affiliation=contributor_affiliation,
        notes=notes
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


def check_paper_exists(db: Session, compound_id: int, doi: str) -> bool:
    """检查文献是否已存在于该元素组合中"""
    paper = db.query(models.Paper).filter(
        and_(
            models.Paper.compound_id == compound_id,
            models.Paper.doi == doi
        )
    ).first()
    return paper is not None


def get_papers_by_compound(
    db: Session,
    compound_id: int,
    search_params: Optional[schemas.PaperSearchParams] = None
) -> List[models.Paper]:
    """获取元素组合的文献列表（支持搜索和筛选）"""
    query = db.query(models.Paper).filter(models.Paper.compound_id == compound_id)

    if search_params:
        # 关键词搜索
        if search_params.keyword:
            keyword = f"%{search_params.keyword}%"
            query = query.filter(
                or_(
                    models.Paper.title.like(keyword),
                    models.Paper.abstract.like(keyword),
                    models.Paper.authors.like(keyword),
                    models.Paper.chemical_formula.like(keyword)
                )
            )

        # 年份筛选
        if search_params.year_min:
            query = query.filter(models.Paper.year >= search_params.year_min)
        if search_params.year_max:
            query = query.filter(models.Paper.year <= search_params.year_max)

        # 期刊筛选
        if search_params.journal:
            query = query.filter(models.Paper.journal.like(f"%{search_params.journal}%"))

        # 晶体结构筛选
        if search_params.crystal_structure:
            query = query.filter(
                models.Paper.crystal_structure.like(f"%{search_params.crystal_structure}%")
            )

        # 审核状态筛选
        if search_params.review_status:
            query = query.filter(models.Paper.review_status == search_params.review_status)

        # 排序
        if search_params.sort_by == "year":
            if search_params.sort_order == "asc":
                query = query.order_by(models.Paper.year.asc())
            else:
                query = query.order_by(models.Paper.year.desc())
        else:  # 默认按创建时间排序
            if search_params.sort_order == "asc":
                query = query.order_by(models.Paper.created_at.asc())
            else:
                query = query.order_by(models.Paper.created_at.desc())

        # 分页
        query = query.offset(search_params.offset).limit(search_params.limit)
    else:
        # 默认按创建时间倒序
        query = query.order_by(models.Paper.created_at.desc())

    return query.all()


def get_paper_by_id(db: Session, paper_id: int) -> Optional[models.Paper]:
    """根据ID获取文献"""
    return db.query(models.Paper).filter(models.Paper.id == paper_id).first()


def get_papers_by_ids(db: Session, paper_ids: List[int]) -> List[models.Paper]:
    """根据ID列表获取多篇文献"""
    return db.query(models.Paper).filter(models.Paper.id.in_(paper_ids)).all()


# ============= 截图相关操作 =============

def create_paper_image(
    db: Session,
    paper_id: int,
    image_data: bytes,
    thumbnail_data: bytes,
    image_order: int,
    file_size: int
) -> models.PaperImage:
    """创建文献截图"""
    image = models.PaperImage(
        paper_id=paper_id,
        image_data=image_data,
        thumbnail_data=thumbnail_data,
        image_order=image_order,
        file_size=file_size
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def get_paper_images(db: Session, paper_id: int) -> List[models.PaperImage]:
    """获取文献的所有截图"""
    return db.query(models.PaperImage).filter(
        models.PaperImage.paper_id == paper_id
    ).order_by(models.PaperImage.image_order).all()


def get_image_by_id(db: Session, image_id: int) -> Optional[models.PaperImage]:
    """根据ID获取截图"""
    return db.query(models.PaperImage).filter(models.PaperImage.id == image_id).first()


def get_paper_image_count(db: Session, paper_id: int) -> int:
    """获取文献的截图数量"""
    return db.query(models.PaperImage).filter(models.PaperImage.paper_id == paper_id).count()


# ============= 统计相关操作 =============

def get_total_papers_count(db: Session) -> int:
    """获取文献总数"""
    return db.query(models.Paper).count()


def get_total_compounds_count(db: Session) -> int:
    """获取元素组合总数"""
    return db.query(models.Compound).count()


def get_compound_papers_count(db: Session, compound_id: int) -> int:
    """获取元素组合的文献数量"""
    return db.query(models.Paper).filter(models.Paper.compound_id == compound_id).count()


# ============= 辅助功能 =============

def get_all_crystal_structures(db: Session) -> List[str]:
    """获取所有已存在的晶体结构类型（去重）"""
    results = db.query(models.Paper.crystal_structure).filter(
        models.Paper.crystal_structure.isnot(None),
        models.Paper.crystal_structure != ''
    ).distinct().all()

    # 提取字符串并排序
    structures = [r[0] for r in results if r[0]]
    return sorted(structures)
