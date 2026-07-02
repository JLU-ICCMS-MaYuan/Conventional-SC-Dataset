import pytest
from fastapi import HTTPException

from backend import crud, models
from backend.services.structure_storage import (
    approve_structure,
    create_structure,
    default_structure_for_record,
    representative_structure_for,
    reject_structure,
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


def _pending_superconductor(formula):
    system = models.ChemicalSystem(
        system_key=formula,
        elements_list=["H", "La"],
        element_count=2,
    )
    return models.Superconductor(
        chemical_system=system,
        chemical_formula=formula,
        formula_normalized=formula,
        display_name=formula,
        elements_list=["H", "La"],
        composition={"La": 1, "H": 1},
        element_ratio={"La": 1, "H": 1},
    )


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


def test_validate_structure_payload_rejects_blank_text():
    with pytest.raises(HTTPException) as exc:
        validate_structure_payload("cif", "   ")

    assert exc.value.status_code == 400
    assert "blank" in exc.value.detail


def test_validate_structure_payload_rejects_parse_failure():
    with pytest.raises(HTTPException) as exc:
        validate_structure_payload("cif", "not a valid cif")

    assert exc.value.status_code == 400
    assert "Unable to parse cif" in exc.value.detail


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
    assert "structure_text" not in payload

    payload_with_text = serialize_structure(structure, include_text=True)
    assert payload_with_text["structure_text"] == CIF_TEXT


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


def test_approve_structure_clears_unflushed_same_identity_defaults(db_session, monkeypatch):
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

    with monkeypatch.context() as context:
        context.setattr(
            db_session,
            "flush",
            lambda *args, **kwargs: pytest.fail("approve_structure must not flush manually"),
        )
        approve_structure(db_session, first)
        approve_structure(db_session, second)

    db_session.commit()

    default_count = (
        db_session.query(models.SuperconductorStructure)
        .filter(
            models.SuperconductorStructure.superconductor_id == superconductor.id,
            models.SuperconductorStructure.pressure_gpa == 100.0,
            models.SuperconductorStructure.space_group_symbol == "P 1",
            models.SuperconductorStructure.space_group_number == 1,
            models.SuperconductorStructure.is_default.is_(True),
        )
        .count()
    )

    assert default_count == 1
    assert first.is_default is False
    assert second.is_default is True
    assert second.review_status == "approved"


def test_approve_structure_keeps_defaults_for_different_pending_parents(db_session):
    user = _user(db_session)
    first_superconductor = _pending_superconductor("PendingLaH")
    second_superconductor = _pending_superconductor("PendingLaH2")
    db_session.add_all([first_superconductor, second_superconductor])
    first = create_structure(
        db_session,
        superconductor=first_superconductor,
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
        superconductor=second_superconductor,
        pressure_gpa=100.0,
        space_group_symbol="P 1",
        space_group_number=1,
        structure_format="poscar",
        structure_text=POSCAR_TEXT,
        source_type="admin_upload",
        source_label="second",
        created_by_user=user,
    )

    approve_structure(db_session, first)
    approve_structure(db_session, second)
    db_session.commit()

    assert first.superconductor_id != second.superconductor_id
    assert first.is_default is True
    assert second.is_default is True


def test_reject_structure_marks_rejected_and_clears_default(db_session):
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
    approve_structure(db_session, structure)

    reject_structure(structure)

    assert structure.review_status == "rejected"
    assert structure.is_default is False


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


def test_default_structure_for_record_matches_record_identity(db_session):
    user = _user(db_session)
    superconductor = crud.get_or_create_superconductor(db_session, "LaH")
    matching = create_structure(
        db_session,
        superconductor=superconductor,
        pressure_gpa=100.0,
        space_group_symbol="P 1",
        space_group_number=1,
        structure_format="cif",
        structure_text=CIF_TEXT,
        source_type="admin_upload",
        source_label="matching",
        created_by_user=user,
    )
    other_pressure = create_structure(
        db_session,
        superconductor=superconductor,
        pressure_gpa=200.0,
        space_group_symbol="P 1",
        space_group_number=1,
        structure_format="poscar",
        structure_text=POSCAR_TEXT,
        source_type="admin_upload",
        source_label="other-pressure",
        created_by_user=user,
    )
    approve_structure(db_session, matching)
    approve_structure(db_session, other_pressure)
    record = models.SuperconductorRecord(
        superconductor_id=superconductor.id,
        source_label="record",
        pressure_gpa=100.0,
        space_group_symbol="P 1",
        space_group_number=1,
    )
    db_session.add(record)
    db_session.commit()

    default_structure = default_structure_for_record(db_session, record)

    assert default_structure.id == matching.id


def test_default_structure_for_record_matches_nullable_space_group_identity(db_session):
    user = _user(db_session)
    superconductor = crud.get_or_create_superconductor(db_session, "LaH")
    nullable_match = create_structure(
        db_session,
        superconductor=superconductor,
        pressure_gpa=100.0,
        space_group_symbol=None,
        space_group_number=None,
        structure_format="cif",
        structure_text=CIF_TEXT,
        source_type="admin_upload",
        source_label="nullable-match",
        created_by_user=user,
    )
    non_nullable = create_structure(
        db_session,
        superconductor=superconductor,
        pressure_gpa=100.0,
        space_group_symbol="P 1",
        space_group_number=1,
        structure_format="poscar",
        structure_text=POSCAR_TEXT,
        source_type="admin_upload",
        source_label="non-nullable",
        created_by_user=user,
    )
    approve_structure(db_session, nullable_match)
    approve_structure(db_session, non_nullable)
    record = models.SuperconductorRecord(
        superconductor_id=superconductor.id,
        source_label="record",
        pressure_gpa=100.0,
        space_group_symbol=None,
        space_group_number=None,
    )
    db_session.add(record)
    db_session.commit()

    default_structure = default_structure_for_record(db_session, record)

    assert default_structure.id == nullable_match.id
