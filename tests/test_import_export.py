import pytest

from backend import crud, models
from backend.scripts.export_data import SCHEMA_VERSION, build_export_payload
from backend.scripts.import_data import import_payload


def test_build_export_payload_uses_redesigned_schema(db_session):
    user = models.User(
        email="u@example.com",
        username="Uploader_1",
        password_hash="!",
        real_name="Uploader",
        role="user",
        is_approved=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.flush()

    paper = models.Paper(
        doi="10.1000/example",
        title="Example Paper",
        authors=["A. User"],
        uploaded_by_user_id=user.id,
        review_status="approved",
    )
    db_session.add(paper)
    db_session.flush()
    superconductor = crud.get_or_create_superconductor(db_session, "LaH10")
    db_session.add(
        models.SuperconductorRecord(
            superconductor_id=superconductor.id,
            paper_id=paper.id,
            source_label="paper",
            pressure_gpa=200.0,
            space_group_symbol="Fm-3m",
            mcmillan_tc=250.0,
            show_in_chart=True,
        )
    )
    db_session.commit()

    payload = build_export_payload(db_session)

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["papers"][0]["doi"] == "10.1000/example"
    assert payload["papers"][0]["uploaded_by_email"] == "u@example.com"
    assert payload["users"][0]["username"] == "Uploader_1"
    assert payload["superconductor_records"][0]["chemical_formula"] == "LaH10"
    assert payload["superconductor_records"][0]["paper_doi"] == "10.1000/example"
    assert "paper_images" not in payload


def test_import_payload_rebuilds_systems_superconductors_and_records(db_session):
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
        "papers": [
            {
                "doi": "10.1000/example",
                "title": "Example Paper",
                "authors": ["A. User"],
                "uploaded_by_email": "u@example.com",
                "review_status": "approved",
            }
        ],
        "superconductor_records": [
            {
                "paper_doi": "10.1000/example",
                "chemical_formula": "LaH10",
                "source_label": "paper",
                "pressure_gpa": 200.0,
                "space_group_symbol": "Fm-3m",
                "mcmillan_tc": 250.0,
                "show_in_chart": True,
            },
            {
                "paper_doi": None,
                "chemical_formula": "LaH10",
                "source_label": "Database A",
                "pressure_gpa": 120.0,
                "experimental_tc": 190.0,
            },
        ],
    }

    result = import_payload(db_session, payload, clear_existing=True)

    assert result["papers"] == 1
    assert result["superconductor_records"] == 2
    paper = db_session.query(models.Paper).filter_by(doi="10.1000/example").one()
    superconductor = db_session.query(models.Superconductor).filter_by(chemical_formula="LaH10").one()
    records = db_session.query(models.SuperconductorRecord).order_by(models.SuperconductorRecord.pressure_gpa).all()
    assert paper.uploaded_by_user.email == "u@example.com"
    assert superconductor.formula_normalized == "H10La"
    assert records[0].source_label == "Database A"
    assert records[1].paper_id == paper.id


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
                "structure_text": "data_LaH\n_cell_length_a 1\n",
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
    assert item["pressure_gpa"] == 100.0
    assert item["space_group_symbol"] == "P 1"
    assert item["space_group_number"] == 1
    assert item["structure_format"] == "cif"
    assert item["structure_text"] == "data_LaH\n_cell_length_a 1\n"
    assert item["structure_hash"] == "abc123"
    assert item["atom_count"] == 2
    assert item["elements_list"] == ["H", "La"]
    assert item["cell_parameters"] == {"a": 1.0}
    assert item["volume"] == 1.0
    assert item["review_status"] == "approved"
    assert item["is_default"] is True
    assert item["source_type"] == "import"
    assert item["source_label"] == "fixture"
    assert item["created_by_email"] == "u@example.com"


def test_import_payload_without_structures_is_backward_compatible(db_session):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "users": [],
        "papers": [],
        "superconductor_records": [],
    }

    result = import_payload(db_session, payload, clear_existing=True)

    assert result["superconductors_structures"] == 0
    assert build_export_payload(db_session)["superconductors_structures"] == []


def test_import_export_preserves_historical_username(db_session):
    historical_username = "sc_0123456789ab"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "users": [
            {
                "email": "legacy@example.com",
                "username": historical_username,
                "username_change_allowed": True,
                "role": "user",
            }
        ],
        "papers": [],
        "superconductor_records": [],
    }

    import_payload(db_session, payload, clear_existing=True)
    exported = build_export_payload(db_session)

    assert exported["users"][0]["username"] == historical_username
    assert exported["users"][0]["username_change_allowed"] is True


def test_import_payload_rejects_structure_missing_chemical_formula(db_session):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "users": [],
        "papers": [],
        "superconductor_records": [],
        "superconductors_structures": [
            {
                "pressure_gpa": 100.0,
                "structure_format": "cif",
                "structure_text": "data_LaH\n",
                "structure_hash": "abc123",
            }
        ],
    }

    with pytest.raises(ValueError, match=r"superconductors_structures\[0\] 缺少 chemical_formula"):
        import_payload(db_session, payload, clear_existing=True)


def test_import_payload_rejects_structure_missing_required_text(db_session):
    payload = {
        "schema_version": SCHEMA_VERSION,
        "users": [],
        "papers": [],
        "superconductor_records": [],
        "superconductors_structures": [
            {
                "chemical_formula": "LaH",
                "pressure_gpa": 100.0,
                "structure_format": "cif",
                "structure_hash": "abc123",
            }
        ],
    }

    with pytest.raises(ValueError, match=r"superconductors_structures\[0\] 缺少 structure_text"):
        import_payload(db_session, payload, clear_existing=True)
