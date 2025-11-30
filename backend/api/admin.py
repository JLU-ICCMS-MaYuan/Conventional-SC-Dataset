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


class ReviewPaperRequest(BaseModel):
    paper_id: int


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

@router.post("/papers/{paper_id}/review", summary="标记文献为已审核")
async def review_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    将文献标记为已审核

    所有已批准的管理员都可以操作
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文献不存在"
        )

    if paper.review_status == "reviewed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该文献已被审核（审核人：{paper.reviewer.real_name}）"
        )

    # 标记为已审核
    paper.review_status = "reviewed"
    paper.reviewed_by = current_user.id
    paper.reviewed_at = datetime.utcnow()
    db.commit()

    return {
        "message": "文献已标记为已审核",
        "paper_id": paper.id,
        "doi": paper.doi,
        "title": paper.title,
        "reviewer": current_user.real_name,
        "reviewed_at": paper.reviewed_at.isoformat()
    }


@router.post("/papers/{paper_id}/unreview", summary="取消文献审核状态")
async def unreview_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    取消文献的审核状态（标记为未审核）

    所有已批准的管理员都可以操作
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()

    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文献不存在"
        )

    if paper.review_status == "unreviewed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该文献尚未被审核"
        )

    # 取消审核状态
    paper.review_status = "unreviewed"
    paper.reviewed_by = None
    paper.reviewed_at = None
    db.commit()

    return {
        "message": "已取消文献审核状态",
        "paper_id": paper.id,
        "doi": paper.doi,
        "title": paper.title
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
