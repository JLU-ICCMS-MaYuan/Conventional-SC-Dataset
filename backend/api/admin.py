"""
Admin APIs for users, paper review, and chart visibility.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
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


class ChartVisibilityRequest(BaseModel):
    paper_ids: list[int]
    show: bool


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


def _record_to_dict(record: models.SuperconductorRecord) -> dict:
    return {
        "id": record.id,
        "superconductor_id": record.superconductor_id,
        "paper_id": record.paper_id,
        "chemical_formula": record.superconductor.chemical_formula if record.superconductor else None,
        "source_label": record.source_label,
        "pressure_gpa": record.pressure_gpa,
        "space_group_symbol": record.space_group_symbol,
        "space_group_number": record.space_group_number,
        "crystal_structure": record.crystal_structure,
        "thermodynamically_stable": record.thermodynamically_stable,
        "dynamically_stable": record.dynamically_stable,
        "energy_above_hull": record.energy_above_hull,
        "mcmillan_tc": record.mcmillan_tc,
        "allen_dynes_tc": record.allen_dynes_tc,
        "isotropic_eliashberg_tc": record.isotropic_eliashberg_tc,
        "anisotropic_eliashberg_tc": record.anisotropic_eliashberg_tc,
        "experimental_tc": record.experimental_tc,
        "lambda_value": record.lambda_value,
        "omega_log": record.omega_log,
        "n_ef_total": record.n_ef_total,
        "element_n_ef": record.element_n_ef,
        "pseudopotential_type": record.pseudopotential_type,
        "pseudopotential_name": record.pseudopotential_name,
        "exchange_correlation_functional": record.exchange_correlation_functional,
        "calculation_code": record.calculation_code,
        "k_grid": record.k_grid,
        "q_grid": record.q_grid,
        "energy_cutoff_value": record.energy_cutoff_value,
        "energy_cutoff_unit": record.energy_cutoff_unit,
        "show_in_chart": record.show_in_chart,
        "article_type": record.article_type,
        "superconductor_type": record.superconductor_type,
        "s_factor": record.s_factor,
        "method": record.method,
        "note": record.note,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _paper_to_dict(paper: models.Paper, include_records: bool = False) -> dict:
    reviewer = paper.reviewed_by_user
    uploader = paper.uploaded_by_user
    first_record = paper.records[0] if paper.records else None
    first_sc = first_record.superconductor if first_record else None
    # 聚合 records 中的类型信息
    article_types = list({r.article_type for r in paper.records if r.article_type})
    sc_types = list({r.superconductor_type for r in paper.records if r.superconductor_type})
    s_factors = [r.s_factor for r in paper.records if r.s_factor is not None]
    payload = {
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
        "record_count": len(paper.records),
        "show_in_chart": any(record.show_in_chart for record in paper.records),
        "compound_symbols": "-".join(first_sc.elements_list) if first_sc else None,
        "article_types": article_types,
        "superconductor_types": sc_types,
        "s_factor": round(sum(s_factors) / len(s_factors), 2) if s_factors else None,
    }
    if include_records:
        payload["records"] = [_record_to_dict(record) for record in paper.records]
    return payload


def _paper_query(
    db: Session,
    *,
    status_filter: Optional[str] = None,
    keyword: Optional[str] = None,
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
    if year_min is not None:
        query = query.filter(models.Paper.year >= year_min)
    if year_max is not None:
        query = query.filter(models.Paper.year <= year_max)
    return query


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
    return _paper_to_dict(paper, include_records=True)


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
    for field in ("doi", "title", "authors", "journal", "volume", "pages", "year", "abstract", "review_comment", "review_status", "show_in_chart"):
        if field in payload:
            setattr(paper, field, payload[field])
    if "records" in payload and isinstance(payload["records"], list):
        for rd in payload["records"]:
            rid = rd.get("id")
            if rid:
                rec = db.query(models.SuperconductorRecord).filter_by(id=rid, paper_id=paper.id).first()
                if rec:
                    for rf in ("chemical_formula", "source_label", "pressure_gpa", "space_group_symbol",
                               "space_group_number", "crystal_structure", "thermodynamically_stable",
                               "dynamically_stable", "energy_above_hull", "mcmillan_tc", "allen_dynes_tc",
                               "isotropic_eliashberg_tc", "anisotropic_eliashberg_tc", "experimental_tc",
                               "lambda_value", "omega_log", "n_ef_total", "element_n_ef",
                               "pseudopotential_type", "pseudopotential_name",
                               "exchange_correlation_functional", "calculation_code",
                               "k_grid", "q_grid", "energy_cutoff_value", "energy_cutoff_unit",
                               "show_in_chart", "article_type", "superconductor_type",
                               "s_factor", "method", "note"):
                        if rf in rd:
                            setattr(rec, rf, rd[rf])
    db.commit()
    return {"message": "文献信息已更新", "paper": _paper_to_dict(paper, include_records=True)}


@router.delete("/papers/{paper_id}", summary="删除文献（仅超级管理员）")
async def delete_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")
    for record in paper.records:
        db.delete(record)
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
    return {"message": "批量审核完成", "updated": len(papers)}


@router.post("/papers/batch-chart-visibility", summary="批量设置图表显示")
async def batch_chart_visibility(
    request: ChartVisibilityRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    records = db.query(models.SuperconductorRecord).filter(models.SuperconductorRecord.paper_id.in_(request.paper_ids)).all()
    for record in records:
        record.show_in_chart = request.show
    db.commit()
    return {"message": "图表显示状态已更新", "updated": len(records)}


@router.post("/papers/batch-delete", summary="批量删除文献（仅超级管理员）")
async def batch_delete_papers(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_superadmin),
):
    papers = db.query(models.Paper).filter(models.Paper.id.in_(request.paper_ids)).all()
    for paper in papers:
        for record in paper.records:
            db.delete(record)
        db.delete(paper)
    db.commit()
    return {"message": "批量删除完成", "deleted": len(papers)}


@router.get("/papers/{paper_id}/images", summary="获取文献的所有图片")
async def get_paper_images(paper_id: int):
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="文献图片存储已下线")


@router.delete("/papers/{paper_id}/images/{image_id}", summary="删除文献截图")
async def delete_paper_image(paper_id: int, image_id: int):
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="文献图片存储已下线")
