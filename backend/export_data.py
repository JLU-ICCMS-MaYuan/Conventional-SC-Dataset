"""
Export the redesigned MySQL dataset as JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend import models
from backend.database import SessionLocal


SCHEMA_VERSION = "mysql-redesign-v1"


def _dt(value) -> str | None:
    return value.isoformat() if value else None


def _user_to_dict(user: models.User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "real_name": user.real_name,
        "affiliation": user.affiliation,
        "role": user.role,
        "is_approved": user.is_approved,
        "is_email_verified": user.is_email_verified,
        "approved_at": _dt(user.approved_at),
        "created_at": _dt(user.created_at),
        "updated_at": _dt(user.updated_at),
    }


def _paper_to_dict(paper: models.Paper) -> dict[str, Any]:
    return {
        "id": paper.id,
        "doi": paper.doi,
        "title": paper.title,
        "journal": paper.journal,
        "volume": paper.volume,
        "pages": paper.pages,
        "year": paper.year,
        "abstract": paper.abstract,
        "authors": paper.authors,
        "uploaded_by_email": paper.uploaded_by_user.email if paper.uploaded_by_user else None,
        "reviewed_by_email": paper.reviewed_by_user.email if paper.reviewed_by_user else None,
        "review_status": paper.review_status,
        "reviewed_at": _dt(paper.reviewed_at),
        "review_comment": paper.review_comment,
        "created_at": _dt(paper.created_at),
        "updated_at": _dt(paper.updated_at),
    }


def _record_to_dict(record: models.SuperconductorRecord) -> dict[str, Any]:
    superconductor = record.superconductor
    return {
        "id": record.id,
        "paper_doi": record.paper.doi if record.paper else None,
        "chemical_formula": superconductor.chemical_formula if superconductor else None,
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
        "s_factor": record.s_factor,
        "method": record.method,
        "note": record.note,
        "created_at": _dt(record.created_at),
        "updated_at": _dt(record.updated_at),
    }


def build_export_payload(db: Session) -> dict[str, Any]:
    users = db.query(models.User).order_by(models.User.id).all()
    papers = db.query(models.Paper).order_by(models.Paper.id).all()
    records = db.query(models.SuperconductorRecord).order_by(models.SuperconductorRecord.id).all()
    return {
        "schema_version": SCHEMA_VERSION,
        "users": [_user_to_dict(user) for user in users],
        "papers": [_paper_to_dict(paper) for paper in papers],
        "superconductor_records": [_record_to_dict(record) for record in records],
    }


def export_all_data(output_file: str = "data/data_export.json") -> dict[str, Any]:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        payload = build_export_payload(db)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("✅ 导出完成")
        print(f"   文件位置: {output_path.absolute()}")
        print(f"   用户: {len(payload['users'])} 个")
        print(f"   文献: {len(payload['papers'])} 篇")
        print(f"   超导记录: {len(payload['superconductor_records'])} 条")
        return payload
    finally:
        db.close()


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "data/data_export.json"
    export_all_data(output_path)
