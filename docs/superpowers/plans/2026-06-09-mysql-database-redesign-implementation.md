# MySQL Database Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current SQLite-shaped database layer with a MySQL-first schema centered on `chemical_systems`, `superconductors`, `papers`, `users`, and `superconductor_records`.

**Architecture:** Introduce a new MySQL/Alembic-backed data model while keeping API behavior incremental and testable. The implementation first adds schema helpers and tests, then migrates database setup, then rewires search, paper upload/review, and chart data APIs around the six-table design.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, MySQL via PyMySQL, Pydantic v2, pytest, httpx TestClient.

---

## File Structure

Create or modify these files:

- Modify `requirements.txt`: add `alembic`, `pymysql`, `pytest`, and keep current dependencies.
- Modify `backend/database.py`: replace multi-SQLite engine setup with one configurable SQLAlchemy engine and session dependency.
- Modify `backend/models.py`: define the six confirmed MySQL-oriented tables.
- Create `backend/db_helpers.py`: formula normalization, system-key generation, JSON composition helpers, and review/search enum constants.
- Create `backend/repositories/superconductors.py`: query functions for `formula_search`, `elements_exact_search`, `elements_combination_search`, and `elements_contained_search`.
- Create `backend/repositories/__init__.py`: package marker.
- Modify `backend/schemas.py`: add request/response models for new search modes and record responses.
- Modify `backend/api/compounds.py`: replace old compound search endpoints with superconductor-centered search behavior while preserving compatible URL shapes where useful.
- Modify `backend/api/papers.py`: remove image upload/storage behavior and write records into the new schema.
- Modify `backend/api/admin.py`: update user role and paper review fields for new schema.
- Modify `backend/api/elements.py`: read from `periodic_table_elements`.
- Modify `backend/init_db.py`: only seed `periodic_table_elements`; table creation moves to Alembic.
- Create `alembic.ini`, `alembic/env.py`, and `alembic/versions/20260609_0001_initial_mysql_schema.py`.
- Create `tests/test_db_helpers.py`: unit tests for normalization and search mode helpers.
- Create `tests/test_superconductor_repository.py`: SQLite-in-memory tests for repository logic.
- Create `tests/test_chart_rules.py`: unit tests for chart inclusion rules.
- Modify `frontend/templates/index.html`, `frontend/templates/compound.html`, `frontend/static/js/periodic_table.js`, and `frontend/static/js/compound_page.js`: remove database selector and use new search mode names.

## Task 1: Add Dependencies and Test Harness

**Files:**
- Modify: `requirements.txt`
- Create: `tests/conftest.py`
- Test: `tests/test_db_helpers.py`

- [ ] **Step 1: Add implementation and test dependencies**

Append these lines to `requirements.txt` under the database and tool sections:

```text
alembic==1.13.1
pymysql==1.1.0
pytest==8.2.2
```

- [ ] **Step 2: Create pytest fixtures**

Create `tests/conftest.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base


@pytest.fixture()
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(sqlite_engine):
    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 3: Add a first failing helper test file**

Create `tests/test_db_helpers.py`:

```python
from backend.db_helpers import (
    build_system_key,
    normalize_formula,
    parse_formula_composition,
)


def test_build_system_key_sorts_symbols():
    assert build_system_key(["La", "H"]) == ("H-La", ["H", "La"])


def test_parse_formula_composition_counts_atoms():
    assert parse_formula_composition("LaH10") == {"La": 1, "H": 10}


def test_normalize_formula_sorts_symbols():
    normalized, elements, composition, ratios = normalize_formula("LaH10")
    assert normalized == "H10La"
    assert elements == ["H", "La"]
    assert composition == {"La": 1, "H": 10}
    assert ratios["La"] == 1 / 11
    assert ratios["H"] == 10 / 11
```

- [ ] **Step 4: Run the failing helper tests**

Run:

```bash
pytest tests/test_db_helpers.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.db_helpers'`.

- [ ] **Step 5: Commit dependency and test harness changes**

```bash
git add requirements.txt tests/conftest.py tests/test_db_helpers.py
git commit -m "test: add database redesign test harness"
```

## Task 2: Implement Database Helpers

**Files:**
- Create: `backend/db_helpers.py`
- Test: `tests/test_db_helpers.py`

- [ ] **Step 1: Create helper implementation**

Create `backend/db_helpers.py`:

```python
import re
from typing import Iterable


REVIEW_STATUSES = {"pending", "approved", "rejected", "needs_revision"}
USER_ROLES = {"user", "admin", "superadmin"}
SEARCH_MODES = {
    "formula_search",
    "elements_exact_search",
    "elements_combination_search",
    "elements_contained_search",
}


def normalize_element_symbols(symbols: Iterable[str]) -> list[str]:
    cleaned = []
    for symbol in symbols:
        value = str(symbol).strip()
        if value:
            cleaned.append(value)
    return sorted(set(cleaned))


def build_system_key(symbols: Iterable[str]) -> tuple[str, list[str]]:
    normalized = normalize_element_symbols(symbols)
    return "-".join(normalized), normalized


def parse_formula_composition(formula: str) -> dict[str, int]:
    if not formula or not formula.strip():
        raise ValueError("chemical formula is required")
    matches = re.findall(r"([A-Z][a-z]?)(\\d*)", formula.strip())
    if not matches:
        raise ValueError(f"invalid chemical formula: {formula}")
    composition: dict[str, int] = {}
    for symbol, amount in matches:
        composition[symbol] = composition.get(symbol, 0) + (int(amount) if amount else 1)
    return composition


def normalize_formula(formula: str) -> tuple[str, list[str], dict[str, int], dict[str, float]]:
    composition = parse_formula_composition(formula)
    elements = sorted(composition)
    normalized_parts = []
    total = sum(composition.values())
    for symbol in elements:
        amount = composition[symbol]
        normalized_parts.append(symbol if amount == 1 else f"{symbol}{amount}")
    ratios = {symbol: composition[symbol] / total for symbol in elements}
    return "".join(normalized_parts), elements, composition, ratios
```

- [ ] **Step 2: Run helper tests**

Run:

```bash
pytest tests/test_db_helpers.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit helper implementation**

```bash
git add backend/db_helpers.py tests/test_db_helpers.py
git commit -m "feat: add database normalization helpers"
```

## Task 3: Replace Database Configuration With MySQL-First Session

**Files:**
- Modify: `backend/database.py`
- Test: `tests/conftest.py`

- [ ] **Step 1: Replace `backend/database.py` with one engine and one base**

Use this implementation:

```python
"""
Database configuration.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DEFAULT_DATABASE_URL = "mysql+pymysql://root:password@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Run helper tests**

Run:

```bash
pytest tests/test_db_helpers.py -v
```

Expected: PASS. These tests import `Base` through `tests/conftest.py`.

- [ ] **Step 3: Commit database configuration**

```bash
git add backend/database.py tests/conftest.py
git commit -m "feat: use mysql-first database session"
```

## Task 4: Define the Six SQLAlchemy Models

**Files:**
- Modify: `backend/models.py`
- Test: `tests/test_model_metadata.py`

- [ ] **Step 1: Write failing metadata tests**

Create `tests/test_model_metadata.py`:

```python
from backend.database import Base


def test_confirmed_tables_exist():
    assert set(Base.metadata.tables) == {
        "periodic_table_elements",
        "chemical_systems",
        "superconductors",
        "papers",
        "users",
        "superconductor_records",
    }


def test_superconductor_records_has_confirmed_fields():
    columns = set(Base.metadata.tables["superconductor_records"].columns)
    assert "energy_above_hull" in columns
    assert "anisotropic_eliashberg_tc" in columns
    assert "show_in_chart" in columns
    assert "pseudopotential_name" in columns
```

- [ ] **Step 2: Replace `backend/models.py`**

Use this model skeleton:

```python
"""
SQLAlchemy models for the MySQL superconductor dataset schema.
"""
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class PeriodicTableElement(Base):
    __tablename__ = "periodic_table_elements"

    id = Column(Integer, primary_key=True)
    atomic_number = Column(Integer, unique=True, nullable=False, index=True)
    symbol = Column(String(3), unique=True, nullable=False, index=True)
    english_name = Column(String(80), nullable=False)
    chinese_name = Column(String(80))
    atomic_mass = Column(Float)
    period_number = Column(Integer)
    group_number = Column(Integer)
    category = Column(String(80))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ChemicalSystem(Base):
    __tablename__ = "chemical_systems"

    id = Column(Integer, primary_key=True)
    system_key = Column(String(255), unique=True, nullable=False, index=True)
    elements_list = Column(JSON, nullable=False)
    element_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    superconductors = relationship("Superconductor", back_populates="chemical_system")


class Superconductor(Base):
    __tablename__ = "superconductors"

    id = Column(Integer, primary_key=True)
    chemical_system_id = Column(Integer, ForeignKey("chemical_systems.id"), nullable=False, index=True)
    chemical_formula = Column(String(255), nullable=False)
    formula_normalized = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    elements_list = Column(JSON, nullable=False)
    composition = Column(JSON, nullable=False)
    element_ratio = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    chemical_system = relationship("ChemicalSystem", back_populates="superconductors")
    records = relationship("SuperconductorRecord", back_populates="superconductor", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(120), nullable=False)
    affiliation = Column(String(255))
    role = Column(String(32), nullable=False, default="user", index=True)
    is_approved = Column(Boolean, nullable=False, default=False)
    is_email_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True)
    doi = Column(String(512), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    journal = Column(String(255))
    volume = Column(String(80))
    pages = Column(String(120))
    year = Column(Integer, index=True)
    abstract = Column(Text)
    authors = Column(JSON, nullable=False)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    review_status = Column(String(32), nullable=False, default="pending", index=True)
    reviewed_at = Column(DateTime(timezone=True))
    review_comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    records = relationship("SuperconductorRecord", back_populates="paper")


class SuperconductorRecord(Base):
    __tablename__ = "superconductor_records"
    __table_args__ = (
        UniqueConstraint(
            "superconductor_id",
            "paper_id",
            "source_label",
            "pressure_gpa",
            "space_group_symbol",
            name="uq_superconductor_record_identity",
        ),
    )

    id = Column(Integer, primary_key=True)
    superconductor_id = Column(Integer, ForeignKey("superconductors.id"), nullable=False, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True, index=True)
    source_label = Column(String(255), nullable=False, index=True)
    pressure_gpa = Column(Float, nullable=False, index=True)
    space_group_symbol = Column(String(80), index=True)
    space_group_number = Column(Integer, index=True)
    crystal_structure = Column(String(255))
    thermodynamically_stable = Column(Boolean)
    dynamically_stable = Column(Boolean)
    energy_above_hull = Column(Float)
    mcmillan_tc = Column(Float)
    allen_dynes_tc = Column(Float)
    isotropic_eliashberg_tc = Column(Float)
    anisotropic_eliashberg_tc = Column(Float)
    experimental_tc = Column(Float)
    lambda_value = Column(Float)
    omega_log = Column(Float)
    n_ef_total = Column(Float)
    element_n_ef = Column(JSON)
    pseudopotential_type = Column(String(120))
    pseudopotential_name = Column(String(255))
    exchange_correlation_functional = Column(String(120))
    calculation_code = Column(String(120))
    k_grid = Column(String(80))
    q_grid = Column(String(80))
    energy_cutoff_value = Column(Float)
    energy_cutoff_unit = Column(String(32))
    show_in_chart = Column(Boolean, nullable=False, default=False, index=True)
    s_factor = Column(Float)
    method = Column(String(120))
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    superconductor = relationship("Superconductor", back_populates="records")
    paper = relationship("Paper", back_populates="records")
```

- [ ] **Step 3: Run metadata tests**

Run:

```bash
pytest tests/test_model_metadata.py tests/test_db_helpers.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit models**

```bash
git add backend/models.py tests/test_model_metadata.py
git commit -m "feat: define mysql dataset models"
```

## Task 5: Add Alembic Initial Migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/20260609_0001_initial_mysql_schema.py`

- [ ] **Step 1: Create Alembic config**

Create `alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = mysql+pymysql://root:password@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: Create Alembic env**

Create `alembic/env.py`:

```python
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.database import Base
from backend import models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Generate migration from metadata**

Run:

```bash
mkdir -p alembic/versions
alembic revision --autogenerate -m "initial mysql schema"
```

Expected: Alembic creates one file under `alembic/versions/`.

- [ ] **Step 4: Rename migration file**

Rename the generated file to:

```text
alembic/versions/20260609_0001_initial_mysql_schema.py
```

Keep the generated `upgrade()` and `downgrade()` bodies, and verify it creates exactly the six confirmed tables.

- [ ] **Step 5: Run offline SQL generation**

Run:

```bash
alembic upgrade head --sql
```

Expected: SQL output includes `CREATE TABLE periodic_table_elements`, `CREATE TABLE superconductor_records`, and `CREATE TABLE users`.

- [ ] **Step 6: Commit Alembic setup**

```bash
git add alembic.ini alembic
git commit -m "feat: add initial mysql alembic migration"
```

## Task 6: Seed Periodic Table Elements Without Creating Tables

**Files:**
- Modify: `backend/init_db.py`
- Test: `tests/test_periodic_seed.py`

- [ ] **Step 1: Write failing seed test**

Create `tests/test_periodic_seed.py`:

```python
from backend.init_db import seed_periodic_table_elements
from backend.models import PeriodicTableElement


def test_seed_periodic_table_elements_is_idempotent(db_session):
    seed_periodic_table_elements(db_session)
    seed_periodic_table_elements(db_session)

    assert db_session.query(PeriodicTableElement).count() == 118
    hydrogen = db_session.query(PeriodicTableElement).filter_by(symbol="H").one()
    assert hydrogen.atomic_number == 1
    assert hydrogen.english_name == "Hydrogen"
```

- [ ] **Step 2: Replace `backend/init_db.py` with seed-only behavior**

Keep the existing `ELEMENTS_DATA`, then implement:

```python
from backend.database import SessionLocal
from backend.models import PeriodicTableElement


def seed_periodic_table_elements(db):
    existing = db.query(PeriodicTableElement).count()
    if existing >= 118:
        return

    by_symbol = {
        row.symbol
        for row in db.query(PeriodicTableElement.symbol).all()
    }
    rows = []
    for atomic_number, symbol, english_name, chinese_name in ELEMENTS_DATA:
        if symbol in by_symbol:
            continue
        rows.append(
            PeriodicTableElement(
                atomic_number=atomic_number,
                symbol=symbol,
                english_name=english_name,
                chinese_name=chinese_name,
            )
        )
    db.add_all(rows)
    db.commit()


def init_database():
    db = SessionLocal()
    try:
        seed_periodic_table_elements(db)
    finally:
        db.close()
```

- [ ] **Step 3: Run seed test**

Run:

```bash
pytest tests/test_periodic_seed.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit seed changes**

```bash
git add backend/init_db.py tests/test_periodic_seed.py
git commit -m "feat: seed periodic table elements"
```

## Task 7: Implement Superconductor Repository Search

**Files:**
- Create: `backend/repositories/__init__.py`
- Create: `backend/repositories/superconductors.py`
- Test: `tests/test_superconductor_repository.py`

- [ ] **Step 1: Write repository tests**

Create `tests/test_superconductor_repository.py`:

```python
from backend.db_helpers import build_system_key, normalize_formula
from backend.models import ChemicalSystem, Superconductor
from backend.repositories.superconductors import search_superconductors


def add_superconductor(db, formula):
    normalized, elements, composition, ratios = normalize_formula(formula)
    system_key, system_elements = build_system_key(elements)
    system = db.query(ChemicalSystem).filter_by(system_key=system_key).first()
    if system is None:
        system = ChemicalSystem(
            system_key=system_key,
            elements_list=system_elements,
            element_count=len(system_elements),
        )
        db.add(system)
        db.flush()
    sc = Superconductor(
        chemical_system_id=system.id,
        chemical_formula=formula,
        formula_normalized=normalized,
        display_name=formula,
        elements_list=elements,
        composition=composition,
        element_ratio=ratios,
    )
    db.add(sc)
    db.commit()
    return sc


def test_formula_search_finds_normalized_formula(db_session):
    add_superconductor(db_session, "LaH10")
    result = search_superconductors(db_session, "formula_search", formula="H10La")
    assert [item.chemical_formula for item in result.items] == ["LaH10"]


def test_elements_exact_search_matches_same_system(db_session):
    add_superconductor(db_session, "LaH10")
    add_superconductor(db_session, "H3S")
    result = search_superconductors(db_session, "elements_exact_search", elements=["La", "H"])
    assert [item.chemical_formula for item in result.items] == ["LaH10"]


def test_elements_contained_search_matches_supersets(db_session):
    add_superconductor(db_session, "LaH10")
    add_superconductor(db_session, "LaH3S")
    result = search_superconductors(db_session, "elements_contained_search", elements=["La", "H"])
    assert {item.chemical_formula for item in result.items} == {"LaH10", "LaH3S"}
```

- [ ] **Step 2: Implement repository**

Create `backend/repositories/__init__.py` as an empty file.

Create `backend/repositories/superconductors.py`:

```python
from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend import models
from backend.db_helpers import build_system_key, normalize_element_symbols, normalize_formula


@dataclass
class SuperconductorSearchResult:
    items: list[models.Superconductor]
    total: int
    page: int
    page_size: int
    has_prev: bool
    has_next: bool


def _paginate(items, limit: int, offset: int):
    total = len(items)
    page_items = items[offset: offset + limit]
    page_size = limit
    page = (offset // page_size) + 1 if page_size else 1
    return SuperconductorSearchResult(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        has_prev=offset > 0,
        has_next=offset + limit < total,
    )


def search_superconductors(
    db: Session,
    mode: str,
    *,
    formula: str | None = None,
    elements: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> SuperconductorSearchResult:
    query = db.query(models.Superconductor).join(models.ChemicalSystem)

    if mode == "formula_search":
        if not formula:
            return _paginate([], limit, offset)
        normalized, _, _, _ = normalize_formula(formula)
        items = query.filter(models.Superconductor.formula_normalized == normalized).all()
        return _paginate(items, limit, offset)

    normalized_elements = normalize_element_symbols(elements or [])
    if not normalized_elements:
        return _paginate([], limit, offset)

    if mode == "elements_exact_search":
        system_key, _ = build_system_key(normalized_elements)
        items = query.filter(models.ChemicalSystem.system_key == system_key).all()
        return _paginate(items, limit, offset)

    all_items = query.all()
    selection = set(normalized_elements)
    if mode == "elements_combination_search":
        matched = [item for item in all_items if set(item.elements_list).issubset(selection)]
    elif mode == "elements_contained_search":
        matched = [item for item in all_items if selection.issubset(set(item.elements_list))]
    else:
        matched = []

    matched.sort(key=lambda item: (len(item.elements_list), item.formula_normalized))
    return _paginate(matched, limit, offset)
```

- [ ] **Step 3: Run repository tests**

Run:

```bash
pytest tests/test_superconductor_repository.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit repository**

```bash
git add backend/repositories tests/test_superconductor_repository.py
git commit -m "feat: add superconductor search repository"
```

## Task 8: Add Record Chart Rules

**Files:**
- Create: `backend/chart_rules.py`
- Test: `tests/test_chart_rules.py`

- [ ] **Step 1: Write chart rule tests**

Create `tests/test_chart_rules.py`:

```python
from types import SimpleNamespace

from backend.chart_rules import include_in_tc_pressure_chart, include_in_tc_year_chart


def test_pressure_chart_requires_show_in_chart_and_a_tc_value():
    record = SimpleNamespace(show_in_chart=True, pressure_gpa=200, allen_dynes_tc=270, paper_id=None)
    assert include_in_tc_pressure_chart(record) is True


def test_year_chart_requires_paper_id():
    database_record = SimpleNamespace(show_in_chart=True, pressure_gpa=200, allen_dynes_tc=270, paper_id=None)
    paper_record = SimpleNamespace(show_in_chart=True, pressure_gpa=200, allen_dynes_tc=270, paper_id=1)
    assert include_in_tc_year_chart(database_record) is False
    assert include_in_tc_year_chart(paper_record) is True
```

- [ ] **Step 2: Implement chart rules**

Create `backend/chart_rules.py`:

```python
TC_FIELDS = (
    "experimental_tc",
    "anisotropic_eliashberg_tc",
    "isotropic_eliashberg_tc",
    "allen_dynes_tc",
    "mcmillan_tc",
)


def representative_tc(record):
    for field in TC_FIELDS:
        value = getattr(record, field, None)
        if value is not None:
            return value
    return None


def include_in_tc_pressure_chart(record) -> bool:
    return bool(getattr(record, "show_in_chart", False)) and getattr(record, "pressure_gpa", None) is not None and representative_tc(record) is not None


def include_in_tc_year_chart(record) -> bool:
    return include_in_tc_pressure_chart(record) and getattr(record, "paper_id", None) is not None
```

- [ ] **Step 3: Run chart tests**

Run:

```bash
pytest tests/test_chart_rules.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit chart rules**

```bash
git add backend/chart_rules.py tests/test_chart_rules.py
git commit -m "feat: add chart inclusion rules"
```

## Task 9: Update API Schemas and Search Endpoint

**Files:**
- Modify: `backend/schemas.py`
- Modify: `backend/api/compounds.py`
- Test: `tests/test_superconductor_repository.py`

- [ ] **Step 1: Add Pydantic schemas**

Append these models to `backend/schemas.py`:

```python
from typing import Any, Literal

from pydantic import BaseModel, Field


SearchMode = Literal[
    "formula_search",
    "elements_exact_search",
    "elements_combination_search",
    "elements_contained_search",
]


class SuperconductorSearchRequest(BaseModel):
    mode: SearchMode
    formula: str | None = None
    elements: list[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class SuperconductorSummary(BaseModel):
    id: int
    chemical_system_id: int
    chemical_formula: str
    formula_normalized: str
    display_name: str
    elements_list: list[str]
    composition: dict[str, Any]
    element_ratio: dict[str, Any]


class SuperconductorSearchResponse(BaseModel):
    items: list[SuperconductorSummary]
    total: int
    page: int
    page_size: int
    has_prev: bool
    has_next: bool
```

- [ ] **Step 2: Replace compound search endpoint behavior**

In `backend/api/compounds.py`, keep `router = APIRouter(prefix="/api/compounds", tags=["compounds"])`, import the repository, and replace `/search` with:

```python
@router.post("/search", response_model=schemas.SuperconductorSearchResponse)
def search_superconductors_endpoint(
    request: schemas.SuperconductorSearchRequest,
    db: Session = Depends(get_db),
):
    result = search_superconductors(
        db,
        request.mode,
        formula=request.formula,
        elements=request.elements,
        limit=request.limit,
        offset=request.offset,
    )
    return {
        "items": [
            {
                "id": item.id,
                "chemical_system_id": item.chemical_system_id,
                "chemical_formula": item.chemical_formula,
                "formula_normalized": item.formula_normalized,
                "display_name": item.display_name,
                "elements_list": item.elements_list,
                "composition": item.composition,
                "element_ratio": item.element_ratio,
            }
            for item in result.items
        ],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "has_prev": result.has_prev,
        "has_next": result.has_next,
    }
```

Add this import:

```python
from backend.repositories.superconductors import search_superconductors
```

- [ ] **Step 3: Run existing repository tests and compile backend**

Run:

```bash
pytest tests/test_superconductor_repository.py -v
python3 -m compileall backend
```

Expected: PASS and compileall completes without syntax errors.

- [ ] **Step 4: Commit API search update**

```bash
git add backend/schemas.py backend/api/compounds.py
git commit -m "feat: add superconductor search api"
```

## Task 10: Remove Database Selector From Frontend Search

**Files:**
- Modify: `frontend/templates/index.html`
- Modify: `frontend/templates/compound.html`
- Modify: `frontend/static/js/periodic_table.js`
- Modify: `frontend/static/js/compound_page.js`

- [ ] **Step 1: Remove database selector markup**

In `frontend/templates/index.html` and `frontend/templates/compound.html`, remove the select block whose label is `数据库`. Keep review status and keyword filters.

- [ ] **Step 2: Rename frontend search modes**

In `frontend/static/js/periodic_table.js`, replace old mode names:

```javascript
const SEARCH_MODE_MAP = {
  precision: "formula_search",
  only: "elements_exact_search",
  combination: "elements_combination_search",
  contain: "elements_contained_search",
};
```

When sending `/api/compounds/search`, use the new value:

```javascript
body: JSON.stringify({
  mode: SEARCH_MODE_MAP[currentMode] || currentMode,
  formula: formulaInputValue || null,
  elements: selectedElements,
  limit,
  offset,
})
```

- [ ] **Step 3: Remove database query parameters**

In `frontend/static/js/compound_page.js`, remove `database` from fetch URLs and request bodies. Keep rendering `source_label` as a regular table/filter value once the backend returns it.

- [ ] **Step 4: Run a syntax grep check**

Run:

```bash
grep -R "database" frontend/static/js frontend/templates | grep -E "本地数据库|AI筛选数据库|Alexandria|HTSC-2025" || true
```

Expected: no remaining database selector UI strings in the main search controls.

- [ ] **Step 5: Commit frontend search cleanup**

```bash
git add frontend/templates/index.html frontend/templates/compound.html frontend/static/js/periodic_table.js frontend/static/js/compound_page.js
git commit -m "feat: remove database selector from search"
```

## Task 11: Rework Paper Upload Around Records and No Images

**Files:**
- Modify: `backend/api/papers.py`
- Modify: `backend/crud.py`
- Test: `python3 -m compileall backend`

- [ ] **Step 1: Remove image dependencies from paper upload**

In `backend/api/papers.py`, remove these imports from the upload path:

```python
UploadFile
File
process_image
validate_image_util
get_image_db
create_paper_image
```

Keep `UploadFile` and `File` only for batch-upload if still needed.

- [ ] **Step 2: Change create paper form data**

The upload endpoint should accept:

```python
doi: str = Form(...)
title: str = Form(...)
authors: str = Form("[]")
journal: str | None = Form(None)
volume: str | None = Form(None)
pages: str | None = Form(None)
year: int | None = Form(None)
abstract: str | None = Form(None)
records: str = Form(...)
```

`records` is JSON list of superconductor record payloads. Each item includes `chemical_formula`, `pressure_gpa`, `space_group_symbol`, `space_group_number`, Tc fields, stability fields, and calculation settings.

- [ ] **Step 3: Add creation helpers in `backend/crud.py`**

Add:

```python
from backend.db_helpers import build_system_key, normalize_formula


def get_or_create_chemical_system(db, elements):
    system_key, elements_list = build_system_key(elements)
    system = db.query(models.ChemicalSystem).filter_by(system_key=system_key).first()
    if system:
        return system
    system = models.ChemicalSystem(
        system_key=system_key,
        elements_list=elements_list,
        element_count=len(elements_list),
    )
    db.add(system)
    db.flush()
    return system


def get_or_create_superconductor(db, chemical_formula):
    normalized, elements, composition, ratios = normalize_formula(chemical_formula)
    existing = db.query(models.Superconductor).filter_by(formula_normalized=normalized).first()
    if existing:
        return existing
    system = get_or_create_chemical_system(db, elements)
    superconductor = models.Superconductor(
        chemical_system_id=system.id,
        chemical_formula=chemical_formula,
        formula_normalized=normalized,
        display_name=chemical_formula,
        elements_list=elements,
        composition=composition,
        element_ratio=ratios,
    )
    db.add(superconductor)
    db.flush()
    return superconductor
```

- [ ] **Step 4: Write records in one transaction**

Inside the paper upload endpoint:

```python
paper = models.Paper(
    doi=doi,
    title=title,
    journal=journal,
    volume=volume,
    pages=pages,
    year=year,
    abstract=abstract,
    authors=json.loads(authors),
    uploaded_by_user_id=current_user.id,
    review_status="pending",
)
db.add(paper)
db.flush()

for item in json.loads(records):
    superconductor = crud.get_or_create_superconductor(db, item["chemical_formula"])
    db.add(models.SuperconductorRecord(
        superconductor_id=superconductor.id,
        paper_id=paper.id,
        source_label="paper",
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
    ))
db.commit()
```

- [ ] **Step 5: Run backend compile**

Run:

```bash
python3 -m compileall backend
```

Expected: no syntax errors.

- [ ] **Step 6: Commit upload rewrite**

```bash
git add backend/api/papers.py backend/crud.py
git commit -m "feat: upload papers as superconductor records"
```

## Task 12: Update Chart Endpoints

**Files:**
- Modify: `backend/api/papers.py`
- Test: `tests/test_chart_rules.py`

- [ ] **Step 1: Replace chart data query**

In `backend/api/papers.py`, update `/stats/chart-data` to query `SuperconductorRecord` and `Paper`:

```python
from backend.chart_rules import include_in_tc_pressure_chart, include_in_tc_year_chart, representative_tc
from backend.models import Paper, SuperconductorRecord


@router.get("/stats/tc-pressure")
def get_tc_pressure_chart_data(db: Session = Depends(get_db)):
    rows = db.query(SuperconductorRecord).join(SuperconductorRecord.superconductor).all()
    return [
        {
            "x": row.pressure_gpa,
            "y": representative_tc(row),
            "formula": row.superconductor.chemical_formula,
            "space_group": row.space_group_symbol,
            "source_label": row.source_label,
        }
        for row in rows
        if include_in_tc_pressure_chart(row)
    ]


@router.get("/stats/tc-year")
def get_tc_year_chart_data(db: Session = Depends(get_db)):
    rows = db.query(SuperconductorRecord).join(Paper).join(SuperconductorRecord.superconductor).all()
    return [
        {
            "x": row.paper.year,
            "y": representative_tc(row),
            "formula": row.superconductor.chemical_formula,
            "doi": row.paper.doi,
            "source_label": row.source_label,
        }
        for row in rows
        if row.paper and row.paper.year and include_in_tc_year_chart(row)
    ]
```

- [ ] **Step 2: Preserve old route temporarily**

Keep `/stats/chart-data` as an alias for Tc-Pressure for frontend compatibility:

```python
@router.get("/stats/chart-data")
def get_chart_data(db: Session = Depends(get_db)):
    return get_tc_pressure_chart_data(db)
```

- [ ] **Step 3: Run chart tests and compile**

Run:

```bash
pytest tests/test_chart_rules.py -v
python3 -m compileall backend
```

Expected: PASS and no syntax errors.

- [ ] **Step 4: Commit chart endpoints**

```bash
git add backend/api/papers.py backend/chart_rules.py
git commit -m "feat: add record-based chart endpoints"
```

## Task 13: Update Auth and Admin Role Handling

**Files:**
- Modify: `backend/security.py`
- Modify: `backend/api/auth_routes.py`
- Modify: `backend/api/admin.py`

- [ ] **Step 1: Replace boolean role checks**

In `backend/security.py`, replace checks for `is_admin` and `is_superadmin` with:

```python
def user_is_admin(user):
    return user.role in {"admin", "superadmin"}


def user_is_superadmin(user):
    return user.role == "superadmin"
```

Update `get_current_admin` to require `user_is_admin(current_user)` and `get_current_superadmin` to require `user_is_superadmin(current_user)`.

- [ ] **Step 2: Update registration defaults**

In `backend/api/auth_routes.py`, when creating a normal user:

```python
role="user"
is_approved=False
is_email_verified=False
```

When creating an admin request:

```python
role="admin"
is_approved=False
is_email_verified=False
```

- [ ] **Step 3: Update admin permission endpoint**

In `backend/api/admin.py`, replace permission request fields with:

```python
class UserPermissionRequest(BaseModel):
    role: str
    is_approved: bool
```

Validate:

```python
if request.role not in {"user", "admin", "superadmin"}:
    raise HTTPException(status_code=400, detail="无效的用户角色")
```

- [ ] **Step 4: Run backend compile**

Run:

```bash
python3 -m compileall backend
```

Expected: no syntax errors.

- [ ] **Step 5: Commit auth/admin updates**

```bash
git add backend/security.py backend/api/auth_routes.py backend/api/admin.py
git commit -m "feat: use role-based user permissions"
```

## Task 14: Final Verification

**Files:**
- No new files

- [ ] **Step 1: Run unit tests**

Run:

```bash
pytest tests -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run backend compile**

Run:

```bash
python3 -m compileall backend
```

Expected: no syntax errors.

- [ ] **Step 3: Generate Alembic SQL**

Run:

```bash
alembic upgrade head --sql
```

Expected: SQL output creates exactly these tables:

```text
periodic_table_elements
chemical_systems
superconductors
papers
users
superconductor_records
```

- [ ] **Step 4: Check no image database model remains active**

Run:

```bash
grep -R "PaperImage\\|paper_images\\|get_image_db\\|image_data\\|thumbnail_data" backend || true
```

Expected: no active API/model references remain. If matches are in comments or deleted compatibility files, remove the stale code before committing.

- [ ] **Step 5: Commit final cleanup**

```bash
git add backend frontend tests requirements.txt alembic.ini alembic
git commit -m "chore: verify mysql database redesign"
```

## Self-Review

Spec coverage:

- Six confirmed tables are implemented by Tasks 4 and 5.
- MySQL-first database setup is implemented by Tasks 1, 3, and 5.
- Periodic table seed behavior is implemented by Task 6.
- Search mode rename and formula search are implemented by Tasks 7, 9, and 10.
- Paper authors JSON and paper-level review fields are implemented by Tasks 4 and 11.
- `paper_id + source_label` source rules are implemented by Tasks 4 and 11.
- `show_in_chart` and chart rules are implemented by Tasks 8 and 12.
- No image storage is handled by Tasks 10, 11, and 14.
- Role-based users are handled by Task 13.

Placeholder scan:

- The plan contains no vague markers, vague field names, or unbounded deferred-work instructions.

Type consistency:

- Field names match the design spec: `energy_above_hull`, `anisotropic_eliashberg_tc`, `element_n_ef`, `source_label`, and `show_in_chart`.
- Search mode names match the confirmed names: `formula_search`, `elements_exact_search`, `elements_combination_search`, `elements_contained_search`.
