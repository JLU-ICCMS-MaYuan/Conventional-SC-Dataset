"""
AI筛选数据库 API
使用 hydride_literature_ai.db 和 hydride_literature_image_ai.db
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from io import BytesIO

from backend.database import get_ai_db, get_ai_image_db
from backend import crud, schemas

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/compounds/{element_symbols}")
def get_ai_compound_info(
    element_symbols: str,
    db: Session = Depends(get_ai_db)
):
    """获取AI筛选数据库中的元素组合信息"""
    symbols = element_symbols.split("-")

    compounds = crud.get_compounds_by_symbols(db, symbols, exact=True)
    compound = compounds[0] if compounds else None
    if not compound:
        elements = crud.get_elements_by_symbols(db, symbols)
        if len(elements) != len(symbols):
            invalid_symbols = set(symbols) - {e.symbol for e in elements}
            raise HTTPException(status_code=400, detail=f"以下元素不存在: {', '.join(invalid_symbols)}")

    paper_count = sum(crud.get_compound_papers_count(db, item.id) for item in compounds)

    return {
        "id": compound.id if compound else None,
        "element_symbols": "-".join(symbols),
        "element_list": symbols,
        "created_at": None,
        "paper_count": paper_count
    }


@router.get("/papers/compound/{element_symbols}", response_model=schemas.PaperPaginationResponse)
def get_ai_papers_by_compound(
    element_symbols: str,
    keyword: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    journal: Optional[str] = None,
    crystal_structure: Optional[str] = None,
    review_status: Optional[str] = None,
    sort_by: str = "year",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_ai_db),
    image_db: Session = Depends(get_ai_image_db)
):
    """获取AI筛选数据库中元素组合的文献列表"""
    symbols = element_symbols.split("-")

    compounds = crud.get_compounds_by_symbols(db, symbols, exact=True)
    if not compounds:
        raise HTTPException(
            status_code=404,
            detail=f"元素组合 {element_symbols} 在AI数据库中不存在或暂无文献"
        )

    search_params = schemas.PaperSearchParams(
        keyword=keyword,
        year_min=year_min,
        year_max=year_max,
        journal=journal,
        crystal_structure=crystal_structure,
        review_status=review_status,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )

    compound_ids = [compound.id for compound in compounds]
    total = crud.get_papers_by_compounds_count(db, compound_ids, search_params)
    papers = crud.get_papers_by_compounds(db, compound_ids, search_params)

    page_size = limit
    page = (offset // page_size) + 1 if page_size else 1
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": [crud.paper_to_response(db, paper, image_db=image_db) for paper in papers],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": offset > 0,
        "has_next": offset + page_size < total,
    }


@router.post("/papers/search-by-mode", response_model=schemas.PaperPaginationResponse)
def search_ai_papers_by_mode(
    request: schemas.PaperModeSearchRequest,
    db: Session = Depends(get_ai_db),
    image_db: Session = Depends(get_ai_image_db)
):
    """按模式搜索AI筛选数据库中的文献"""
    compound_ids = crud.get_matching_compound_ids(db, request.elements, request.mode)
    if not compound_ids:
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": request.limit,
            "total_pages": 0,
            "has_prev": False,
            "has_next": False,
        }

    search_params = schemas.PaperSearchParams(
        keyword=request.keyword,
        year_min=request.year_min,
        year_max=request.year_max,
        journal=request.journal,
        crystal_structure=request.crystal_structure,
        review_status=request.review_status,
        sort_by=request.sort_by,
        sort_order=request.sort_order,
        limit=request.limit,
        offset=request.offset,
    )

    total = crud.get_papers_by_compounds_count(db, compound_ids, search_params)
    papers = crud.get_papers_by_compounds(db, compound_ids, search_params)

    page_size = request.limit
    page = (request.offset // page_size) + 1 if page_size else 1
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": [crud.paper_to_response(db, paper, image_db=image_db) for paper in papers],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": request.offset > 0,
        "has_next": request.offset + page_size < total,
    }


@router.get("/papers/crystal-structures")
def get_ai_crystal_structures(db: Session = Depends(get_ai_db)):
    """获取AI数据库中所有晶体结构类型"""
    return crud.get_all_crystal_structures(db)


@router.get("/papers/{paper_id}/images/{image_order}")
def get_ai_paper_image(
    paper_id: int,
    image_order: int,
    thumbnail: bool = False,
    image_db: Session = Depends(get_ai_image_db)
):
    """获取AI数据库中文献截图"""
    image = crud.get_image_by_order(image_db, paper_id, image_order)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    image_data = image.thumbnail_data if thumbnail else image.image_data
    if not image_data:
        image_data = getattr(image, f"fig{image_order}", None)
    if not image_data:
        raise HTTPException(status_code=404, detail="图片不存在")

    return StreamingResponse(
        BytesIO(image_data),
        media_type="image/jpeg"
    )
