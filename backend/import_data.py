"""
Import JSON data into the redesigned MySQL schema.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend import crud, models
from backend.database import SessionLocal
from backend.export_data import SCHEMA_VERSION


SYSTEM_IMPORT_EMAIL = "import@example.local"


def _parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value)


def _ensure_import_user(db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.email == SYSTEM_IMPORT_EMAIL).first()
    if user:
        return user
    user = models.User(
        email=SYSTEM_IMPORT_EMAIL,
        password_hash="!",
        real_name="Data Import",
        role="admin",
        is_approved=True,
        is_email_verified=True,
    )
    db.add(user)
    db.flush()
    return user


def _upsert_user(db: Session, item: dict[str, Any]) -> models.User:
    user = db.query(models.User).filter(models.User.email == item["email"]).first()
    if not user:
        user = models.User(email=item["email"], password_hash="!")
        db.add(user)
    user.real_name = item.get("real_name") or item["email"]
    user.affiliation = item.get("affiliation")
    user.role = item.get("role") or "user"
    user.is_approved = bool(item.get("is_approved", user.role == "user"))
    user.is_email_verified = bool(item.get("is_email_verified", True))
    user.approved_at = _parse_dt(item.get("approved_at"))
    return user


def _clear_business_data(db: Session) -> None:
    db.query(models.SuperconductorRecord).delete()
    db.query(models.Paper).delete()
    db.query(models.Superconductor).delete()
    db.query(models.ChemicalSystem).delete()
    db.query(models.User).delete()
    db.commit()


def _record_item(db: Session, item: dict[str, Any], paper_by_doi: dict[str, models.Paper]) -> models.SuperconductorRecord | None:
    formula = item.get("chemical_formula")
    if not formula:
        return None
    superconductor = crud.get_or_create_superconductor(db, formula)
    paper = paper_by_doi.get(item.get("paper_doi")) if item.get("paper_doi") else None
    record = models.SuperconductorRecord(
        superconductor_id=superconductor.id,
        paper_id=paper.id if paper else None,
        source_label=item.get("source_label") or ("paper" if paper else "import"),
        pressure_gpa=item["pressure_gpa"],
        space_group_symbol=item.get("space_group_symbol"),
        space_group_number=item.get("space_group_number"),
        crystal_structure=item.get("crystal_structure"),
        thermodynamically_stable=item.get("thermodynamically_stable"),
        dynamically_stable=item.get("dynamically_stable"),
        energy_above_hull=item.get("energy_above_hull"),
        mcmillan_tc=item.get("mcmillan_tc"),
        allen_dynes_tc=item.get("allen_dynes_tc"),
        isotropic_eliashberg_tc=item.get("isotropic_eliashberg_tc"),
        anisotropic_eliashberg_tc=item.get("anisotropic_eliashberg_tc"),
        experimental_tc=item.get("experimental_tc"),
        lambda_value=item.get("lambda_value"),
        omega_log=item.get("omega_log"),
        n_ef_total=item.get("n_ef_total"),
        element_n_ef=item.get("element_n_ef"),
        pseudopotential_type=item.get("pseudopotential_type"),
        pseudopotential_name=item.get("pseudopotential_name"),
        exchange_correlation_functional=item.get("exchange_correlation_functional"),
        calculation_code=item.get("calculation_code"),
        k_grid=item.get("k_grid"),
        q_grid=item.get("q_grid"),
        energy_cutoff_value=item.get("energy_cutoff_value"),
        energy_cutoff_unit=item.get("energy_cutoff_unit"),
        show_in_chart=bool(item.get("show_in_chart", False)),
        s_factor=item.get("s_factor"),
        method=item.get("method"),
        note=item.get("note"),
    )
    db.add(record)
    return record


def import_payload(db: Session, payload: dict[str, Any], clear_existing: bool = False) -> dict[str, int]:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {payload.get('schema_version')}")
    if clear_existing:
        _clear_business_data(db)

    user_by_email: dict[str, models.User] = {}
    for item in payload.get("users", []):
        user = _upsert_user(db, item)
        user_by_email[user.email] = user
    import_user = _ensure_import_user(db)
    db.flush()

    paper_by_doi: dict[str, models.Paper] = {}
    for item in payload.get("papers", []):
        doi = item["doi"]
        paper = db.query(models.Paper).filter(models.Paper.doi == doi).first()
        if not paper:
            uploaded_by = user_by_email.get(item.get("uploaded_by_email")) or import_user
            reviewed_by = user_by_email.get(item.get("reviewed_by_email"))
            paper = models.Paper(
                doi=doi,
                uploaded_by_user_id=uploaded_by.id,
                reviewed_by_user_id=reviewed_by.id if reviewed_by else None,
            )
            db.add(paper)
        paper.title = item.get("title") or f"Imported Paper: {doi}"
        paper.journal = item.get("journal")
        paper.volume = item.get("volume")
        paper.pages = item.get("pages")
        paper.year = item.get("year")
        paper.abstract = item.get("abstract")
        paper.authors = item.get("authors") or []
        paper.review_status = item.get("review_status") or "pending"
        paper.reviewed_at = _parse_dt(item.get("reviewed_at"))
        paper.review_comment = item.get("review_comment")
        db.flush()
        paper_by_doi[paper.doi] = paper

    imported_records = 0
    for item in payload.get("superconductor_records", []):
        if _record_item(db, item, paper_by_doi):
            imported_records += 1

    db.commit()
    return {
        "users": len(user_by_email) + (0 if SYSTEM_IMPORT_EMAIL in user_by_email else 1),
        "papers": len(paper_by_doi),
        "superconductor_records": imported_records,
    }


def import_all_data(input_file: str = "data/data_export.json", clear_existing: bool = False) -> dict[str, int]:
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在: {input_path}")
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        result = import_payload(db, payload, clear_existing=clear_existing)
        print("✅ 导入完成")
        print(f"   用户: {result['users']} 个")
        print(f"   文献: {result['papers']} 篇")
        print(f"   超导记录: {result['superconductor_records']} 条")
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    input_file = "data/data_export.json"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        input_file = sys.argv[1]

    clear = "--clear" in sys.argv
    if clear:
        confirm = input("⚠️  确定要清空现有数据吗？(yes/no): ")
        if confirm.lower() != "yes":
            print("取消操作")
            sys.exit(0)
    import_all_data(input_file, clear_existing=clear)
