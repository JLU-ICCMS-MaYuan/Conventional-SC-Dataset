# Crystal Structure Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent CIF/POSCAR crystal structure storage in `superconductors_structures`, with ASE validation, default-version rules, representative lookup, raw download, and import/export support.

**Architecture:** Store real structure text in a new `SuperconductorStructure` model linked to `Superconductor`. Keep `SuperconductorRecord` as the physical-data table and resolve structures by `superconductor_id + space_group + pressure_gpa`, with optional future `structure_id` linkage left out of the first implementation. Put validation/default-selection logic in a small service module used by API routes and tests.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest, ASE, existing repository helpers in `backend.crud`.

---

## File Structure

- Modify `requirements.txt`: add `ase` as a runtime dependency.
- Modify `backend/models.py`: add `SuperconductorStructure` SQLAlchemy model and relationships.
- Create `alembic/versions/20260610_0002_add_superconductors_structures.py`: create/drop the new table and indexes.
- Create `backend/services/structure_storage.py`: validate format/text with ASE, compute hashes, choose defaults, serialize structures.
- Create `backend/api/structures.py`: expose upload, record lookup, representative lookup, raw download, and review endpoint.
- Modify `backend/main.py`: include the new structures router.
- Modify `backend/export_data.py`: export `superconductors_structures`.
- Modify `backend/import_data.py`: import `superconductors_structures`.
- Modify `backend/schemas.py`: add request/response schemas for structure API if route-local models become too large; otherwise keep route-local Pydantic models.
- Modify `docs/business-overview.md`: document the new crystal structure storage module as implemented behavior.
- Modify `docs/business-paper-ingestion.md`: document how paper ingestion can relate to stored structures.
- Create `tests/test_structure_storage.py`: service-level tests for validation, defaults, representative selection.
- Create `tests/test_structures_api.py`: API tests for upload, representative lookup, raw download, review behavior.
- Modify `tests/test_model_metadata.py`: expect the new table and verify key columns/foreign keys.
- Modify `tests/test_import_export.py`: cover import/export of structures.

## Scope Notes

- First implementation supports only `cif` and `poscar`.
- First implementation stores original structure text plus minimal metadata. It does not add a `structure_id` foreign key to `superconductor_records`.
- First implementation allows repeated `structure_hash` values and keeps source provenance.
- Uploads create `pending` structures. Admin review can approve and make the structure default.

---

### Task 1: Dependency And Metadata Contract

**Files:**
- Modify: `requirements.txt`
- Modify: `tests/test_model_metadata.py`
- Modify: `backend/models.py`

- [ ] **Step 1: Write failing metadata tests**

Replace `EXPECTED_TABLES` in `tests/test_model_metadata.py` with:

```python
EXPECTED_TABLES = {
    "periodic_table_elements",
    "chemical_systems",
    "superconductors",
    "papers",
    "users",
    "superconductor_records",
    "superconductors_structures",
}
```

Append these tests to `tests/test_model_metadata.py`:

```python
def test_superconductors_structures_table_contract():
    structures = Base.metadata.tables["superconductors_structures"]

    assert structures.columns["superconductor_id"].nullable is False
    assert structures.columns["pressure_gpa"].nullable is False
    assert structures.columns["structure_format"].nullable is False
    assert structures.columns["structure_text"].nullable is False
    assert structures.columns["structure_hash"].nullable is False
    assert structures.columns["review_status"].nullable is False
    assert structures.columns["is_default"].nullable is False
    assert structures.columns["source_type"].nullable is False
    assert isinstance(structures.columns["pressure_gpa"].type, Float)
    assert isinstance(structures.columns["structure_text"].type, Text)
    assert isinstance(structures.columns["is_default"].type, Boolean)


def test_superconductors_structures_foreign_keys_are_declared():
    structures = Base.metadata.tables["superconductors_structures"]

    assert {fk.column.table.name for fk in structures.columns["superconductor_id"].foreign_keys} == {"superconductors"}
    assert {fk.column.table.name for fk in structures.columns["created_by_user_id"].foreign_keys} == {"users"}
```

- [ ] **Step 2: Run metadata tests and verify failure**

Run:

```bash
pytest tests/test_model_metadata.py -v
```

Expected: fail because `superconductors_structures` is not in SQLAlchemy metadata.

- [ ] **Step 3: Add ASE dependency**

Add this line under the tools or numeric/scientific dependency section in `requirements.txt`:

```text
ase==3.22.1
```

- [ ] **Step 4: Add model**

In `backend/models.py`, add this relationship to `Superconductor`:

```python
structures = relationship("SuperconductorStructure", back_populates="superconductor")
```

Add this relationship to `User`:

```python
created_structures = relationship(
    "SuperconductorStructure",
    back_populates="created_by_user",
    foreign_keys="SuperconductorStructure.created_by_user_id",
)
```

Append this model after `SuperconductorRecord`:

```python
class SuperconductorStructure(Base):
    __tablename__ = "superconductors_structures"

    id = Column(Integer, primary_key=True)
    superconductor_id = Column(Integer, ForeignKey("superconductors.id"), nullable=False, index=True)
    pressure_gpa = Column(Float, nullable=False, index=True)
    space_group_symbol = Column(String(100), index=True)
    space_group_number = Column(Integer, index=True)
    structure_format = Column(String(20), nullable=False, index=True)
    structure_text = Column(Text, nullable=False)
    structure_hash = Column(String(64), nullable=False, index=True)
    atom_count = Column(Integer)
    elements_list = Column(JSON)
    cell_parameters = Column(JSON)
    volume = Column(Float)
    review_status = Column(String(50), default="pending", nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    source_type = Column(String(100), nullable=False, index=True)
    source_label = Column(String(255))
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    superconductor = relationship("Superconductor", back_populates="structures")
    created_by_user = relationship(
        "User",
        back_populates="created_structures",
        foreign_keys=[created_by_user_id],
    )
```

- [ ] **Step 5: Run metadata tests and verify pass**

Run:

```bash
pytest tests/test_model_metadata.py -v
```

Expected: all tests in `tests/test_model_metadata.py` pass.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt backend/models.py tests/test_model_metadata.py
git commit -m "[时间] 2026-06-10 15:30:00" \
  -m "[修改目的] 增加晶体结构表模型契约" \
  -m "[修改内容] 添加 ASE 依赖、SuperconductorStructure 模型和模型元数据测试" \
  -m "[影响范围] 依赖安装、SQLAlchemy 元数据、结构存储后续开发" \
  -m "[验证方式] pytest tests/test_model_metadata.py -v"
```

---

### Task 2: Alembic Migration

**Files:**
- Create: `alembic/versions/20260610_0002_add_superconductors_structures.py`

- [ ] **Step 1: Write migration file**

Create `alembic/versions/20260610_0002_add_superconductors_structures.py`:

```python
"""add superconductors structures

Revision ID: 20260610_0002
Revises: 20260609_0001
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa


revision = "20260610_0002"
down_revision = "20260609_0001"
branch_labels = None
depends_on = None


def _timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def upgrade():
    op.create_table(
        "superconductors_structures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("superconductor_id", sa.Integer(), sa.ForeignKey("superconductors.id"), nullable=False),
        sa.Column("pressure_gpa", sa.Float(), nullable=False),
        sa.Column("space_group_symbol", sa.String(length=100)),
        sa.Column("space_group_number", sa.Integer()),
        sa.Column("structure_format", sa.String(length=20), nullable=False),
        sa.Column("structure_text", sa.Text(), nullable=False),
        sa.Column("structure_hash", sa.String(length=64), nullable=False),
        sa.Column("atom_count", sa.Integer()),
        sa.Column("elements_list", sa.JSON()),
        sa.Column("cell_parameters", sa.JSON()),
        sa.Column("volume", sa.Float()),
        sa.Column("review_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_label", sa.String(length=255)),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        *_timestamps(),
    )
    op.create_index("ix_superconductors_structures_superconductor_id", "superconductors_structures", ["superconductor_id"])
    op.create_index("ix_superconductors_structures_pressure_gpa", "superconductors_structures", ["pressure_gpa"])
    op.create_index("ix_superconductors_structures_space_group_symbol", "superconductors_structures", ["space_group_symbol"])
    op.create_index("ix_superconductors_structures_space_group_number", "superconductors_structures", ["space_group_number"])
    op.create_index("ix_superconductors_structures_structure_format", "superconductors_structures", ["structure_format"])
    op.create_index("ix_superconductors_structures_structure_hash", "superconductors_structures", ["structure_hash"])
    op.create_index("ix_superconductors_structures_review_status", "superconductors_structures", ["review_status"])
    op.create_index("ix_superconductors_structures_is_default", "superconductors_structures", ["is_default"])
    op.create_index("ix_superconductors_structures_source_type", "superconductors_structures", ["source_type"])
    op.create_index("ix_superconductors_structures_created_by_user_id", "superconductors_structures", ["created_by_user_id"])
    op.create_index(
        "ix_superconductors_structures_identity",
        "superconductors_structures",
        ["superconductor_id", "space_group_symbol", "space_group_number", "pressure_gpa"],
    )


def downgrade():
    op.drop_index("ix_superconductors_structures_identity", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_created_by_user_id", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_source_type", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_is_default", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_review_status", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_structure_hash", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_structure_format", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_space_group_number", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_space_group_symbol", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_pressure_gpa", table_name="superconductors_structures")
    op.drop_index("ix_superconductors_structures_superconductor_id", table_name="superconductors_structures")
    op.drop_table("superconductors_structures")
```

- [ ] **Step 2: Check Alembic revision chain**

Run:

```bash
python -m alembic history
```

Expected: output includes `20260609_0001 -> 20260610_0002`.

- [ ] **Step 3: Run model tests again**

Run:

```bash
pytest tests/test_model_metadata.py -v
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/20260610_0002_add_superconductors_structures.py
git commit -m "[时间] 2026-06-10 15:35:00" \
  -m "[修改目的] 增加晶体结构表迁移" \
  -m "[修改内容] 新增 superconductors_structures Alembic 迁移和相关索引" \
  -m "[影响范围] 数据库迁移、结构存储表创建" \
  -m "[验证方式] python -m alembic history；pytest tests/test_model_metadata.py -v"
```

---

### Task 3: Structure Storage Service

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/structure_storage.py`
- Create: `tests/test_structure_storage.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_structure_storage.py`:

```python
import pytest
from fastapi import HTTPException

from backend import crud, models
from backend.services.structure_storage import (
    approve_structure,
    create_structure,
    representative_structure_for,
    serialize_structure,
    validate_structure_payload,
)


CIF_TEXT = """data_LaH
_symmetry_space_group_name_H-M 'P 1'
_cell_length_a 3.000000
_cell_length_b 3.000000
_cell_length_c 3.000000
_cell_angle_alpha 90.0000
_cell_angle_beta 90.0000
_cell_angle_gamma 90.0000
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
La1 La 0.00000000 0.00000000 0.00000000
H1 H 0.50000000 0.50000000 0.50000000
"""


POSCAR_TEXT = """LaH
1.0
3.0 0.0 0.0
0.0 3.0 0.0
0.0 0.0 3.0
La H
1 1
Direct
0.0 0.0 0.0
0.5 0.5 0.5
"""


def _user(db_session):
    user = models.User(
        email="structure@example.com",
        password_hash="!",
        real_name="Structure User",
        role="admin",
        is_approved=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_validate_structure_payload_accepts_cif_and_poscar():
    cif_meta = validate_structure_payload("cif", CIF_TEXT)
    poscar_meta = validate_structure_payload("poscar", POSCAR_TEXT)

    assert cif_meta["atom_count"] == 2
    assert poscar_meta["atom_count"] == 2
    assert cif_meta["elements_list"] == ["H", "La"]
    assert poscar_meta["elements_list"] == ["H", "La"]
    assert cif_meta["structure_hash"]


def test_validate_structure_payload_rejects_unknown_format():
    with pytest.raises(HTTPException) as exc:
        validate_structure_payload("xyz", CIF_TEXT)

    assert exc.value.status_code == 400
    assert "cif" in exc.value.detail


def test_create_structure_starts_pending_and_serializes(db_session):
    user = _user(db_session)
    superconductor = crud.get_or_create_superconductor(db_session, "LaH")

    structure = create_structure(
        db_session,
        superconductor=superconductor,
        pressure_gpa=100.0,
        space_group_symbol="P 1",
        space_group_number=1,
        structure_format="cif",
        structure_text=CIF_TEXT,
        source_type="admin_upload",
        source_label="manual",
        created_by_user=user,
    )
    db_session.commit()

    payload = serialize_structure(structure)
    assert payload["chemical_formula"] == "LaH"
    assert payload["review_status"] == "pending"
    assert payload["is_default"] is False
    assert payload["structure_format"] == "cif"


def test_approve_structure_sets_latest_default_for_same_identity(db_session):
    user = _user(db_session)
    superconductor = crud.get_or_create_superconductor(db_session, "LaH")
    first = create_structure(
        db_session,
        superconductor=superconductor,
        pressure_gpa=100.0,
        space_group_symbol="P 1",
        space_group_number=1,
        structure_format="cif",
        structure_text=CIF_TEXT,
        source_type="admin_upload",
        source_label="first",
        created_by_user=user,
    )
    second = create_structure(
        db_session,
        superconductor=superconductor,
        pressure_gpa=100.0,
        space_group_symbol="P 1",
        space_group_number=1,
        structure_format="poscar",
        structure_text=POSCAR_TEXT,
        source_type="admin_upload",
        source_label="second",
        created_by_user=user,
    )
    db_session.flush()

    approve_structure(db_session, first)
    approve_structure(db_session, second)
    db_session.commit()

    assert first.is_default is False
    assert second.is_default is True
    assert second.review_status == "approved"


def test_representative_structure_uses_lowest_pressure_default(db_session):
    user = _user(db_session)
    superconductor = crud.get_or_create_superconductor(db_session, "LaH")
    high = create_structure(
        db_session,
        superconductor=superconductor,
        pressure_gpa=200.0,
        space_group_symbol="P 1",
        space_group_number=1,
        structure_format="cif",
        structure_text=CIF_TEXT,
        source_type="admin_upload",
        source_label="high",
        created_by_user=user,
    )
    low = create_structure(
        db_session,
        superconductor=superconductor,
        pressure_gpa=100.0,
        space_group_symbol="P 1",
        space_group_number=1,
        structure_format="poscar",
        structure_text=POSCAR_TEXT,
        source_type="admin_upload",
        source_label="low",
        created_by_user=user,
    )
    approve_structure(db_session, high)
    approve_structure(db_session, low)
    db_session.commit()

    representative = representative_structure_for(db_session, superconductor, "P 1")

    assert representative.id == low.id
```

- [ ] **Step 2: Run service tests and verify failure**

Run:

```bash
pytest tests/test_structure_storage.py -v
```

Expected: fail because `backend.services.structure_storage` does not exist.

- [ ] **Step 3: Create service package**

Create `backend/services/__init__.py`:

```python
"""Service helpers for business logic that spans API routes and models."""
```

- [ ] **Step 4: Implement structure service**

Create `backend/services/structure_storage.py`:

```python
from __future__ import annotations

import hashlib
from io import StringIO
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models


ALLOWED_STRUCTURE_FORMATS = {"cif", "poscar"}
APPROVED_STATUS = "approved"
PENDING_STATUS = "pending"
REJECTED_STATUS = "rejected"


def _read_atoms(structure_format: str, structure_text: str):
    try:
        from ase.io import read
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="ASE 未安装，无法解析晶体结构") from exc

    ase_format = "vasp" if structure_format == "poscar" else "cif"
    try:
        return read(StringIO(structure_text), format=ase_format)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"无法解析 {structure_format} 结构文件") from exc


def validate_structure_payload(structure_format: str, structure_text: str) -> dict[str, Any]:
    normalized_format = (structure_format or "").strip().lower()
    if normalized_format not in ALLOWED_STRUCTURE_FORMATS:
        raise HTTPException(status_code=400, detail="structure_format 仅支持 cif 或 poscar")
    if not structure_text or not structure_text.strip():
        raise HTTPException(status_code=400, detail="structure_text 不能为空")

    atoms = _read_atoms(normalized_format, structure_text)
    cell = atoms.cell
    lengths = cell.lengths()
    angles = cell.angles()
    symbols = sorted(set(atoms.get_chemical_symbols()))
    normalized_text = "\n".join(line.rstrip() for line in structure_text.strip().splitlines())
    digest = hashlib.sha256(f"{normalized_format}\n{normalized_text}".encode("utf-8")).hexdigest()

    return {
        "structure_format": normalized_format,
        "structure_hash": digest,
        "atom_count": len(atoms),
        "elements_list": symbols,
        "cell_parameters": {
            "a": float(lengths[0]),
            "b": float(lengths[1]),
            "c": float(lengths[2]),
            "alpha": float(angles[0]),
            "beta": float(angles[1]),
            "gamma": float(angles[2]),
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
        created_by_user_id=created_by_user.id if created_by_user else None,
    )
    db.add(structure)
    return structure


def approve_structure(db: Session, structure: models.SuperconductorStructure) -> models.SuperconductorStructure:
    query = db.query(models.SuperconductorStructure).filter(
        models.SuperconductorStructure.superconductor_id == structure.superconductor_id,
        models.SuperconductorStructure.pressure_gpa == structure.pressure_gpa,
    )
    if structure.space_group_symbol is None:
        query = query.filter(models.SuperconductorStructure.space_group_symbol.is_(None))
    else:
        query = query.filter(models.SuperconductorStructure.space_group_symbol == structure.space_group_symbol)
    if structure.space_group_number is None:
        query = query.filter(models.SuperconductorStructure.space_group_number.is_(None))
    else:
        query = query.filter(models.SuperconductorStructure.space_group_number == structure.space_group_number)

    for existing in query.all():
        existing.is_default = False
    structure.review_status = APPROVED_STATUS
    structure.is_default = True
    return structure


def reject_structure(structure: models.SuperconductorStructure) -> models.SuperconductorStructure:
    structure.review_status = REJECTED_STATUS
    structure.is_default = False
    return structure


def representative_structure_for(
    db: Session,
    superconductor: models.Superconductor,
    space_group: str | None,
) -> models.SuperconductorStructure | None:
    query = db.query(models.SuperconductorStructure).filter(
        models.SuperconductorStructure.superconductor_id == superconductor.id,
        models.SuperconductorStructure.review_status == APPROVED_STATUS,
    )
    if space_group:
        query = query.filter(models.SuperconductorStructure.space_group_symbol == space_group)
    return (
        query.order_by(
            models.SuperconductorStructure.is_default.desc(),
            models.SuperconductorStructure.pressure_gpa.asc(),
            models.SuperconductorStructure.created_at.desc(),
        )
        .first()
    )


def default_structure_for_record(db: Session, record: models.SuperconductorRecord) -> models.SuperconductorStructure | None:
    query = db.query(models.SuperconductorStructure).filter(
        models.SuperconductorStructure.superconductor_id == record.superconductor_id,
        models.SuperconductorStructure.pressure_gpa == record.pressure_gpa,
        models.SuperconductorStructure.review_status == APPROVED_STATUS,
    )
    if record.space_group_symbol is None:
        query = query.filter(models.SuperconductorStructure.space_group_symbol.is_(None))
    else:
        query = query.filter(models.SuperconductorStructure.space_group_symbol == record.space_group_symbol)
    if record.space_group_number is None:
        query = query.filter(models.SuperconductorStructure.space_group_number.is_(None))
    else:
        query = query.filter(models.SuperconductorStructure.space_group_number == record.space_group_number)
    return query.order_by(models.SuperconductorStructure.is_default.desc(), models.SuperconductorStructure.created_at.desc()).first()


def serialize_structure(structure: models.SuperconductorStructure, *, include_text: bool = False) -> dict[str, Any]:
    payload = {
        "id": structure.id,
        "superconductor_id": structure.superconductor_id,
        "chemical_formula": structure.superconductor.chemical_formula if structure.superconductor else None,
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
        "created_at": structure.created_at.isoformat() if structure.created_at else None,
        "updated_at": structure.updated_at.isoformat() if structure.updated_at else None,
    }
    if include_text:
        payload["structure_text"] = structure.structure_text
    return payload
```

- [ ] **Step 5: Run service tests and verify pass**

Run:

```bash
pytest tests/test_structure_storage.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/services tests/test_structure_storage.py
git commit -m "[时间] 2026-06-10 15:45:00" \
  -m "[修改目的] 增加晶体结构存储服务" \
  -m "[修改内容] 新增 ASE 解析校验、结构创建、审核默认切换和代表结构选择逻辑" \
  -m "[影响范围] 晶体结构上传校验、默认结构选择、后续 API 实现" \
  -m "[验证方式] pytest tests/test_structure_storage.py -v"
```

---

### Task 4: Structures API

**Files:**
- Create: `backend/api/structures.py`
- Modify: `backend/main.py`
- Create: `tests/test_structures_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_structures_api.py`:

```python
from fastapi.testclient import TestClient

from backend import crud, models
from backend.database import get_db
from backend.main import app
from backend.security import get_current_user


CIF_TEXT = """data_LaH
_symmetry_space_group_name_H-M 'P 1'
_cell_length_a 3.000000
_cell_length_b 3.000000
_cell_length_c 3.000000
_cell_angle_alpha 90.0000
_cell_angle_beta 90.0000
_cell_angle_gamma 90.0000
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
La1 La 0.00000000 0.00000000 0.00000000
H1 H 0.50000000 0.50000000 0.50000000
"""


def _admin(db_session):
    user = models.User(
        email="admin@example.com",
        password_hash="!",
        real_name="Admin User",
        role="admin",
        is_approved=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _client(db_session, user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_structure_upload_review_representative_and_raw_download(db_session):
    user = _admin(db_session)
    crud.get_or_create_superconductor(db_session, "LaH")
    db_session.commit()
    client = _client(db_session, user)
    try:
        created = client.post(
            "/api/structures/",
            json={
                "chemical_formula": "LaH",
                "pressure_gpa": 100.0,
                "space_group_symbol": "P 1",
                "space_group_number": 1,
                "structure_format": "cif",
                "structure_text": CIF_TEXT,
                "source_type": "admin_upload",
                "source_label": "manual",
            },
        )
        assert created.status_code == 200
        structure_id = created.json()["id"]
        assert created.json()["review_status"] == "pending"

        reviewed = client.post(f"/api/structures/{structure_id}/review", json={"status": "approved"})
        assert reviewed.status_code == 200
        assert reviewed.json()["is_default"] is True

        representative = client.get("/api/structures/representative", params={"formula": "LaH", "space_group": "P 1"})
        assert representative.status_code == 200
        assert representative.json()["id"] == structure_id

        raw = client.get(f"/api/structures/{structure_id}/raw")
        assert raw.status_code == 200
        assert "La1 La" in raw.text
        assert raw.headers["content-type"].startswith("chemical/x-cif")
    finally:
        app.dependency_overrides.clear()


def test_structure_by_record_matches_identity(db_session):
    user = _admin(db_session)
    superconductor = crud.get_or_create_superconductor(db_session, "LaH")
    record = models.SuperconductorRecord(
        superconductor_id=superconductor.id,
        source_label="paper",
        pressure_gpa=100.0,
        space_group_symbol="P 1",
        space_group_number=1,
        mcmillan_tc=10.0,
    )
    db_session.add(record)
    db_session.commit()
    client = _client(db_session, user)
    try:
        created = client.post(
            "/api/structures/",
            json={
                "chemical_formula": "LaH",
                "pressure_gpa": 100.0,
                "space_group_symbol": "P 1",
                "space_group_number": 1,
                "structure_format": "cif",
                "structure_text": CIF_TEXT,
                "source_type": "admin_upload",
            },
        )
        structure_id = created.json()["id"]
        client.post(f"/api/structures/{structure_id}/review", json={"status": "approved"})

        by_record = client.get(f"/api/structures/by-record/{record.id}")
        assert by_record.status_code == 200
        assert by_record.json()["id"] == structure_id
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run API tests and verify failure**

Run:

```bash
pytest tests/test_structures_api.py -v
```

Expected: fail because `/api/structures/*` routes do not exist.

- [ ] **Step 3: Implement API routes**

Create `backend/api/structures.py`:

```python
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
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
    space_group_symbol: str | None = None
    space_group_number: int | None = None
    structure_format: Literal["cif", "poscar"]
    structure_text: str = Field(..., min_length=1)
    source_type: str = "admin_upload"
    source_label: str | None = None


class StructureReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]


def _require_user(current_user: models.User | None) -> models.User:
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    return current_user


def _require_admin(current_user: models.User | None) -> models.User:
    user = _require_user(current_user)
    if user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@router.post("/")
def upload_structure(
    request: StructureCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user),
):
    user = _require_user(current_user)
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
        created_by_user=user,
    )
    db.commit()
    db.refresh(structure)
    return serialize_structure(structure)


@router.post("/{structure_id}/review")
def review_structure(
    structure_id: int,
    request: StructureReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user),
):
    _require_admin(current_user)
    structure = db.query(models.SuperconductorStructure).filter_by(id=structure_id).first()
    if not structure:
        raise HTTPException(status_code=404, detail="晶体结构不存在")
    if request.status == "approved":
        approve_structure(db, structure)
    else:
        reject_structure(structure)
    db.commit()
    db.refresh(structure)
    return serialize_structure(structure)


@router.get("/by-record/{record_id}")
def get_structure_by_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(models.SuperconductorRecord).filter_by(id=record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="超导记录不存在")
    structure = default_structure_for_record(db, record)
    if not structure:
        raise HTTPException(status_code=404, detail="该记录暂无已审核晶体结构")
    return serialize_structure(structure, include_text=True)


@router.get("/representative")
def get_representative_structure(formula: str, space_group: str | None = None, db: Session = Depends(get_db)):
    superconductor = crud.get_or_create_superconductor(db, formula)
    structure = representative_structure_for(db, superconductor, space_group)
    if not structure:
        raise HTTPException(status_code=404, detail="暂无代表晶体结构")
    return serialize_structure(structure, include_text=True)


@router.get("/{structure_id}/raw")
def get_structure_raw(structure_id: int, db: Session = Depends(get_db)):
    structure = db.query(models.SuperconductorStructure).filter_by(id=structure_id).first()
    if not structure:
        raise HTTPException(status_code=404, detail="晶体结构不存在")
    media_type = "chemical/x-cif" if structure.structure_format == "cif" else "text/plain"
    filename = f"structure-{structure.id}.{structure.structure_format}"
    return Response(
        content=structure.structure_text,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
```

- [ ] **Step 4: Register router**

In `backend/main.py`, change the API import:

```python
from backend.api import elements, compounds, papers, admin, auth_routes, tc_predict, alexandria, htsc2025, structures
```

Add the include near the other routers:

```python
app.include_router(structures.router)
```

- [ ] **Step 5: Run API tests and verify pass**

Run:

```bash
pytest tests/test_structures_api.py -v
```

Expected: pass.

- [ ] **Step 6: Run related backend tests**

Run:

```bash
pytest tests/test_structure_storage.py tests/test_structures_api.py tests/test_model_metadata.py -v
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add backend/api/structures.py backend/main.py tests/test_structures_api.py
git commit -m "[时间] 2026-06-10 16:00:00" \
  -m "[修改目的] 增加晶体结构 API" \
  -m "[修改内容] 新增结构上传、审核、按记录匹配、代表结构查询和原始文件下载接口" \
  -m "[影响范围] 后端结构接口、ASE 可视化数据来源、管理员审核流程" \
  -m "[验证方式] pytest tests/test_structure_storage.py tests/test_structures_api.py tests/test_model_metadata.py -v"
```

---

### Task 5: Import And Export

**Files:**
- Modify: `backend/export_data.py`
- Modify: `backend/import_data.py`
- Modify: `tests/test_import_export.py`

- [ ] **Step 1: Write failing import/export tests**

Append this test to `tests/test_import_export.py`:

```python
def test_import_export_round_trips_superconductor_structures(db_session):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "users": [
            {
                "email": "u@example.com",
                "real_name": "Uploader",
                "role": "user",
                "is_approved": True,
                "is_email_verified": True,
            }
        ],
        "papers": [],
        "superconductor_records": [],
        "superconductors_structures": [
            {
                "chemical_formula": "LaH",
                "pressure_gpa": 100.0,
                "space_group_symbol": "P 1",
                "space_group_number": 1,
                "structure_format": "cif",
                "structure_text": "data_LaH\\n_cell_length_a 1\\n",
                "structure_hash": "abc123",
                "atom_count": 2,
                "elements_list": ["H", "La"],
                "cell_parameters": {"a": 1.0},
                "volume": 1.0,
                "review_status": "approved",
                "is_default": True,
                "source_type": "import",
                "source_label": "fixture",
                "created_by_email": "u@example.com",
            }
        ],
    }

    result = import_payload(db_session, payload, clear_existing=True)
    exported = build_export_payload(db_session)

    assert result["superconductors_structures"] == 1
    item = exported["superconductors_structures"][0]
    assert item["chemical_formula"] == "LaH"
    assert item["structure_format"] == "cif"
    assert item["review_status"] == "approved"
    assert item["is_default"] is True
```

- [ ] **Step 2: Run import/export tests and verify failure**

Run:

```bash
pytest tests/test_import_export.py -v
```

Expected: fail because `superconductors_structures` is not exported/imported.

- [ ] **Step 3: Export structures**

In `backend/export_data.py`, add:

```python
def _structure_to_dict(structure: models.SuperconductorStructure) -> dict[str, Any]:
    return {
        "id": structure.id,
        "chemical_formula": structure.superconductor.chemical_formula if structure.superconductor else None,
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
        "created_by_email": structure.created_by_user.email if structure.created_by_user else None,
        "created_at": _dt(structure.created_at),
        "updated_at": _dt(structure.updated_at),
    }
```

In `build_export_payload`, query structures:

```python
structures = db.query(models.SuperconductorStructure).order_by(models.SuperconductorStructure.id).all()
```

Add this payload key:

```python
"superconductors_structures": [_structure_to_dict(structure) for structure in structures],
```

Update the CLI print section to include:

```python
print(f"   晶体结构: {len(payload['superconductors_structures'])} 条")
```

- [ ] **Step 4: Import structures**

In `backend/import_data.py`, when clearing existing business data, delete structures before records:

```python
db.query(models.SuperconductorStructure).delete()
```

Add helper:

```python
def _structure_item(
    db: Session,
    item: dict[str, Any],
    user_by_email: dict[str, models.User],
) -> models.SuperconductorStructure | None:
    formula = item.get("chemical_formula")
    if not formula:
        return None
    superconductor = crud.get_or_create_superconductor(db, formula)
    created_by = user_by_email.get(item.get("created_by_email")) if item.get("created_by_email") else None
    structure = models.SuperconductorStructure(
        superconductor_id=superconductor.id,
        pressure_gpa=item.get("pressure_gpa"),
        space_group_symbol=item.get("space_group_symbol"),
        space_group_number=item.get("space_group_number"),
        structure_format=item.get("structure_format"),
        structure_text=item.get("structure_text"),
        structure_hash=item.get("structure_hash"),
        atom_count=item.get("atom_count"),
        elements_list=item.get("elements_list"),
        cell_parameters=item.get("cell_parameters"),
        volume=item.get("volume"),
        review_status=item.get("review_status") or "pending",
        is_default=bool(item.get("is_default", False)),
        source_type=item.get("source_type") or "import",
        source_label=item.get("source_label"),
        created_by_user_id=created_by.id if created_by else None,
    )
    db.add(structure)
    return structure
```

In `import_payload`, after records import loop:

```python
imported_structures = 0
for item in payload.get("superconductors_structures", []):
    if _structure_item(db, item, user_by_email):
        imported_structures += 1
```

Add result key:

```python
"superconductors_structures": imported_structures,
```

Update CLI print section:

```python
print(f"   晶体结构: {result['superconductors_structures']} 条")
```

- [ ] **Step 5: Run import/export tests and verify pass**

Run:

```bash
pytest tests/test_import_export.py -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/export_data.py backend/import_data.py tests/test_import_export.py
git commit -m "[时间] 2026-06-10 16:15:00" \
  -m "[修改目的] 支持晶体结构导入导出" \
  -m "[修改内容] 在 mysql-redesign-v1 JSON 中加入 superconductors_structures 数据导入导出" \
  -m "[影响范围] 运维导入导出、结构数据备份恢复" \
  -m "[验证方式] pytest tests/test_import_export.py -v"
```

---

### Task 6: Business Documentation

**Files:**
- Modify: `docs/business-overview.md`
- Modify: `docs/business-paper-ingestion.md`
- Modify: `docs/current-state-and-gaps.md`

- [ ] **Step 1: Update business overview**

In `docs/business-overview.md`, update the core table list in section 6 to include `superconductors_structures`:

```markdown
- 当前核心业务表为 `periodic_table_elements`、`chemical_systems`、`superconductors`、`superconductors_structures`、`papers`、`users`、`superconductor_records`
```

Add a sentence to the document module relationship section:

```markdown
- 晶体结构存储由 `superconductors_structures` 承接，按化学式、空间群和压强保存 CIF/POSCAR 结构正文；`superconductor_records` 继续承接超导物理数据点。
```

- [ ] **Step 2: Update paper ingestion docs**

In `docs/business-paper-ingestion.md`, add a section after “物理数据模型”:

```markdown
## 5. 晶体结构存储

当前晶体结构正文由 `superconductors_structures` 表保存，支持 `cif` 和 `poscar` 两种格式。结构存储粒度为“化学式 + 空间群 + 压强”，同一粒度下可以保存多个版本。

结构上传后进入 `pending` 状态。管理员审核通过后，最新审核通过版本成为同一化学式、空间群和压强下的默认结构。组合页或详情页做可视化展示时，可按“化学式 + 空间群”选择代表结构，默认从已审核结构中按默认标记、压强和创建时间选择。

`superconductor_records.crystal_structure` 仍用于结构类型或空间群描述，不保存 CIF/POSCAR 正文。
```

Renumber the old sections below if the document uses numbered headings.

- [ ] **Step 3: Update current-state docs**

In `docs/current-state-and-gaps.md`, add an implemented capability statement:

```markdown
- 已新增晶体结构存储设计与后端承接：`superconductors_structures` 保存 CIF/POSCAR 结构正文、结构来源、审核状态和默认版本；前端可视化入口可基于结构 API 获取代表结构。
```

- [ ] **Step 4: Verify docs mention the table name**

Run:

```bash
Select-String -Path docs\\*.md -Pattern 'superconductors_structures'
```

Expected: output includes the three updated business docs and the design spec.

- [ ] **Step 5: Commit**

```bash
git add docs/business-overview.md docs/business-paper-ingestion.md docs/current-state-and-gaps.md
git commit -m "[时间] 2026-06-10 16:25:00" \
  -m "[修改目的] 补充晶体结构存储业务文档" \
  -m "[修改内容] 说明 superconductors_structures 表职责、上传审核规则和与超导记录表的边界" \
  -m "[影响范围] 业务总览、文献采集文档、当前状态说明" \
  -m "[验证方式] Select-String -Path docs\\*.md -Pattern 'superconductors_structures'"
```

---

### Task 7: Full Verification

**Files:**
- No source changes unless verification exposes a defect.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
pytest tests/test_model_metadata.py tests/test_structure_storage.py tests/test_structures_api.py tests/test_import_export.py -v
```

Expected: pass.

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -v
```

Expected: pass.

- [ ] **Step 3: Inspect changed files**

Run:

```bash
git status --short
git diff --stat HEAD
```

Expected: only intended files changed since the last commit, or no unstaged changes if every task committed cleanly.

- [ ] **Step 4: Manual API smoke test**

Start the server if local dependencies and database are available:

```bash
python -m uvicorn backend.main:app --reload
```

Expected: server starts and `/docs` shows `structures` routes. If MySQL is not available locally, record this as not run and rely on SQLite-backed API tests.

- [ ] **Step 5: Final implementation commit if needed**

If verification required a fix, commit only the fix:

```bash
git add requirements.txt backend/models.py backend/services/__init__.py backend/services/structure_storage.py backend/api/structures.py backend/main.py backend/export_data.py backend/import_data.py tests/test_model_metadata.py tests/test_structure_storage.py tests/test_structures_api.py tests/test_import_export.py docs/business-overview.md docs/business-paper-ingestion.md docs/current-state-and-gaps.md
git commit -m "[时间] 2026-06-10 16:35:00" \
  -m "[修改目的] 修正晶体结构存储验证中发现的问题" \
  -m "[修改内容] 根据测试结果修正结构存储实现" \
  -m "[影响范围] 晶体结构存储相关接口或服务" \
  -m "[验证方式] pytest -v"
```

---

## Self-Review

- Spec coverage: the plan covers CIF/POSCAR support, `superconductors_structures`, ASE validation, structure versions, default approval behavior, representative lookup, API endpoints, import/export, docs, and tests.
- Scope check: the plan does not add frontend visualization UI work because the current requirement is storage/API. Existing ASE visualization can consume `GET /api/structures/representative` or `GET /api/structures/by-record/{record_id}`.
- Placeholder scan: no task uses unresolved placeholder markers.
- Type consistency: model, migration, service, API, and import/export use `SuperconductorStructure` and the table name `superconductors_structures` consistently.
