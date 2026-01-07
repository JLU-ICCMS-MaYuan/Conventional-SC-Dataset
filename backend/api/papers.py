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

from backend.auth import (
    get_current_user,
    get_current_admin
)

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.post("/", response_model=schemas.PaperResponse)
async def create_paper(
    doi: str = Form(...),
    element_symbols: str = Form(...),  # JSON字符串
    article_type: str = Form(...),  # 文章类型: theoretical 或 experimental
    superconductor_type: str = Form(...),  # 超导体类型: cuprate, iron_based, nickel_based, hydride, carbon_organic, other_conventional, other_unconventional, unknown
    physical_data: str = Form(...),  # JSON字符串，包含多组物理参数
    chemical_formula: Optional[str] = Form(None),
    crystal_structure: Optional[str] = Form(None),
    contributor_name: Optional[str] = Form(None),
    contributor_affiliation: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: Annotated[schemas.User, Depends(get_current_user)] = None
):
    """
    上传新文献
    """
    # 强制登录
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录后再上传文献")

    # 1. 解析参数
    try:
        symbols_list = json.loads(element_symbols)
        if not isinstance(symbols_list, list) or len(symbols_list) == 0:
            raise ValueError("元素符号列表不能为空")
        
        data_list = json.loads(physical_data)
        if not isinstance(data_list, list) or len(data_list) == 0:
            raise ValueError("物理数据不能为空")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"参数格式错误: {str(e)}")

    # 2. 验证截图数量
    # 如果没有文件上传，FastAPI 会返回一个空列表
    images_to_process = [img for img in images if img.filename]
    
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
    # 优先使用登录用户的真实姓名作为贡献者
    final_contributor_name = current_user.real_name if current_user else (contributor_name or "匿名贡献者")

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
        contributor_name=final_contributor_name,
        contributor_affiliation=contributor_affiliation or "未提供单位",
        notes=notes
    )

    # 8. 保存物理数据点
    crud.create_paper_data(db=db, paper_id=paper.id, data_list=data_list)

    # 9. 处理并保存截图
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
    review_status: Optional[str] = None,  # 审核状态筛选 (approved/unreviewed/rejected/modifying)
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    获取元素组合的文献列表
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


@router.get("/stats/chart-data")
def get_chart_data(db: Session = Depends(get_db)):
    """获取用于图表展示的 P-Tc 数据点"""
    from backend.models import Paper
    
    # 查询所有标记为在图表中显示的文献
    papers = db.query(Paper).filter(Paper.show_in_chart == True).all()
    
    result = []
    for paper in papers:
        for data in paper.physical_parameters:
            if data.pressure is not None and data.tc is not None:
                result.append({
                    "x": data.pressure,
                    "y": data.tc,
                    "label": paper.chemical_formula or paper.title[:20],
                    "doi": paper.doi,
                    "type": paper.article_type,
                    "sc_type": paper.superconductor_type
                })
    return result
