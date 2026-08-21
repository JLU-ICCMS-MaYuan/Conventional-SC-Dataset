from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend import models
from backend.database import SessionLocal


SCHEMA_VERSION = 2


def _user_email(user_id: int | None, users: dict[int, models.User]) -> str | None:
    if user_id is None:
        return None
    user = users.get(user_id)
    return user.email if user else None


def build_export_payload(db: Session) -> dict[str, Any]:
    users = {user.id: user for user in db.query(models.User).order_by(models.User.id).all()}
    papers = db.query(models.Paper).order_by(models.Paper.id).all()
    records = db.query(models.SuperconductorRecord).order_by(models.SuperconductorRecord.id).all()
    structures = db.query(models.SuperconductorStructure).order_by(models.SuperconductorStructure.id).all()

    return {
        "schema_version": SCHEMA_VERSION,
        "users": [
            {
                "email": user.email,
                "username": user.username,
                "username_change_allowed": user.username_change_allowed,
                "real_name": user.real_name,
                "role": user.role,
                "is_approved": user.is_approved,
                "is_email_verified": user.is_email_verified,
            }
            for user in users.values()
        ],
        "papers": [
            {
                "doi": paper.doi,
                "title": paper.title,
                "authors": paper.authors,
                "journal": paper.journal,
                "volume": paper.volume,
                "pages": paper.pages,
                "year": paper.year,
                "abstract": paper.abstract,
                "review_status": paper.review_status,
                "uploaded_by_email": _user_email(paper.uploaded_by_user_id, users),
            }
            for paper in papers
        ],
        "superconductor_records": [
            {
                "paper_doi": record.paper.doi if record.paper else None,
                "chemical_formula": record.superconductor.chemical_formula,
                "source_label": record.source_label,
                "pressure_gpa": record.pressure_gpa,
                "space_group_symbol": record.space_group_symbol,
                "space_group_number": record.space_group_number,
                "crystal_structure": record.crystal_structure,
                "mcmillan_tc": record.mcmillan_tc,
                "allen_dynes_tc": record.allen_dynes_tc,
                "isotropic_eliashberg_tc": record.isotropic_eliashberg_tc,
                "anisotropic_eliashberg_tc": record.anisotropic_eliashberg_tc,
                "experimental_tc": record.experimental_tc,
                "lambda_value": record.lambda_value,
                "omega_log": record.omega_log,
                "n_ef_total": record.n_ef_total,
                "show_in_chart": record.show_in_chart,
            }
            for record in records
        ],
        "superconductors_structures": [
            {
                "chemical_formula": structure.superconductor.chemical_formula,
                "pressure_gpa": structure.pressure_gpa,
                "space_group_symbol": structure.space_group_symbol,
                "space_group_number": structure.space_group_number,
                "structure_format": structure.structure_format,
                "structure_text": structure.structure_text,
                "structure_hash": structure.structure_hash,
                "atom_count": structure.atom_count,
                "elements_list": structure.elements_list,
                "cell_parameters": structure.cell_parameters,
                "volume": structure.volume,
                "review_status": structure.review_status,
                "is_default": structure.is_default,
                "source_type": structure.source_type,
                "source_label": structure.source_label,
                "created_by_email": _user_email(structure.created_by_user_id, users),
            }
            for structure in structures
        ],
    }


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data_export.json")
    db = SessionLocal()
    try:
        payload = build_export_payload(db)
    finally:
        db.close()
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
