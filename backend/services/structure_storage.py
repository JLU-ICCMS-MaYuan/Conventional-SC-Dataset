"""Crystal structure validation, persistence, and selection helpers."""

from __future__ import annotations

import hashlib
from io import StringIO
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend import models


ALLOWED_STRUCTURE_FORMATS = {"cif", "poscar"}
APPROVED_STATUS = "approved"
PENDING_STATUS = "pending"
REJECTED_STATUS = "rejected"


def _normalize_structure_format(structure_format: str) -> str:
    normalized = (structure_format or "").strip().lower()
    if normalized not in ALLOWED_STRUCTURE_FORMATS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported structure format. Supported formats: cif, poscar.",
        )
    return normalized


def _read_atoms(structure_format: str, structure_text: str):
    try:
        from ase.io import read
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="ASE is required to parse crystal structure payloads.",
        ) from exc

    ase_format = "vasp" if structure_format == "poscar" else "cif"
    try:
        return read(StringIO(structure_text), format=ase_format)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to parse {structure_format} structure payload.",
        ) from exc


def validate_structure_payload(structure_format: str, structure_text: str) -> dict[str, Any]:
    normalized_format = _normalize_structure_format(structure_format)
    if not structure_text or not structure_text.strip():
        raise HTTPException(status_code=400, detail="Structure text cannot be blank.")

    atoms = _read_atoms(normalized_format, structure_text)
    cellpar = atoms.cell.cellpar()
    structure_hash = hashlib.sha256(
        f"{normalized_format}\n{structure_text.strip()}".encode("utf-8")
    ).hexdigest()

    return {
        "structure_format": normalized_format,
        "structure_hash": structure_hash,
        "atom_count": len(atoms),
        "elements_list": sorted(set(atoms.get_chemical_symbols())),
        "cell_parameters": {
            "a": float(cellpar[0]),
            "b": float(cellpar[1]),
            "c": float(cellpar[2]),
            "alpha": float(cellpar[3]),
            "beta": float(cellpar[4]),
            "gamma": float(cellpar[5]),
        },
        "volume": float(atoms.get_volume()),
    }


def create_structure(
    db: Session,
    *,
    superconductor: models.Superconductor,
    pressure_gpa: float,
    space_group_symbol: str | None,
    space_group_number: int | None,
    structure_format: str,
    structure_text: str,
    source_type: str,
    source_label: str | None = None,
    created_by_user: models.User | None = None,
) -> models.SuperconductorStructure:
    metadata = validate_structure_payload(structure_format, structure_text)
    structure = models.SuperconductorStructure(
        superconductor_id=superconductor.id,
        superconductor=superconductor,
        pressure_gpa=pressure_gpa,
        space_group_symbol=space_group_symbol,
        space_group_number=space_group_number,
        structure_format=metadata["structure_format"],
        structure_text=structure_text,
        structure_hash=metadata["structure_hash"],
        atom_count=metadata["atom_count"],
        elements_list=metadata["elements_list"],
        cell_parameters=metadata["cell_parameters"],
        volume=metadata["volume"],
        review_status=PENDING_STATUS,
        is_default=False,
        source_type=source_type,
        source_label=source_label,
        created_by_user=created_by_user,
        created_by_user_id=created_by_user.id if created_by_user else None,
    )
    db.add(structure)
    return structure


def _nullable_match(column, value):
    if value is None:
        return column.is_(None)
    return column == value


def _identity_filters(structure: models.SuperconductorStructure):
    return (
        models.SuperconductorStructure.superconductor_id == structure.superconductor_id,
        models.SuperconductorStructure.pressure_gpa == structure.pressure_gpa,
        _nullable_match(
            models.SuperconductorStructure.space_group_symbol,
            structure.space_group_symbol,
        ),
        _nullable_match(
            models.SuperconductorStructure.space_group_number,
            structure.space_group_number,
        ),
    )


def _same_identity(
    left: models.SuperconductorStructure,
    right: models.SuperconductorStructure,
) -> bool:
    return (
        left.superconductor_id == right.superconductor_id
        and left.pressure_gpa == right.pressure_gpa
        and left.space_group_symbol == right.space_group_symbol
        and left.space_group_number == right.space_group_number
    )


def _clear_session_defaults(db: Session, structure: models.SuperconductorStructure) -> None:
    candidates = list(db.identity_map.values()) + list(db.new)
    for candidate in candidates:
        if (
            candidate is not structure
            and isinstance(candidate, models.SuperconductorStructure)
            and _same_identity(candidate, structure)
        ):
            candidate.is_default = False


def approve_structure(db: Session, structure: models.SuperconductorStructure) -> models.SuperconductorStructure:
    db.query(models.SuperconductorStructure).filter(*_identity_filters(structure)).update(
        {"is_default": False},
        synchronize_session="fetch",
    )
    _clear_session_defaults(db, structure)
    structure.review_status = APPROVED_STATUS
    structure.is_default = True
    db.add(structure)
    return structure


def reject_structure(structure: models.SuperconductorStructure) -> models.SuperconductorStructure:
    structure.review_status = REJECTED_STATUS
    structure.is_default = False
    return structure


def representative_structure_for(
    db: Session,
    superconductor: models.Superconductor,
    space_group: str | None = None,
) -> models.SuperconductorStructure | None:
    query = db.query(models.SuperconductorStructure).filter(
        models.SuperconductorStructure.superconductor_id == superconductor.id,
        models.SuperconductorStructure.review_status == APPROVED_STATUS,
    )
    if space_group:
        query = query.filter(models.SuperconductorStructure.space_group_symbol == space_group)

    return (
        query.order_by(
            desc(models.SuperconductorStructure.is_default),
            models.SuperconductorStructure.pressure_gpa.asc(),
            models.SuperconductorStructure.created_at.desc(),
            models.SuperconductorStructure.id.desc(),
        )
        .first()
    )


def default_structure_for_record(
    db: Session,
    record: models.SuperconductorRecord,
) -> models.SuperconductorStructure | None:
    return (
        db.query(models.SuperconductorStructure)
        .filter(
            models.SuperconductorStructure.superconductor_id == record.superconductor_id,
            models.SuperconductorStructure.pressure_gpa == record.pressure_gpa,
            _nullable_match(
                models.SuperconductorStructure.space_group_symbol,
                record.space_group_symbol,
            ),
            _nullable_match(
                models.SuperconductorStructure.space_group_number,
                record.space_group_number,
            ),
            models.SuperconductorStructure.review_status == APPROVED_STATUS,
        )
        .order_by(
            desc(models.SuperconductorStructure.is_default),
            models.SuperconductorStructure.created_at.desc(),
            models.SuperconductorStructure.id.desc(),
        )
        .first()
    )


def _serialize_datetime(value):
    if value is None:
        return None
    return value.isoformat()


def serialize_structure(
    structure: models.SuperconductorStructure,
    include_text: bool = False,
) -> dict[str, Any]:
    payload = {
        "id": structure.id,
        "superconductor_id": structure.superconductor_id,
        "chemical_formula": structure.superconductor.chemical_formula
        if structure.superconductor
        else None,
        "pressure_gpa": structure.pressure_gpa,
        "space_group_symbol": structure.space_group_symbol,
        "space_group_number": structure.space_group_number,
        "structure_format": structure.structure_format,
        "structure_hash": structure.structure_hash,
        "atom_count": structure.atom_count,
        "elements_list": structure.elements_list,
        "cell_parameters": structure.cell_parameters,
        "volume": structure.volume,
        "review_status": structure.review_status,
        "is_default": structure.is_default,
        "source_type": structure.source_type,
        "source_label": structure.source_label,
        "created_by_user_id": structure.created_by_user_id,
        "created_at": _serialize_datetime(structure.created_at),
        "updated_at": _serialize_datetime(structure.updated_at),
    }
    if include_text:
        payload["structure_text"] = structure.structure_text
    return payload
