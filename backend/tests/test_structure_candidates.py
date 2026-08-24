import pytest

from backend.services.structure_candidates import (
    StructureCandidateError,
    build_structure_candidate,
    read_atoms,
    structures_equivalent,
    validate_structure_text,
)


POSCAR = """Si conventional cell
1.0
5.4307 0.0 0.0
0.0 5.4307 0.0
0.0 0.0 5.4307
Si
2
Direct
0.0 0.0 0.0
0.25 0.25 0.25
"""


CIF = """data_si
_cell_length_a 5.4307
_cell_length_b 5.4307
_cell_length_c 5.4307
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 Si 0 0 0
Si2 Si 0.25 0.25 0.25
"""


def test_validate_cif_and_poscar_have_same_core_metadata():
    cif = validate_structure_text("cif", CIF)
    poscar = validate_structure_text("poscar", POSCAR)

    assert cif["ase_valid"] is True
    assert poscar["ase_valid"] is True
    assert cif["atom_count"] == poscar["atom_count"] == 2
    assert cif["elements"] == poscar["elements"] == ["Si"]
    assert cif["cell_parameters"]["a"] == pytest.approx(poscar["cell_parameters"]["a"], rel=1e-5)


def test_invalid_structure_has_stable_file_level_error():
    with pytest.raises(StructureCandidateError, match="无法解析") as error:
        validate_structure_text("cif", "data_broken\n_cell_length_a nope")
    assert error.value.code == "structure_parse_failed"


def test_candidate_contains_four_derived_representations_and_preserves_source():
    candidate = build_structure_candidate(
        structure_format="poscar",
        structure_text=POSCAR,
        source={"file_id": "f-1", "role": "attachment", "page": None},
        material_state_ref="ms-1",
    )

    assert candidate["original_text"] == POSCAR
    assert candidate["status"] == "valid"
    assert set(candidate["representations"]) == {"primitive", "conventional"}
    assert all(set(value) == {"cif", "poscar"} for value in candidate["representations"].values())
    assert all(
        item["validation"]["ase_valid"]
        for cells in candidate["representations"].values()
        for item in cells.values()
    )


def test_cif_and_poscar_are_periodically_equivalent():
    assert structures_equivalent(read_atoms("cif", CIF), read_atoms("poscar", POSCAR))
