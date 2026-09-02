"""Seed the isolated Issue #51 browser-acceptance environment."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.engine import make_url

from backend.database import SessionLocal
from backend.ingest.upload_tasks import create_task, save_draft, save_state
from backend.models import (
    ChemicalSystem,
    MaterialFamily,
    MaterialState,
    Paper,
    Superconductor,
    User,
)
from backend.security import hash_password


def _require_test_environment() -> str:
    database_url = os.environ.get("DATABASE_URL", "")
    if os.environ.get("ISSUE51_LIVE_ACCEPTANCE") != "1":
        raise RuntimeError("set ISSUE51_LIVE_ACCEPTANCE=1 for the isolated fixture")
    if "issue51_acceptance" not in (make_url(database_url).database or ""):
        raise RuntimeError("refusing to seed a non-Issue-51 database")
    password = os.environ.get("ISSUE51_TEST_PASSWORD", "")
    if len(password) < 10:
        raise RuntimeError("ISSUE51_TEST_PASSWORD must contain at least 10 characters")
    return password


def _create_user(session, *, email: str, username: str, role: str, password: str) -> User:
    existing = session.query(User).filter(User.email == email).one_or_none()
    if existing is not None:
        return existing
    user = User(
        email=email,
        username=username,
        real_name=username,
        password_hash=hash_password(password),
        role=role,
        is_approved=True,
        is_email_verified=True,
        account_status="active",
        username_change_allowed=False,
        session_version=0,
    )
    session.add(user)
    session.flush()
    return user


def main() -> None:
    password = _require_test_environment()
    session = SessionLocal()
    try:
        user = _create_user(
            session,
            email="issue51-user@example.test",
            username="Issue51User",
            role="user",
            password=password,
        )
        admin = _create_user(
            session,
            email="issue51-admin@example.test",
            username="Issue51Admin",
            role="admin",
            password=password,
        )
        superadmin = _create_user(
            session,
            email="issue51-super@example.test",
            username="Issue51Super",
            role="superadmin",
            password=password,
        )

        family = session.query(MaterialFamily).filter_by(code="hydrogen_based").one()
        chemical_system = ChemicalSystem(
            system_key="H-La",
            elements_list=["H", "La"],
            element_count=2,
        )
        session.add(chemical_system)
        session.flush()
        superconductor = Superconductor(
            chemical_system_id=chemical_system.id,
            chemical_formula="LaH10",
            formula_normalized="LaH10",
            composition_key="H10La1",
            display_name="LaH10",
            elements_list=["H", "La"],
            composition={"H": 10, "La": 1},
            element_ratio={"H": 10 / 11, "La": 1 / 11},
        )
        session.add(superconductor)
        session.flush()
        paper = Paper(
            title="Issue #51 live acceptance paper",
            authors=["Acceptance Author"],
            paper_type="experimental",
            review_status="pending",
            content_revision=1,
            uploaded_by_user_id=user.id,
            research_materials=["LaH10"],
        )
        session.add(paper)
        session.flush()
        material_state = MaterialState(
            paper_id=paper.id,
            paper_revision=1,
            superconductor_id=superconductor.id,
            element_count=2,
            material_dimensionality="three_dimensional",
            state_kind="experimental",
        )
        session.add(material_state)
        session.flush()
        session.commit()

        task = create_task(user.id, filename="issue51-live.md", file_kind="text")
        task.update(
            status="ready",
            stage="complete",
            stage_index=5,
            processing_status="completed",
            completed_chunks=1,
            total_chunks=1,
        )
        save_state(task["task_id"], task)
        draft = {
            "paper": {
                "title": "Issue #51 browser draft",
                "authors": ["Acceptance Author"],
                "paper_type": "experimental",
                "research_materials": ["LaH10"],
                "material_families": [
                    {"id": family.id, "name": family.name_zh, "status": "confirmed"}
                ],
            },
            "material_states": [
                {
                    "material": "LaH10",
                    "structure_families": [
                        {"id": 1, "name": "笼状结构", "status": "confirmed", "is_primary": True}
                    ],
                    "element_count": 2,
                    "material_dimensionality": "three_dimensional",
                    "pressure": "150 GPa",
                    "state_kind": "experimental",
                }
            ],
            "classification_evidence": [],
        }
        save_draft(task["task_id"], draft)
        print(
            json.dumps(
                {
                    "emails": [user.email, admin.email, superadmin.email],
                    "task_id": task["task_id"],
                    "paper_id": paper.id,
                },
                ensure_ascii=False,
            )
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
