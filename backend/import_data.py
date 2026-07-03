from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend import crud, models
from backend.database import SessionLocal


def _clear_business_data(db: Session) -> None:
    db.query(models.SuperconductorStructure).delete()
    db.query(models.SuperconductorRecord).delete()
    db.query(models.Paper).delete()
    db.query(models.Superconductor).delete()
    db.query(models.ChemicalSystem).delete()
    db.query(models.User).delete()
    db.flush()


def _user_by_email(db: Session, email: str | None) -> models.User | None:
    if not email:
        return None
    return db.query(models.User).filter_by(email=email).first()


def _paper_by_doi(db: Session, doi: str | None) -> models.Paper | None:
    if not doi:
        return None
    return db.query(models.Paper).filter_by(doi=doi).first()


def _import_users(db: Session, users: list[dict[str, Any]]) -> int:
    count = 0
    for item in users:
        email = item.get("email")
        if not email:
            continue
        user = _user_by_email(db, email)
        if user is None:
            user = models.User(email=email, password_hash=item.get("password_hash") or "!")
            db.add(user)
            count += 1
        user.real_name = item.get("real_name") or email
        user.role = item.get("role") or "user"
        user.is_approved = bool(item.get("is_approved", False))
        user.is_email_verified = bool(item.get("is_email_verified", False))
    db.flush()
    return count


def _import_papers(db: Session, papers: list[dict[str, Any]]) -> int:
    count = 0
    for item in papers:
        doi = item.get("doi")
        paper = _paper_by_doi(db, doi) if doi else None
        if paper is None:
            paper = models.Paper(doi=doi)
            db.add(paper)
            count += 1
        uploader = _user_by_email(db, item.get("uploaded_by_email"))
        paper.title = item.get("title")
        paper.authors = item.get("authors")
        paper.journal = item.get("journal")
        paper.volume = item.get("volume")
        paper.pages = item.get("pages")
        paper.year = item.get("year")
        paper.abstract = item.get("abstract")
        paper.review_status = item.get("review_status") or "pending"
        paper.uploaded_by_user_id = uploader.id if uploader else None
    db.flush()
    return count


def _import_records(db: Session, records: list[dict[str, Any]]) -> int:
    count = 0
    for item in records:
        formula = item.get("chemical_formula")
        if not formula:
            continue
        superconductor = crud.get_or_create_superconductor(db, formula)
        paper = _paper_by_doi(db, item.get("paper_doi"))
        db.add(
            models.SuperconductorRecord(
                superconductor_id=superconductor.id,
                paper_id=paper.id if paper else None,
                source_label=item.get("source_label") or "import",
                pressure_gpa=item.get("pressure_gpa") or 0,
                space_group_symbol=item.get("space_group_symbol"),
                space_group_number=item.get("space_group_number"),
                crystal_structure=item.get("crystal_structure"),
                mcmillan_tc=item.get("mcmillan_tc"),
                allen_dynes_tc=item.get("allen_dynes_tc"),
                isotropic_eliashberg_tc=item.get("isotropic_eliashberg_tc"),
                anisotropic_eliashberg_tc=item.get("anisotropic_eliashberg_tc"),
                experimental_tc=item.get("experimental_tc"),
                lambda_value=item.get("lambda_value"),
                omega_log=item.get("omega_log"),
                n_ef_total=item.get("n_ef_total"),
                show_in_chart=bool(item.get("show_in_chart", False)),
            )
        )
        count += 1
    db.flush()
    return count


def _require_structure_field(item: dict[str, Any], index: int, field: str) -> Any:
    value = item.get(field)
    if value in (None, ""):
        raise ValueError(f"superconductors_structures[{index}] 缺少 {field}")
    return value


def _import_structures(db: Session, structures: list[dict[str, Any]]) -> int:
    count = 0
    for index, item in enumerate(structures):
        formula = _require_structure_field(item, index, "chemical_formula")
        structure_text = _require_structure_field(item, index, "structure_text")
        structure_format = _require_structure_field(item, index, "structure_format")
        structure_hash = _require_structure_field(item, index, "structure_hash")
        superconductor = crud.get_or_create_superconductor(db, formula)
        creator = _user_by_email(db, item.get("created_by_email"))
        db.add(
            models.SuperconductorStructure(
                superconductor_id=superconductor.id,
                pressure_gpa=item.get("pressure_gpa") or 0,
                space_group_symbol=item.get("space_group_symbol"),
                space_group_number=item.get("space_group_number"),
                structure_format=structure_format,
                structure_text=structure_text,
                structure_hash=structure_hash,
                atom_count=item.get("atom_count"),
                elements_list=item.get("elements_list"),
                cell_parameters=item.get("cell_parameters"),
                volume=item.get("volume"),
                review_status=item.get("review_status") or "pending",
                is_default=bool(item.get("is_default", False)),
                source_type=item.get("source_type") or "import",
                source_label=item.get("source_label"),
                created_by_user_id=creator.id if creator else None,
            )
        )
        count += 1
    db.flush()
    return count


def import_payload(db: Session, payload: dict[str, Any], *, clear_existing: bool = False) -> dict[str, int]:
    if clear_existing:
        _clear_business_data(db)

    result = {
        "users": _import_users(db, payload.get("users") or []),
        "papers": 0,
        "superconductor_records": 0,
        "superconductors_structures": 0,
    }
    result["papers"] = _import_papers(db, payload.get("papers") or [])
    result["superconductor_records"] = _import_records(db, payload.get("superconductor_records") or [])
    result["superconductors_structures"] = _import_structures(db, payload.get("superconductors_structures") or [])
    db.commit()
    return result


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m backend.import_data <json_path> [--clear]")
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        result = import_payload(db, payload, clear_existing="--clear" in sys.argv[2:])
    finally:
        db.close()
    print(result)


if __name__ == "__main__":
    main()
