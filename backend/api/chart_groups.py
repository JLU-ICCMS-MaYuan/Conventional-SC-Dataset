"""
Chart Group API — 散点图数据点组合管理
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import models
from backend.database import get_db
from backend.security import get_current_user, get_current_user_optional

router = APIRouter(prefix="/api/chart-groups", tags=["图表组合"])


def _group_to_dict(g: models.ChartGroup) -> dict:
    return {
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "is_preset": g.is_preset,
        "is_public": g.is_public,
        "created_by": g.created_by,
        "creator_name": g.creator.real_name if g.creator else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
        "item_count": len(g.items),
        "items": [_item_to_dict(it) for it in g.items],
    }


def _item_to_dict(it: models.ChartGroupItem) -> dict:
    if it.key_property_id and it.key_property:
        kp = it.key_property
        return {
            "id": it.id,
            "sort_order": it.sort_order,
            "source": "kp",
            "key_property_id": kp.id,
            "material": kp.material,
            "tc": kp.value_max,
            "pressure": kp.pressure_gpa,
            "type": kp.superconductor_type,
            "year": it.key_property.paper.year if it.key_property.paper else None,
            "doi": it.key_property.paper.doi if it.key_property.paper else None,
            "article_type": kp.article_type,
        }
    else:
        return {
            "id": it.id,
            "sort_order": it.sort_order,
            "source": "custom",
            "key_property_id": None,
            "material": it.custom_label,
            "tc": it.custom_tc,
            "pressure": it.custom_pressure,
            "type": it.custom_type,
            "year": it.custom_year,
            "doi": None,
            "article_type": it.custom_article_type,
        }


def _can_edit(g: models.ChartGroup, user: models.User) -> bool:
    if user.role == "superadmin":
        return True
    if user.role == "admin":
        return True
    if g.created_by == user.id:
        return True
    return False


def _can_set_public(user: models.User) -> bool:
    return user.role in ("admin", "superadmin")


def _can_delete(g: models.ChartGroup, user: models.User) -> bool:
    if user.role == "superadmin":
        return True
    if g.created_by == user.id:
        return True
    return False


class ItemIn(BaseModel):
    key_property_id: Optional[int] = None
    custom_label: Optional[str] = None
    custom_tc: Optional[float] = None
    custom_pressure: Optional[float] = None
    custom_type: Optional[str] = None
    custom_article_type: Optional[str] = None
    custom_year: Optional[int] = None


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    items: list[ItemIn] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[list[ItemIn]] = None


# ── Routes ──

@router.get("", summary="列表（公开+预设+自己的）")
def list_groups(db: Session = Depends(get_db),
                current_user: models.User | None = Depends(get_current_user_optional)):
    if current_user:
        query = db.query(models.ChartGroup).filter(
            (models.ChartGroup.is_public == True) |
            (models.ChartGroup.is_preset == True) |
            (models.ChartGroup.created_by == current_user.id)
        )
    else:
        query = db.query(models.ChartGroup).filter(
            (models.ChartGroup.is_public == True) |
            (models.ChartGroup.is_preset == True)
        )
    groups = query.order_by(models.ChartGroup.is_preset.desc(), models.ChartGroup.updated_at.desc()).all()
    return [_group_to_dict(g) for g in groups]


@router.post("", summary="创建组合")
def create_group(body: GroupCreate, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user)):
    g = models.ChartGroup(
        name=body.name, description=body.description,
        is_preset=False, is_public=False, created_by=current_user.id,
    )
    db.add(g)
    db.flush()
    for i, item in enumerate(body.items):
        db.add(models.ChartGroupItem(
            group_id=g.id, sort_order=i,
            key_property_id=item.key_property_id,
            custom_label=item.custom_label,
            custom_tc=item.custom_tc,
            custom_pressure=item.custom_pressure,
            custom_type=item.custom_type,
            custom_article_type=item.custom_article_type,
            custom_year=item.custom_year,
        ))
    db.commit()
    db.refresh(g)
    return _group_to_dict(g)


@router.post("/import", summary="从 JSON 导入组合")
def import_group(body: dict, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user)):
    g = models.ChartGroup(
        name=body.get("name", "导入的组合"),
        description=body.get("description"),
        is_preset=False, is_public=False, created_by=current_user.id,
    )
    db.add(g)
    db.flush()
    for i, item in enumerate(body.get("items", [])):
        db.add(models.ChartGroupItem(
            group_id=g.id, sort_order=i,
            key_property_id=item.get("key_property_id") if item.get("type") == "kp" else None,
            custom_label=item.get("custom_label"),
            custom_tc=item.get("custom_tc"),
            custom_pressure=item.get("custom_pressure"),
            custom_type=item.get("custom_type"),
            custom_article_type=item.get("custom_article_type"),
            custom_year=item.get("custom_year"),
        ))
    db.commit()
    db.refresh(g)
    return _group_to_dict(g)


@router.get("/search", summary="搜索可加入组合的 key_properties")
def search_kps(q: str = Query(min_length=1), limit: int = 20,
               db: Session = Depends(get_db)):
    rows = db.query(models.KeyProperty).filter(
        models.KeyProperty.material.like(f"%{q}%")
    ).limit(limit).all()
    return [
        {
            "id": kp.id,
            "material": kp.material,
            "name": kp.name,
            "value_max": kp.value_max,
            "value_min": kp.value_min,
            "unit": kp.unit,
            "pressure_gpa": kp.pressure_gpa,
            "superconductor_type": kp.superconductor_type,
            "article_type": kp.article_type,
        }
        for kp in rows
    ]


@router.get("/{group_id}", summary="组合详情")
def get_group(group_id: int, db: Session = Depends(get_db),
              current_user: models.User = Depends(get_current_user)):
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    return _group_to_dict(g)


@router.put("/{group_id}", summary="更新组合")
def update_group(group_id: int, body: GroupUpdate, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user)):
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    if not _can_edit(g, current_user):
        raise HTTPException(status_code=403, detail="无权编辑此组合")
    if body.name is not None:
        g.name = body.name
    if body.description is not None:
        g.description = body.description
    if body.items is not None:
        db.query(models.ChartGroupItem).filter(
            models.ChartGroupItem.group_id == group_id
        ).delete()
        for i, item in enumerate(body.items):
            db.add(models.ChartGroupItem(
                group_id=g.id, sort_order=i,
                key_property_id=item.key_property_id,
                custom_label=item.custom_label,
                custom_tc=item.custom_tc,
                custom_pressure=item.custom_pressure,
                custom_type=item.custom_type,
            custom_article_type=item.custom_article_type,
                custom_year=item.custom_year,
            ))
    g.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(g)
    return _group_to_dict(g)


@router.delete("/{group_id}", summary="删除组合")
def delete_group(group_id: int, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_user)):
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    if not _can_delete(g, current_user):
        raise HTTPException(status_code=403, detail="无权删除此组合")
    db.delete(g)
    db.commit()
    return {"message": "已删除"}


@router.post("/{group_id}/copy", summary="复制组合")
def copy_group(group_id: int, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user)):
    src = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="组合不存在")
    g = models.ChartGroup(
        name=f"{src.name} (副本)", description=src.description,
        is_preset=False, is_public=False, created_by=current_user.id,
    )
    db.add(g)
    db.flush()
    for item in src.items:
        db.add(models.ChartGroupItem(
            group_id=g.id, sort_order=item.sort_order,
            key_property_id=item.key_property_id,
            custom_label=item.custom_label,
            custom_tc=item.custom_tc,
            custom_pressure=item.custom_pressure,
            custom_type=item.custom_type,
            custom_article_type=item.custom_article_type,
            custom_year=item.custom_year,
        ))
    db.commit()
    db.refresh(g)
    return _group_to_dict(g)


@router.get("/{group_id}/export", summary="导出组合 JSON")
def export_group(group_id: int, db: Session = Depends(get_db)):
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    return {
        "name": g.name,
        "description": g.description,
        "items": [
            {
                "type": "kp" if it.key_property_id else "custom",
                "key_property_id": it.key_property_id,
                "custom_label": it.custom_label,
                "custom_tc": it.custom_tc,
                "custom_pressure": it.custom_pressure,
                "custom_type": it.custom_type, "custom_article_type": it.custom_article_type,
                "custom_year": it.custom_year,
            }
            for it in g.items
        ],
    }


@router.patch("/{group_id}/public", summary="管理员切换公开状态")
def toggle_public(group_id: int, body: dict, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    if not _can_set_public(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可设置公开")
    g = db.query(models.ChartGroup).filter(models.ChartGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="组合不存在")
    g.is_public = body.get("is_public", not g.is_public)
    db.commit()
    return {"message": "已更新", "is_public": g.is_public}
