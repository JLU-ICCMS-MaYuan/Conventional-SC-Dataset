"""
文献相关API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Annotated
import json
from io import BytesIO

from backend.database import get_db
from backend import crud, schemas
from backend.utils.doi_resolver import get_doi_metadata, validate_doi
from backend.utils.citation import generate_aps_citation, generate_bibtex_citation
from backend.utils.image_processor import process_image, validate_image as validate_image_util

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.post("/", response_model=schemas.PaperResponse)
async def create_paper(
    doi: str = Form(...),
    element_symbols: str = Form(...),  # JSON字符串
    article_type: str = Form(...),  # 文章类型: theoretical 或 experimental
    superconductor_type: str = Form(...),  # 超导体类型: conventional, unconventional, unknown
    tc: float = Form(...),
    pressure: float = Form(...),
    chemical_formula: Optional[str] = Form(None),
    crystal_structure: Optional[str] = Form(None),
    contributor_name: Optional[str] = Form("匿名贡献者"),
    contributor_affiliation: Optional[str] = Form("未提供单位"),
    notes: Optional[str] = Form(None),
    lambda_val: Optional[float] = Form(None),
    omega_log: Optional[float] = Form(None),
    n_ef: Optional[float] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    """
    上传新文献

    必填字段:
    - doi: DOI标识符
    - element_symbols: 元素符号列表（JSON字符串）
    - article_type: 文章类型 (theoretical 或 experimental)
    - superconductor_type: 超导体类型 (conventional, unconventional, unknown)
    - tc: 超导温度 Tc (K)

    可选字段:
    - pressure: 压强 (GPa)
    - lambda_val: λ (lambda)
    - omega_log: ω_log
    - n_ef: N(E_F)
    - images: 文献截图（0-5张）
    - chemical_formula: 化学式
    - crystal_structure: 晶体结构类型
    - contributor_name: 贡献者姓名
    - contributor_affiliation: 贡献者单位
    - notes: 备注说明
    """
    # 1. 解析元素符号列表
    try:
        symbols_list = json.loads(element_symbols)
        if not isinstance(symbols_list, list) or len(symbols_list) == 0:
            raise ValueError("元素符号列表不能为空")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"元素符号格式错误: {str(e)}")

    # 2. 验证截图数量
    images_to_process = images or []
    if len(images_to_process) > 5:
        raise HTTPException(
            status_code=400,
            detail="最多允许上传5张文献截图"
        )

    # 3. 验证DOI并获取元数据
    print(f"正在验证DOI: {doi}")
    is_valid = await validate_doi(doi)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"DOI {doi} 无效或不存在，请检查格式"
        )

    print(f"正在获取DOI元数据...")
    metadata = await get_doi_metadata(doi)
    if not metadata:
        raise HTTPException(
            status_code=500,
            detail="无法获取文献元数据，请稍后重试"
        )

    # 4. 获取或创建元素组合
    compound = crud.get_or_create_compound(db, symbols_list)

    # 5. 检查文献是否已存在
    if crud.check_paper_exists(db, compound.id, doi):
        raise HTTPException(
            status_code=400,
            detail=f"文献 {doi} 已存在于 {compound.element_symbols} 系统中"
        )

    # 6. 生成引用格式
    authors_list = metadata.get("authors", [])
    title = metadata.get("title", "")
    journal = metadata.get("journal", "")
    volume = metadata.get("volume", "")
    pages = metadata.get("pages", "")
    year = metadata.get("year")

    citation_aps = generate_aps_citation(
        authors_list, title, journal, volume, pages, year, doi
    )
    citation_bibtex = generate_bibtex_citation(
        authors_list, title, journal, volume, pages, year, doi
    )

    # 7. 创建文献记录
    paper = crud.create_paper(
        db=db,
        compound_id=compound.id,
        doi=doi,
        title=title,
        article_type=article_type,
        superconductor_type=superconductor_type,
        authors=json.dumps(authors_list, ensure_ascii=False),
        journal=journal,
        volume=volume,
        pages=pages,
        year=year,
        abstract=metadata.get("abstract", ""),
        citation_aps=citation_aps,
        citation_bibtex=citation_bibtex,
        chemical_formula=chemical_formula,
        crystal_structure=crystal_structure,
        contributor_name=contributor_name or "匿名贡献者",
        contributor_affiliation=contributor_affiliation or "未提供单位",
        notes=notes,
        pressure=pressure,
        tc=tc,
        lambda_val=lambda_val,
        omega_log=omega_log,
        n_ef=n_ef
    )

    # 8. 处理并保存截图
    for idx, image_file in enumerate(images_to_process, start=1):
        # 读取图片数据
        image_data = await image_file.read()

        # 验证图片
        if not validate_image_util(image_data):
            raise HTTPException(
                status_code=400,
                detail=f"图片 {image_file.filename} 无效或损坏"
            )

        # 处理图片（生成压缩图和缩略图）
        try:
            compressed_data, thumbnail_data = process_image(image_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"图片处理失败: {str(e)}"
            )

        # 保存到数据库
        crud.create_paper_image(
            db=db,
            paper_id=paper.id,
            image_data=compressed_data,
            thumbnail_data=thumbnail_data,
            image_order=idx,
            file_size=len(compressed_data)
        )

    # 9. 返回响应
    paper_response = schemas.PaperResponse.from_orm(paper)
    paper_response.image_count = len(images_to_process)

    return paper_response


@router.get("/compound/{element_symbols}", response_model=List[schemas.PaperResponse])
def get_papers_by_compound(
    element_symbols: str,
    keyword: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    journal: Optional[str] = None,
    crystal_structure: Optional[str] = None,
    review_status: Optional[str] = None,  # 新增：审核状态筛选 (reviewed/unreviewed)
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    获取元素组合的文献列表

    Args:
        element_symbols: 元素符号组合，如 "Ba-Cu-O-Y"
        keyword: 搜索关键词（可选）
        year_min, year_max: 年份范围（可选）
        journal: 期刊名称（可选）
        crystal_structure: 晶体结构类型（可选）
        review_status: 审核状态筛选 - 'reviewed'(已审核), 'unreviewed'(未审核), None(全部)
        sort_by: 排序字段（created_at或year）
        sort_order: 排序顺序（asc或desc）
        limit: 返回数量限制
        offset: 偏移量
    """
    # 解析元素符号
    symbols = element_symbols.split("-")

    # 获取元素组合
    compound = crud.get_compound_by_symbols(db, symbols)
    if not compound:
        raise HTTPException(
            status_code=404,
            detail=f"元素组合 {element_symbols} 不存在或暂无文献"
        )

    # 构建搜索参数
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

    # 获取文献列表
    papers = crud.get_papers_by_compound(db, compound.id, search_params)

    # 添加图片数量和审核人姓名
    papers_with_count = []
    for paper in papers:
        paper_resp = schemas.PaperResponse.from_orm(paper)
        # 添加审核人姓名
        if paper.reviewer:
            paper_resp.reviewer_name = paper.reviewer.real_name
        else:
            paper_resp.reviewer_name = None
        paper_resp.image_count = crud.get_paper_image_count(db, paper.id)
        papers_with_count.append(paper_resp)

    return papers_with_count


@router.get("/crystal-structures")
def get_crystal_structures(db: Session = Depends(get_db)):
    """
    获取所有已存在的晶体结构类型（用于自动补全）

    Returns:
        晶体结构类型列表（已去重并排序）
    """
    structures = crud.get_all_crystal_structures(db)
    return structures


@router.get("/{paper_id}", response_model=schemas.PaperDetail)
def get_paper_detail(paper_id: int, db: Session = Depends(get_db)):
    """
    获取文献详情
    """
    paper = crud.get_paper_by_id(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")

    # 获取元素组合信息
    compound = paper.compound

    paper_detail = schemas.PaperDetail.from_orm(paper)
    paper_detail.element_symbols = compound.element_symbols
    paper_detail.image_count = crud.get_paper_image_count(db, paper.id)

    return paper_detail


@router.get("/{paper_id}/images/{image_order}")
def get_paper_image(
    paper_id: int,
    image_order: int,
    thumbnail: bool = False,
    db: Session = Depends(get_db)
):
    """
    根据文献ID和图片顺序获取截图

    Args:
        paper_id: 文献ID
        image_order: 图片顺序 (1-5)
        thumbnail: 是否返回缩略图（默认False返回原图）
    """
    image = crud.get_image_by_order(db, paper_id, image_order)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    # 选择原图或缩略图
    image_data = image.thumbnail_data if thumbnail else image.image_data

    # 返回图片
    return StreamingResponse(
        BytesIO(image_data),
        media_type="image/jpeg"
    )


@router.get("/images/{image_id}")
def get_image_by_id(
    image_id: int,
    thumbnail: bool = False,
    db: Session = Depends(get_db)
):
    """
    根据图片ID获取截图

    Args:
        image_id: 图片ID
        thumbnail: 是否返回缩略图
    """
    image = crud.get_image_by_id(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    # 选择原图或缩略图
    image_data = image.thumbnail_data if thumbnail else image.image_data

    # 返回图片
    return StreamingResponse(
        BytesIO(image_data),
        media_type="image/jpeg"
    )


@router.post("/export")
def export_papers(
    export_data: schemas.ExportFormat,
    db: Session = Depends(get_db)
):
    """
    导出文献引用格式

    Args:
        export_data: 包含格式和文献ID列表

    Returns:
        导出的引用文本
    """
    # 获取文献
    papers = crud.get_papers_by_ids(db, export_data.paper_ids)
    if len(papers) == 0:
        raise HTTPException(status_code=404, detail="未找到文献")

    # 生成引用
    citations = []
    for paper in papers:
        if export_data.format == "aps":
            citations.append(paper.citation_aps)
        elif export_data.format == "bibtex":
            citations.append(paper.citation_bibtex)

    # 返回文本
    export_text = "\n\n".join(citations)

    return Response(
        content=export_text,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=citations.{export_data.format}"
        }
    )
