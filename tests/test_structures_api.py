import anyio
from httpx import ASGITransport, AsyncClient

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


def _override_dependencies(db_session, user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user


def test_structure_upload_review_representative_and_raw_download(db_session):
    user = _admin(db_session)
    crud.get_or_create_superconductor(db_session, "LaH")
    db_session.commit()
    _override_dependencies(db_session, user)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            created = await client.post(
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

            reviewed = await client.post(f"/api/structures/{structure_id}/review", json={"status": "approved"})
            assert reviewed.status_code == 200
            assert reviewed.json()["is_default"] is True

            representative = await client.get(
                "/api/structures/representative",
                params={"formula": "LaH", "space_group": "P 1"},
            )
            assert representative.status_code == 200
            assert representative.json()["id"] == structure_id

            raw = await client.get(f"/api/structures/{structure_id}/raw")
            assert raw.status_code == 200
            assert "La1 La" in raw.text
            assert raw.headers["content-type"].startswith("chemical/x-cif")

    try:
        anyio.run(run)
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
    _override_dependencies(db_session, user)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            created = await client.post(
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
            await client.post(f"/api/structures/{structure_id}/review", json={"status": "approved"})

            by_record = await client.get(f"/api/structures/by-record/{record.id}")
            assert by_record.status_code == 200
            assert by_record.json()["id"] == structure_id

    try:
        anyio.run(run)
    finally:
        app.dependency_overrides.clear()
