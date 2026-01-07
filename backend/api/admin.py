"""
管理员管理与文献审核 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from backend.database import get_db
from backend.models import User, Paper
from backend.auth import get_current_superadmin, get_current_admin
from backend.email_service import email_service

router = APIRouter(prefix="/api/admin", tags=["管理员"])


# Pydantic 模型
class PendingAdminResponse(BaseModel):
    id: int
    email: str
    real_name: str
    created_at: str
    is_email_verified: bool


class ApproveRequest(BaseModel):
    user_id: int
    approved: bool  # True=通过，False=拒绝


class ChartVisibilityRequest(BaseModel):
    paper_ids: List[int]
    show: bool


class ReviewPaperRequest(BaseModel):
    status: str  # approved, rejected, modifying, unreviewed
    comment: Optional[str] = None


class PaperReviewInfo(BaseModel):
    id: int
    doi: str
    title: str
    review_status: str
    reviewed_by: Optional[int]
    reviewed_at: Optional[str]
    reviewer_name: Optional[str]


# ========== 超级管理员功能 ==========

@router.get("/pending-approvals", summary="获取待审批的管理员列表（仅超级管理员）")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """
    获取所有待审批的管理员申请

    只有超级管理员可以访问
    """
    pending_users = db.query(User).filter(
        User.is_admin == True,
        User.is_email_verified == True,
        User.is_approved == False
    ).all()

    return [
        {
            "id": user.id,
            "email": user.email,
            "real_name": user.real_name,
            "created_at": user.created_at.isoformat(),
            "is_email_verified": user.is_email_verified
        }
        for user in pending_users
    ]


@router.post("/approve-user", summary="审批管理员申请（仅超级管理员）")
async def approve_user(
    request: ApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """
    批准或拒绝管理员申请

    只有超级管理员可以操作
    """
    user = db.query(User).filter(User.id == request.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户已经被审批"
        )

    if request.approved:
        # 批准
        user.is_approved = True
        user.approved_at = datetime.utcnow()
        user.approved_by = current_user.id
        db.commit()

        # 发送批准通知邮件
        email_service.send_approval_notification(
            to_email=user.email,
            real_name=user.real_name,
            approved=True
        )

        return {
            "message": f"已批准 {user.real_name} 的管理员申请",
            "user_id": user.id,
            "email": user.email
        }
    else:
        # 拒绝 - 删除该用户
        email_service.send_approval_notification(
            to_email=user.email,
            real_name=user.real_name,
            approved=False
        )

        db.delete(user)
        db.commit()

        return {
            "message": f"已拒绝 {user.real_name} 的管理员申请",
            "user_id": user.id
        }


@router.get("/all-admins", summary="获取所有管理员列表（仅超级管理员）")
async def get_all_admins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """获取所有已批准的管理员"""
    admins = db.query(User).filter(
        User.is_admin == True,
        User.is_approved == True
    ).all()

    return [
        {
            "id": admin.id,
            "email": admin.email,
            "real_name": admin.real_name,
            "is_superadmin": admin.is_superadmin,
            "approved_at": admin.approved_at.isoformat() if admin.approved_at else None,
            "reviewed_papers_count": len(admin.reviewed_papers)
        }
        for admin in admins
    ]


# ========== 文献审核功能（所有管理员） ==========

@router.post("/papers/{paper_id}/review", summary="更新文献审核状态")
async def review_paper(
    paper_id: int,
    request: ReviewPaperRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    更新文献的审核状态

    支持的状态:
    - approved: 已通过
    - rejected: 已拒绝
    - modifying: 待修改
    - unreviewed: 未审核
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文献不存在"
        )

    valid_statuses = ["approved", "rejected", "modifying", "unreviewed"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的状态。必须是以下之一: {', '.join(valid_statuses)}"
        )

    # 更新审核信息
    paper.review_status = request.status
    paper.review_comment = request.comment
    
    if request.status == "unreviewed":
        paper.reviewed_by = None
        paper.reviewed_at = None
    else:
        paper.reviewed_by = current_user.id
        paper.reviewed_at = datetime.utcnow()
        
    db.commit()

    return {
        "message": f"文献审核状态已更新为: {request.status}",
        "paper_id": paper.id,
        "doi": paper.doi,
        "status": paper.review_status,
        "reviewer": current_user.real_name if paper.reviewed_by else None,
        "reviewed_at": paper.reviewed_at.isoformat() if paper.reviewed_at else None
    }


@router.get("/papers/unreviewed", summary="获取未审核文献列表")
async def get_unreviewed_papers(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取所有未审核的文献（分页）

    管理员可以使用此接口查看待审核文献
    """
    papers = db.query(Paper).filter(
        Paper.review_status == "unreviewed"
    ).order_by(Paper.created_at.desc()).offset(offset).limit(limit).all()

    total = db.query(Paper).filter(Paper.review_status == "unreviewed").count()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "papers": [
            {
                "id": paper.id,
                "doi": paper.doi,
                "title": paper.title,
                "year": paper.year,
                "journal": paper.journal,
                "tc": paper.physical_parameters[0].tc if paper.physical_parameters else None,
                "pressure": paper.physical_parameters[0].pressure if paper.physical_parameters else None,
                "created_at": paper.created_at.isoformat(),
                "contributor_name": paper.contributor_name
            }
            for paper in papers
        ]
    }


@router.get("/my-reviews", summary="获取我审核的文献列表")
async def get_my_reviewed_papers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """获取当前管理员审核过的所有文献"""
    papers = db.query(Paper).filter(
        Paper.reviewed_by == current_user.id
    ).order_by(Paper.reviewed_at.desc()).all()

    return {
        "total": len(papers),
        "papers": [
            {
                "id": paper.id,
                "doi": paper.doi,
                "title": paper.title,
                "year": paper.year,
                "reviewed_at": paper.reviewed_at.isoformat()
            }
            for paper in papers
        ]
    }


# ========== 文献编辑与删除功能（管理员/超级管理员） ==========

class UpdatePaperRequest(BaseModel):
    """文献编辑请求模型"""
    title: Optional[str] = None
    authors: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    article_type: Optional[str] = None  # theoretical 或 experimental
    superconductor_type: Optional[str] = None  # conventional, unconventional, unknown
    chemical_formula: Optional[str] = None
    crystal_structure: Optional[str] = None
    contributor_name: Optional[str] = None
    contributor_affiliation: Optional[str] = None
    notes: Optional[str] = None
    physical_data: Optional[List[dict]] = None  # 物理数据数组
    show_in_chart: Optional[bool] = None


# ========== 全局文献管理功能 ==========

@router.get("/papers/all", summary="获取所有文献（支持多维度筛选）")
async def get_all_papers(
    review_status: Optional[str] = None,  # unreviewed, approved, rejected, modifying
    article_type: Optional[str] = None,  # theoretical, experimental
    superconductor_type: Optional[str] = None,  # conventional, unconventional, unknown
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    keyword: Optional[str] = None,  # 搜索标题、DOI、化学式
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取所有文献列表（不限元素组合）

    支持多维度筛选：
    - review_status: 审核状态
    - article_type: 文章类型
    - superconductor_type: 超导体类型
    - year_min/year_max: 年份范围
    - keyword: 关键词搜索（标题、DOI、化学式）
    """
    query = db.query(Paper)

    # 审核状态筛选
    if review_status:
        query = query.filter(Paper.review_status == review_status)

    # 文章类型筛选
    if article_type:
        query = query.filter(Paper.article_type == article_type)

    # 超导体类型筛选
    if superconductor_type:
        query = query.filter(Paper.superconductor_type == superconductor_type)

    # 年份范围筛选
    if year_min:
        query = query.filter(Paper.year >= year_min)
    if year_max:
        query = query.filter(Paper.year <= year_max)

    # 关键词搜索
    if keyword:
        search_pattern = f"%{keyword}%"
        query = query.filter(
            (Paper.title.like(search_pattern)) |
            (Paper.doi.like(search_pattern)) |
            (Paper.chemical_formula.like(search_pattern))
        )

    # 获取总数
    total = query.count()

    # 分页查询
    papers = query.order_by(Paper.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "papers": [
            {
                "id": paper.id,
                "doi": paper.doi,
                "title": paper.title,
                "year": paper.year,
                "journal": paper.journal,
                "article_type": paper.article_type,
                "superconductor_type": paper.superconductor_type,
                "chemical_formula": paper.chemical_formula,
                "tc": paper.physical_parameters[0].tc if paper.physical_parameters else None,
                "pressure": paper.physical_parameters[0].pressure if paper.physical_parameters else None,
                "compound_symbols": paper.compound.element_symbols,
                "review_status": paper.review_status,
                "review_comment": paper.review_comment,
                "reviewer_name": paper.reviewer.real_name if paper.reviewer else None,
                "contributor_name": paper.contributor_name,
                "created_at": paper.created_at.isoformat(),
                "images_count": len(paper.images),
                "show_in_chart": paper.show_in_chart
            }
            for paper in papers
        ]
    }


@router.get("/papers/{paper_id}", summary="获取文献详细信息")
async def get_paper_detail(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取文献的完整信息（用于编辑表单）

    所有管理员都可以访问
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文献不存在"
        )

    return {
        "id": paper.id,
        "doi": paper.doi,
        "title": paper.title,
        "authors": paper.authors,
        "journal": paper.journal,
        "volume": paper.volume,
        "pages": paper.pages,
        "year": paper.year,
        "abstract": paper.abstract,
        "article_type": paper.article_type,
        "superconductor_type": paper.superconductor_type,
        "chemical_formula": paper.chemical_formula,
        "crystal_structure": paper.crystal_structure,
        "contributor_name": paper.contributor_name,
        "contributor_affiliation": paper.contributor_affiliation,
        "notes": paper.notes,
        "data": [
            {
                "pressure": d.pressure,
                "tc": d.tc,
                "lambda_val": d.lambda_val,
                "omega_log": d.omega_log,
                "n_ef": d.n_ef,
                "s_factor": d.s_factor
            } for d in paper.physical_parameters
        ],
        "review_status": paper.review_status,
        "review_comment": paper.review_comment,
        "created_at": paper.created_at.isoformat(),
        "compound_symbols": paper.compound.element_symbols,
        "show_in_chart": paper.show_in_chart
    }


@router.put("/papers/{paper_id}", summary="编辑文献信息")
async def update_paper(
    paper_id: int,
    request: UpdatePaperRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    编辑文献信息

    所有管理员都可以编辑
    只更新提供的字段，未提供的字段保持不变
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文献不存在"
        )

    # 验证文章类型
    if request.article_type and request.article_type not in ["theoretical", "experimental"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文章类型必须是 theoretical 或 experimental"
        )

    # 验证超导体类型
    if request.superconductor_type and request.superconductor_type not in ["conventional", "unconventional", "unknown"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="超导体类型必须是 conventional, unconventional 或 unknown"
        )

    # 验证年份范围
    if request.year and (request.year < 1900 or request.year > 2100):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="年份必须在 1900-2100 之间"
        )

    # 更新字段（只更新非None的字段）
    update_data = request.dict(exclude_unset=True)
    
    # 特殊处理物理数据
    if "physical_data" in update_data:
        new_data = update_data.pop("physical_data")
        if new_data is not None:
            # 删除旧数据
            from backend.models import PaperData
            db.query(PaperData).filter(PaperData.paper_id == paper_id).delete()
            db.flush() # 确保删除执行
            # 插入新数据
            for item in new_data:
                db_data = PaperData(
                    paper_id=paper_id,
                    pressure=item.get("pressure"),
                    tc=item.get("tc"),
                    lambda_val=item.get("lambda_val"),
                    omega_log=item.get("omega_log"),
                    n_ef=item.get("n_ef"),
                    s_factor=item.get("s_factor") if item.get("s_factor") is not None else crud.compute_s_factor(
                        item.get("pressure"), item.get("tc")
                    )
                )
                db.add(db_data)

    for field, value in update_data.items():
        if value is not None:
            setattr(paper, field, value)

    db.commit()
    db.refresh(paper)

    return {
        "message": "文献信息已更新",
        "paper_id": paper.id,
        "doi": paper.doi,
        "title": paper.title,
        "updated_by": current_user.real_name
    }


@router.delete("/papers/{paper_id}", summary="删除文献（仅超级管理员）")
async def delete_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """
    删除文献及其所有关联数据

    仅超级管理员可以操作
    会级联删除所有文献截图
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文献不存在"
        )

    # 记录删除的文献信息（用于日志）
    deleted_info = {
        "paper_id": paper.id,
        "doi": paper.doi,
        "title": paper.title,
        "compound": paper.compound.element_symbols,
        "images_count": len(paper.images),
        "deleted_by": current_user.real_name,
        "deleted_at": datetime.utcnow().isoformat()
    }

    # 删除文献（会自动级联删除 paper_images）
    db.delete(paper)
    db.commit()

    return {
        "message": f"文献《{deleted_info['title']}》已删除",
        "deleted_info": deleted_info
    }


# ========== 批量操作功能 ==========

class BatchReviewRequest(BaseModel):
    """批量审核请求模型"""
    paper_ids: List[int]
    status: str = "approved"  # 默认批量设为已通过


@router.post("/papers/batch-review", summary="批量审核文献")
async def batch_review_papers(
    request: BatchReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    批量将文献标记为已审核

    所有管理员都可以操作
    """
    if not request.paper_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供文献ID列表"
        )

    # 查询所有指定的文献
    papers = db.query(Paper).filter(Paper.id.in_(request.paper_ids)).all()

    if not papers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定的文献"
        )

    # 批量标记
    reviewed_count = 0
    for paper in papers:
        paper.review_status = request.status
        if request.status == "unreviewed":
            paper.reviewed_by = None
            paper.reviewed_at = None
        else:
            paper.reviewed_by = current_user.id
            paper.reviewed_at = datetime.utcnow()
        reviewed_count += 1

    db.commit()

    return {
        "message": f"批量更新完成，已将 {reviewed_count} 篇文献设为 {request.status}",
        "reviewed_count": reviewed_count,
        "total_requested": len(request.paper_ids)
    }


@router.post("/papers/batch-chart-visibility", summary="批量设置图表显示（仅超级管理员）")
async def batch_chart_visibility(
    request: ChartVisibilityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """
    批量更新文献是否显示在图表中
    """
    if not request.paper_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供文献ID列表"
        )

    papers = db.query(Paper).filter(Paper.id.in_(request.paper_ids)).all()

    if not papers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定的文献"
        )

    for paper in papers:
        paper.show_in_chart = request.show

    db.commit()

    return {
        "message": f\"已将 {len(papers)} 篇文献设置为 {'显示' if request.show else '隐藏'}\",
        "updated_count": len(papers),
        "show": request.show
    }


@router.post("/papers/batch-delete", summary="批量删除文献（仅超级管理员）")
async def batch_delete_papers(
    request: BatchReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin)
):
    """
    批量删除文献及其所有关联数据

    仅超级管理员可以操作
    """
    if not request.paper_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供文献ID列表"
        )

    # 查询所有指定的文献
    papers = db.query(Paper).filter(Paper.id.in_(request.paper_ids)).all()

    if not papers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到指定的文献"
        )

    # 记录删除信息
    deleted_papers = []
    for paper in papers:
        deleted_papers.append({
            "paper_id": paper.id,
            "doi": paper.doi,
            "title": paper.title
        })
        db.delete(paper)

    db.commit()

    return {
        "message": f"批量删除完成",
        "deleted_count": len(deleted_papers),
        "deleted_papers": deleted_papers,
        "deleted_by": current_user.real_name,
        "deleted_at": datetime.utcnow().isoformat()
    }


# ========== 图片管理功能 ==========

from backend.models import PaperImage
from backend.utils.image_processor import process_image


@router.get("/papers/{paper_id}/images", summary="获取文献的所有图片")
async def get_paper_images(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    获取文献的所有截图列表

    返回图片ID、顺序、文件大小等信息
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文献不存在"
        )

    return {
        "paper_id": paper.id,
        "total_images": len(paper.images),
        "images": [
            {
                "id": img.id,
                "order": img.image_order,
                "file_size": img.file_size,
                "created_at": img.created_at.isoformat()
            }
            for img in sorted(paper.images, key=lambda x: x.image_order)
        ]
    }


@router.delete("/papers/{paper_id}/images/{image_id}", summary="删除文献截图")
async def delete_paper_image(
    paper_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    删除指定的文献截图

    管理员可以操作
    """
    image = db.query(PaperImage).filter(
        PaperImage.id == image_id,
        PaperImage.paper_id == paper_id
    ).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图片不存在"
        )

    # 获取文献的所有图片
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if len(paper.images) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要保留一张图片"
        )

    deleted_order = image.image_order
    db.delete(image)

    # 重新排序剩余图片
    remaining_images = db.query(PaperImage).filter(
        PaperImage.paper_id == paper_id,
        PaperImage.image_order > deleted_order
    ).all()

    for img in remaining_images:
        img.image_order -= 1

    db.commit()

    return {
        "message": "图片已删除",
        "deleted_image_id": image_id,
        "remaining_images": len(paper.images) - 1
    }
