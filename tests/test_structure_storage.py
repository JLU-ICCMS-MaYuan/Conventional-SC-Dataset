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
