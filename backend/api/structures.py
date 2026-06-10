"""Crystal structure storage APIs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models
from backend.database import get_db
from backend.security import get_current_user
from backend.services.structure_storage import (
    approve_structure,
    create_structure,
    default_structure_for_record,
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


async def _require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role not in {"admin", "superadmin"} or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


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
    current_user: models.User = Depends(_require_admin),
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


@router.get("/by-record/{record_id}")
async def get_structure_by_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_user),
):
    record = db.get(models.SuperconductorRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Superconductor record not found.")

    structure = default_structure_for_record(db, record)
    if structure is None:
        raise HTTPException(status_code=404, detail="Structure not found.")
    return serialize_structure(structure)


@router.get("/representative")
async def get_representative_structure(
    formula: str,
    space_group: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_user),
):
    superconductor = crud.get_or_create_superconductor(db, formula)
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

    media_type = "chemical/x-cif" if structure.structure_format == "cif" else "text/plain"
    return Response(content=structure.structure_text, media_type=media_type)
