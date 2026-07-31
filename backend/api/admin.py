"""
Admin APIs for users, paper review, and data management (v2 key_properties).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.security import get_current_admin, get_current_superadmin


router = APIRouter(prefix="/api/admin", tags=["管理员"])

REVIEW_STATUSES = {"pending", "approved", "rejected", "needs_revision"}
ROLES = {"user", "admin", "superadmin"}


class ApproveRequest(BaseModel):
    user_id: int
    approved: bool


class ReviewPaperRequest(BaseModel):
    status: str
    comment: Optional[str] = None


class UserPermissionRequest(BaseModel):
    role: Optional[str] = None
    is_admin: Optional[bool] = None
    is_superadmin: Optional[bool] = None
    is_approved: bool


class BatchReviewRequest(BaseModel):
    paper_ids: list[int]
    status: str
    comment: Optional[str] = None


class BatchDeleteRequest(BaseModel):
    paper_ids: list[int]


def _is_admin(user: models.User) -> bool:
    return user.role in {"admin", "superadmin"}


def _is_superadmin(user: models.User) -> bool:
    return user.role == "superadmin"


def _legacy_role(is_admin: Optional[bool], is_superadmin: Optional[bool], fallback: str = "user") -> str:
    if is_superadmin:
        return "superadmin"
    if is_admin:
        return "admin"
    return fallback


def _user_to_dict(db: Session, user: models.User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "real_name": user.real_name,
        "role": user.role,
        "is_admin": _is_admin(user),
        "is_superadmin": _is_superadmin(user),
        "is_approved": user.is_approved,
        "is_email_verified": user.is_email_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "approved_at": user.approved_at.isoformat() if user.approved_at else None,
        "submitted_count": db.query(models.Paper).filter(models.Paper.uploaded_by_user_id == user.id).count(),
        "reviewed_count": db.query(models.Paper).filter(models.Paper.reviewed_by_user_id == user.id).count(),
    }


def _paper_to_dict(paper: models.Paper) -> dict:
    """v2: 用 key_properties 替代 superconductor_records"""
    reviewer = paper.reviewed_by_user
    uploader = paper.uploaded_by_user
    kps = paper.key_properties or []

    # 从 key_properties 聚合信息
    materials = list({kp.material for kp in kps})
    article_types = list({kp.article_type for kp in kps if kp.article_type})
    sc_types = list({kp.superconductor_type for kp in kps if kp.superconductor_type})

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
        "review_status": paper.review_status,
        "review_comment": paper.review_comment,
        "reviewed_by_user_id": paper.reviewed_by_user_id,
        "reviewer_name": reviewer.real_name if reviewer else None,
        "reviewed_at": paper.reviewed_at.isoformat() if paper.reviewed_at else None,
        "uploaded_by_user_id": paper.uploaded_by_user_id,
        "uploader_name": uploader.real_name if uploader else None,
        "created_at": paper.created_at.isoformat() if paper.created_at else None,
        "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
        "summary": paper.summary,
        "paper_type": paper.paper_type,
        "keywords_tags": paper.keywords_tags,
        "source_file_path": paper.source_file_path,
        "methodology": paper.methodology,
        "key_finding": paper.key_finding,
        "rationale": paper.rationale,
        "record_count": len(kps),
        "show_in_chart": False,
        "compound_symbols": materials[:3] if materials else None,
        "article_types": article_types,
        "superconductor_types": sc_types,
        "materials": materials,
        "key_properties": [
            {
                "id": kp.id,
                "material": kp.material,
                "name": kp.name,
                "name_raw": kp.name_raw,
                "value_min": kp.value_min,
                "value_max": kp.value_max,
                "value_raw": kp.value_raw,
                "unit": kp.unit,
                "pressure_gpa": kp.pressure_gpa,
                "temperature_k": kp.temperature_k,
                "is_primary": kp.is_primary,
                "superconductor_type": kp.superconductor_type,
                "article_type": kp.article_type,
                "name_note": kp.name_note,
                "condition_note": kp.condition_note,
            }
            for kp in kps
        ],
    }


def _paper_query(
    db: Session,
    *,
    status_filter: Optional[str] = None,
    keyword: Optional[str] = None,
    material: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
):
    query = db.query(models.Paper)
    if status_filter:
        query = query.filter(models.Paper.review_status == status_filter)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                models.Paper.title.like(pattern),
                models.Paper.doi.like(pattern),
                models.Paper.journal.like(pattern),
            )
        )
    if material:
        sub = db.query(models.KeyProperty.paper_id).filter(
            models.KeyProperty.material.like(f"%{material}%")
        ).subquery()
        query = query.filter(models.Paper.id.in_(sub))
    if year_min is not None:
        query = query.filter(models.Paper.year >= year_min)
    if year_max is not None:
        query = query.filter(models.Paper.year <= year_max)
    return query


# ═══════════════════════════════════════════════
# User Management
# ═══════════════════════════════════════════════

@router.get("/all-users", summary="获取所有用户列表（仅超级管理员）")
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    return [_user_to_dict(db, user) for user in db.query(models.User).all()]


@router.put("/users/{user_id}/permissions", summary="修改用户权限（仅超级管理员）")
async def update_user_permissions(
    user_id: int,
    request: UserPermissionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id and request.role != "superadmin" and request.is_superadmin is False:
        raise HTTPException(status_code=400, detail="不能取消自己的超级管理员权限")

    role = request.role or _legacy_role(request.is_admin, request.is_superadmin, user.role)
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="无效的用户角色")
    user.role = role
    user.is_approved = request.is_approved
    if user.is_approved and not user.approved_at:
        user.approved_at = datetime.utcnow()
        user.approved_by_user_id = current_user.id
    db.commit()
    return {"message": "用户权限已更新", "user": _user_to_dict(db, user)}


@router.delete("/users/{user_id}", summary="删除用户（仅超级管理员）")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.delete(user)
    db.commit()
    return {"message": "用户已删除"}


@router.get("/pending-approvals", summary="获取待审批的管理员列表（仅超级管理员）")
async def get_pending_approvals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    users = (
        db.query(models.User)
        .filter(models.User.role == "admin", models.User.is_approved == False)
        .all()
    )
    return [_user_to_dict(db, user) for user in users]


@router.post("/approve-user", summary="审批管理员申请（仅超级管理员）")
async def approve_user(
    request: ApproveRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    user = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=400, detail="该用户不是管理员申请")
    user.is_approved = request.approved
    user.approved_at = datetime.utcnow() if request.approved else None
    user.approved_by_user_id = current_user.id if request.approved else None
    db.commit()
    return {"message": "审批已更新", "user": _user_to_dict(db, user)}


@router.get("/all-admins", summary="获取所有管理员列表（仅超级管理员）")
async def get_all_admins(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    users = db.query(models.User).filter(models.User.role.in_(["admin", "superadmin"])).all()
    return [_user_to_dict(db, user) for user in users]


# ═══════════════════════════════════════════════
# Paper Review
# ═══════════════════════════════════════════════

@router.post("/papers/{paper_id}/review", summary="更新文献审核状态")
async def review_paper(
    paper_id: int,
    request: ReviewPaperRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    if request.status not in REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="无效的审核状态")
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")
    paper.review_status = request.status
    paper.review_comment = request.comment
    paper.reviewed_by_user_id = current_user.id
    paper.reviewed_at = datetime.utcnow()
    db.commit()

    # 审批通过后同步到 Neo4j
    if request.status == "approved":
        try:
            from backend.ingest.sync_neo4j import KGSync
            kg = KGSync()
            kg.sync_single(paper_id)
            kg.close()
        except Exception:
            pass  # Neo4j 不可用时不阻塞审批流程

    return {"message": "审核状态已更新", "paper": _paper_to_dict(paper)}


@router.get("/papers/unreviewed", summary="获取未审核文献列表")
async def get_unreviewed_papers(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    query = _paper_query(db, status_filter="pending").order_by(models.Paper.created_at.asc())
    total = query.count()
    papers = query.offset(offset).limit(limit).all()
    return {"items": [_paper_to_dict(paper) for paper in papers], "total": total}


@router.get("/my-reviews", summary="获取我审核的文献列表")
async def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    papers = db.query(models.Paper).filter(models.Paper.reviewed_by_user_id == current_user.id).all()
    return [_paper_to_dict(paper) for paper in papers]


@router.get("/papers/all", summary="获取所有文献（支持筛选）")
async def get_all_papers(
    keyword: Optional[str] = None,
    material: Optional[str] = None,
    review_status: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    query = _paper_query(
        db,
        status_filter=review_status,
        keyword=keyword,
        material=material,
        year_min=year_min,
        year_max=year_max,
    ).order_by(models.Paper.created_at.desc())
    total = query.count()
    papers = query.offset(offset).limit(limit).all()
    return {
        "items": [_paper_to_dict(paper) for paper in papers],
        "total": total,
        "page": (offset // limit) + 1 if limit else 1,
        "page_size": limit,
        "has_next": offset + limit < total,
        "has_prev": offset > 0,
    }


@router.get("/papers/{paper_id}", summary="获取文献详细信息")
async def get_paper_detail(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")
    return _paper_to_dict(paper)


@router.put("/papers/{paper_id}", summary="编辑文献基础信息")
async def update_paper(
    paper_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")
    editable = ("doi", "title", "authors", "journal", "volume", "pages", "year", "abstract",
                "review_comment", "review_status",
                "summary", "paper_type", "keywords_tags", "source_file_path",
                "methodology", "key_finding", "rationale")
    for field in editable:
        if field in payload:
            setattr(paper, field, payload[field])

    # 更新 key_properties
    kps_in = payload.get("key_properties")
    if isinstance(kps_in, list):
        for kp_data in kps_in:
            kp_id = kp_data.get("id")
            if not kp_id:
                continue
            kp = db.query(models.KeyProperty).filter_by(id=kp_id, paper_id=paper_id).first()
            if not kp:
                continue
            kp_fields = ("material", "name", "name_raw", "name_note",
                         "value_min", "value_max", "value_raw", "unit",
                         "pressure_gpa", "temperature_k", "is_primary",
                         "superconductor_type", "article_type", "condition_note")
            for f in kp_fields:
                if f in kp_data:
                    setattr(kp, f, kp_data[f])

    db.commit()
    return {"message": "文献信息已更新", "paper": _paper_to_dict(paper)}


@router.delete("/papers/{paper_id}", summary="删除文献（仅超级管理员）")
async def delete_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")
    # v2: 删除关联的 key_properties
    db.query(models.KeyProperty).filter(models.KeyProperty.paper_id == paper_id).delete()
    db.delete(paper)
    db.commit()
    return {"message": "文献已删除"}


@router.post("/papers/batch-review", summary="批量审核文献")
async def batch_review_papers(
    request: BatchReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    if request.status not in REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="无效的审核状态")
    papers = db.query(models.Paper).filter(models.Paper.id.in_(request.paper_ids)).all()
    for paper in papers:
        paper.review_status = request.status
        paper.review_comment = request.comment
        paper.reviewed_by_user_id = current_user.id
        paper.reviewed_at = datetime.utcnow()
    db.commit()

    # 审批通过后同步到 Neo4j
    if request.status == "approved":
        try:
            from backend.ingest.sync_neo4j import KGSync
            kg = KGSync()
            for pid in request.paper_ids:
                kg.sync_single(pid)
            kg.close()
        except Exception:
            pass

    return {"message": "批量审核完成", "updated": len(papers)}


@router.post("/papers/batch-delete", summary="批量删除文献（仅超级管理员）")
async def batch_delete_papers(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    db.query(models.KeyProperty).filter(models.KeyProperty.paper_id.in_(request.paper_ids)).delete()
    papers = db.query(models.Paper).filter(models.Paper.id.in_(request.paper_ids)).all()
    for paper in papers:
        db.delete(paper)
    db.commit()
    return {"message": "批量删除完成", "deleted": len(papers)}


# ═══════════════════════════════════════════════
# Key Properties (v2 replacement for records)
# ═══════════════════════════════════════════════

def _kp_to_item(kp: models.KeyProperty) -> dict:
    paper = kp.paper
    sc = kp.superconductor
    return {
        "id": kp.id,
        "paper_id": kp.paper_id,
        "paper_title": paper.title if paper else None,
        "paper_doi": paper.doi if paper else None,
        "paper_year": paper.year if paper else None,
        "material": kp.material,
        "name": kp.name,
        "name_raw": kp.name_raw,
        "value_min": kp.value_min,
        "value_max": kp.value_max,
        "unit": kp.unit,
        "pressure_gpa": kp.pressure_gpa,
        "temperature_k": kp.temperature_k,
        "is_primary": kp.is_primary,
        "article_type": kp.article_type,
        "superconductor_type": kp.superconductor_type,
        "review_status": paper.review_status if paper else None,
        "structure_format": kp.structure_format,
    }


@router.get("/records/all", summary="获取所有物性数据（支持筛选）")
async def get_all_records(
    review_status: Optional[str] = Query(None),
    article_type: Optional[str] = Query(None),
    superconductor_type: Optional[str] = Query(None),
    year_min: Optional[int] = Query(None),
    year_max: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    query = db.query(models.KeyProperty).join(models.Paper)

    if review_status:
        query = query.filter(models.Paper.review_status == review_status)
    if article_type:
        query = query.filter(models.KeyProperty.article_type == article_type)
    if superconductor_type:
        query = query.filter(models.KeyProperty.superconductor_type == superconductor_type)
    if year_min:
        query = query.filter(models.Paper.year >= year_min)
    if year_max:
        query = query.filter(models.Paper.year <= year_max)
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            or_(
                models.Paper.title.ilike(kw),
                models.Paper.doi.ilike(kw),
                models.KeyProperty.material.ilike(kw),
            )
        )

    total = query.count()
    kps = query.order_by(models.KeyProperty.id.desc()).offset(offset).limit(limit).all()
    items = [_kp_to_item(kp) for kp in kps]

    return {
        "items": items,
        "total": total,
        "page_size": limit,
    }
