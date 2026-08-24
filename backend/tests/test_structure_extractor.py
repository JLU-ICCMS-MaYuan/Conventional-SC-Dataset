from backend.ingest.structure_extractor import extract_structure_candidates


def test_extracts_explicit_fractional_coordinate_table_with_page_evidence():
    text = """<!-- page: 4 -->
The lattice parameters are a = 3.6, b = 3.6, c = 3.6, alpha = 90, beta = 90, gamma = 90.
Table 2 lists fractional coordinates:
atom x y z
Cu1 Cu 0 0 0
"""
    candidates = extract_structure_candidates(
        text,
        source={"file_id": "pdf-1", "filename": "paper.pdf", "role": "main"},
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["status"] == "valid"
    assert candidate["derivation"]["kind"] == "direct_coordinates"
    assert candidate["sources"][0]["page"] == 4
    assert candidate["validation"]["atom_count"] == 1
    assert candidate["representations"]["conventional"]["cif"]["text"]


def test_blocks_missing_coordinate_mode_instead_of_guessing():
    text = """<!-- page: 2 -->
The cell has a = 3, b = 3, c = 3, alpha = 90, beta = 90, gamma = 90.
Atomic coordinates:
Cu1 Cu 0 0 0
"""
    candidates = extract_structure_candidates(
        text,
        source={"file_id": "pdf-2", "filename": "paper.pdf"},
    )

    assert len(candidates) == 1
    assert candidates[0]["status"] == "blocked"
    assert candidates[0]["validation"]["code"] == "pdf_structure_incomplete"


def test_keeps_explicit_structures_on_separate_pages_separate():
    text = """<!-- page: 1 -->
Lattice a = 3, b = 3, c = 3, alpha = 90, beta = 90, gamma = 90. Fractional coordinates:
Cu1 Cu 0 0 0
<!-- page: 2 -->
Lattice a = 4, b = 4, c = 4, alpha = 90, beta = 90, gamma = 90. Fractional coordinates:
Fe1 Fe 0 0 0
"""
    candidates = extract_structure_candidates(text, source={"file_id": "pdf-3", "filename": "paper.pdf"})

    assert len(candidates) == 2
    assert [item["sources"][0]["page"] for item in candidates] == [1, 2]
    assert [item["validation"]["elements"] for item in candidates] == [["Cu"], ["Fe"]]
