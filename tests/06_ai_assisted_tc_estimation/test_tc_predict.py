from io import BytesIO

import anyio
import pytest
from fastapi import HTTPException, UploadFile

from backend.api import tc_predict


def test_read_pdos_value_uses_energy_nearest_fermi(monkeypatch):
    numpy = pytest.importorskip("numpy")
    monkeypatch.setattr(tc_predict, "_load_numeric_dependencies", lambda: (numpy, object))

    content = b"-0.2 1.5\n0.05 7.25\n0.4 3.0\n"

    assert tc_predict._read_pdos_value(content) == 7.25


def test_calculate_coupling_uses_only_supported_bond_window():
    bond_distribution = {
        0.9: 10.0,
        1.1: 2.0,
        1.3: 5.0,
    }

    assert tc_predict._calculate_coupling(bond_distribution, 0.5) == pytest.approx(1.1)


def test_predict_tc_rejects_missing_h_pdos(monkeypatch):
    numpy = pytest.importorskip("numpy")
    monkeypatch.setattr(tc_predict, "_load_numeric_dependencies", lambda: (numpy, object))
    monkeypatch.setattr(tc_predict, "_load_structure", lambda _content: object())
    monkeypatch.setattr(tc_predict, "_extract_h_sublattice", lambda _structure: ([1.1, 1.2], 2, 1.0))
    monkeypatch.setattr(tc_predict, "_read_pdos_value", lambda _content: 1.0)

    async def run():
        contcar = UploadFile(file=BytesIO(b"POSCAR"), filename="CONTCAR")
        metal = UploadFile(file=BytesIO(b"0 1\n"), filename="PDOS_La.dat")
        with pytest.raises(HTTPException) as exc:
            await tc_predict.predict_tc(contcar, [metal])

        assert exc.value.status_code == 400
        assert "缺少 PDOS_H.dat" in exc.value.detail

    anyio.run(run)


def test_predict_tc_returns_explainable_features(monkeypatch):
    numpy = pytest.importorskip("numpy")
    monkeypatch.setattr(tc_predict, "_load_numeric_dependencies", lambda: (numpy, object))
    monkeypatch.setattr(tc_predict, "_load_structure", lambda _content: object())
    monkeypatch.setattr(tc_predict, "_extract_h_sublattice", lambda _structure: ([1.1, 1.2], 2, 1.0))
    monkeypatch.setattr(tc_predict, "_normalize_bonds", lambda _bonds, _atoms: {1.1: 0.5, 1.2: 0.5})
    monkeypatch.setattr(tc_predict, "_calculate_coupling", lambda _distribution, _dos: 0.6)

    def read_pdos(upload_content):
        return 3.0 if upload_content == b"H" else 1.0

    monkeypatch.setattr(tc_predict, "_read_pdos_value", read_pdos)

    async def run():
        contcar = UploadFile(file=BytesIO(b"POSCAR"), filename="CONTCAR")
        h_file = UploadFile(file=BytesIO(b"H"), filename="PDOS_H.dat")
        metal_file = UploadFile(file=BytesIO(b"M"), filename="PDOS_La.dat")

        result = await tc_predict.predict_tc(contcar, [h_file, metal_file])

        assert result.predicted_tc == 4739.433
        assert result.f2_value == 0.288
        assert result.dos_h_ratio == 0.75
        assert result.bonds_mean == 1.15
        assert result.bonds_var == 0.0025

    anyio.run(run)
