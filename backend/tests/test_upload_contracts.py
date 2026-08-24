import pytest

from backend.ingest.upload_contracts import validate_manifest


def test_manifest_accepts_cif_poscar_and_extensionless_poscar():
    files = validate_manifest([
        {"client_id": "main", "role": "main", "filename": "paper.pdf", "size": 10},
        {"client_id": "cif", "role": "attachment", "filename": "relaxed.cif", "size": 20},
        {"client_id": "poscar", "role": "attachment", "filename": "POSCAR", "size": 30},
    ])

    assert [item["kind"] for item in files] == ["pdf", "cif", "poscar"]


def test_manifest_rejects_unknown_structure_extension():
    with pytest.raises(ValueError, match="文件类型不支持"):
        validate_manifest([
            {"client_id": "main", "role": "main", "filename": "paper.pdf", "size": 10},
            {"client_id": "bad", "role": "attachment", "filename": "structure.xyz", "size": 20},
        ])
