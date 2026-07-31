"""Crystal structure storage APIs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import crud, models
from backend.database import get_db
from backend.db_helpers import normalize_formula
from backend.security import get_current_admin, get_current_user
from backend.services.structure_storage import (
    approve_structure,
    create_structure,
    reject_structure,
    representative_structure_for,
    serialize_structure,
)


router = APIRouter(prefix="/api/structures", tags=["structures"])


class StructureCreateRequest(BaseModel):
    chemical_formula: str
    pressure_gpa: float
    space_group_symbol: Optional[str] = None
    space_group_number: Optional[int] = None
    structure_format: str
    structure_text: str
    source_type: str
    source_label: Optional[str] = None


class StructureReviewRequest(BaseModel):
    status: str


async def _require_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    return current_user


def _is_admin(user: models.User) -> bool:
    return user.role in {"admin", "superadmin"} and user.is_approved


def _find_superconductor_by_formula(db: Session, formula: str) -> models.Superconductor | None:
    try:
        normalized_formula = normalize_formula(formula)[0]
    except ValueError:
        normalized_formula = None

    filters = [models.Superconductor.chemical_formula == formula]
    if normalized_formula is not None:
        filters.append(models.Superconductor.formula_normalized == normalized_formula)
    return db.query(models.Superconductor).filter(or_(*filters)).first()


@router.post("/")
async def upload_structure(
    request: StructureCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_user),
):
    superconductor = crud.get_or_create_superconductor(db, request.chemical_formula)
    structure = create_structure(
        db,
        superconductor=superconductor,
        pressure_gpa=request.pressure_gpa,
        space_group_symbol=request.space_group_symbol,
        space_group_number=request.space_group_number,
        structure_format=request.structure_format,
        structure_text=request.structure_text,
        source_type=request.source_type,
        source_label=request.source_label,
        created_by_user=current_user,
    )
    db.commit()
    db.refresh(structure)
    return serialize_structure(structure)


@router.post("/{structure_id}/review")
async def review_structure(
    structure_id: int,
    request: StructureReviewRequest,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(get_current_admin),
):
    structure = db.get(models.SuperconductorStructure, structure_id)
    if structure is None:
        raise HTTPException(status_code=404, detail="Structure not found.")

    if request.status == "approved":
        structure = approve_structure(db, structure)
    elif request.status == "rejected":
        structure = reject_structure(structure)
        db.add(structure)
    else:
        raise HTTPException(status_code=400, detail="Review status must be approved or rejected.")

    db.commit()
    db.refresh(structure)
    return serialize_structure(structure)


@router.get("/by-property/{kp_id}")
async def get_structure_by_property(
    kp_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_user),
):
    """v2: 从 key_properties.structure_text 读取结构"""
    kp = db.get(models.KeyProperty, kp_id)
    if kp is None:
        raise HTTPException(status_code=404, detail="Key property not found.")
    if not kp.structure_text:
        raise HTTPException(status_code=404, detail="该物性记录没有关联结构数据")

    # 同时查 superconductors_structures 表
    sc = kp.superconductor
    structure = None
    if sc:
        structure = db.query(models.SuperconductorStructure).filter(
            models.SuperconductorStructure.superconductor_id == sc.id,
            models.SuperconductorStructure.review_status == "approved",
        ).first()

    return {
        "key_property_id": kp.id,
        "material": kp.material,
        "structure_text": kp.structure_text,
        "structure_format": kp.structure_format or "cif",
        "from_table": serialize_structure(structure) if structure else None,
    }


@router.get("/representative")
async def get_representative_structure(
    formula: str,
    space_group: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_user),
):
    superconductor = _find_superconductor_by_formula(db, formula)
    if superconductor is None:
        raise HTTPException(status_code=404, detail="Superconductor not found.")

    structure = representative_structure_for(db, superconductor, space_group=space_group)
    if structure is None:
        raise HTTPException(status_code=404, detail="Structure not found.")
    return serialize_structure(structure)


@router.get("/{structure_id}/raw")
async def download_raw_structure(
    structure_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_user),
):
    structure = db.get(models.SuperconductorStructure, structure_id)
    if structure is None:
        raise HTTPException(status_code=404, detail="Structure not found.")
    if (
        structure.review_status != "approved"
        and structure.created_by_user_id != current_user.id
        and not _is_admin(current_user)
    ):
        raise HTTPException(status_code=403, detail="Structure raw download is not allowed.")

    media_type = "chemical/x-cif" if structure.structure_format == "cif" else "text/plain"
    return Response(content=structure.structure_text, media_type=media_type)
