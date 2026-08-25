from backend.scripts.migrate_material_classifications import classify_legacy_row


FAMILY_IDS = {"hydrogen_based": 1, "copper_based": 2}


def row(value="hydride"):
    return {
        "id": 7,
        "paper_id": 3,
        "superconductor_id": 5,
        "pressure_gpa": 150,
        "superconductor_type": value,
    }


def test_unique_whitelisted_match_is_ready():
    result = classify_legacy_row(
        row("高压氢化物"),
        target_states=[{"id": 11, "material_family_id": None}],
        family_ids_by_code=FAMILY_IDS,
    )
    assert result["status"] == "ready"
    assert result["target_family_id"] == 1


def test_unknown_legacy_value_is_unmapped():
    result = classify_legacy_row(
        row("others"),
        target_states=[{"id": 11, "material_family_id": None}],
        family_ids_by_code=FAMILY_IDS,
    )
    assert result["status"] == "unmapped"


def test_multiple_target_states_are_ambiguous():
    result = classify_legacy_row(
        row(),
        target_states=[
            {"id": 11, "material_family_id": None},
            {"id": 12, "material_family_id": None},
        ],
        family_ids_by_code=FAMILY_IDS,
    )
    assert result["status"] == "ambiguous"


def test_existing_different_family_is_conflict():
    result = classify_legacy_row(
        row(),
        target_states=[{"id": 11, "material_family_id": 2}],
        family_ids_by_code=FAMILY_IDS,
    )
    assert result["status"] == "conflict"
