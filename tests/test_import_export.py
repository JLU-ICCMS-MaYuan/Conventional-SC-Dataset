from backend import crud, models
from backend.export_data import SCHEMA_VERSION, build_export_payload
from backend.import_data import import_payload


def test_build_export_payload_uses_redesigned_schema(db_session):
    user = models.User(
        email="u@example.com",
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
