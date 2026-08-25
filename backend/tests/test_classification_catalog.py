from backend.services.classification_catalog import (
    MATERIAL_DIMENSIONALITIES,
    convert_legacy_draft,
    count_formula_elements,
    normalize_classification_name,
    resolve_seed_material_family,
)


def test_normalization_is_deterministic_across_labels_and_codes():
    assert normalize_classification_name("  IRON_based  ") == "iron based"
    assert normalize_classification_name("Hydrogen-Based\u3000Superconductor") == (
        "hydrogen based superconductor"
    )


def test_seed_aliases_map_to_one_canonical_family():
    matches = [
        resolve_seed_material_family(value)
        for value in ("hydride", "氢化物", "高压氢化物", "Hydrogen-based superconductor")
    ]

    assert {match.code for match in matches if match} == {"hydrogen_based"}
    assert {match.name for match in matches if match} == {"氢基超导体"}
    assert resolve_seed_material_family("carbon") is None
    assert resolve_seed_material_family("others") is None


def test_element_count_means_distinct_elements_not_stoichiometric_sum():
    assert count_formula_elements("LaH10") == 2
    assert count_formula_elements("CeCu2Si2") == 3
    assert count_formula_elements("UPt3") == 2
    assert count_formula_elements("not a formula") is None


def test_material_dimensionality_has_confirmed_controlled_values():
    assert MATERIAL_DIMENSIONALITIES == {
        "zero_dimensional": "零维",
        "one_dimensional": "一维",
        "two_dimensional": "二维",
        "three_dimensional": "三维",
        "quasi_one_dimensional": "准一维",
        "quasi_two_dimensional": "准二维",
        "unknown": "未知",
    }


def test_old_draft_is_converted_once_without_retaining_sc_type():
    draft = {
        "sc_type": "hydride",
        "material_states": [
            {"material": "LaH10"},
            {"material": "LaH10", "material_family": {"id": 9, "name": "已确认", "status": "confirmed"}},
        ],
    }
    converted = convert_legacy_draft(
        draft,
        families_by_code={"hydrogen_based": {"id": 1, "name": "氢基超导体"}},
    )

    assert "sc_type" not in converted
    assert converted["material_states"][0]["material_family"] == {
        "id": 1,
        "name": "氢基超导体",
        "status": "confirmed",
    }
    assert converted["material_states"][1]["material_family"]["id"] == 9
    assert converted["classification_migration_warnings"]


def test_ambiguous_old_values_become_pending_instead_of_guessed():
    converted = convert_legacy_draft(
        {"sc_type": "carbon", "material_states": [{"material": "C"}]},
        families_by_code={},
    )

    assert converted["material_states"][0]["material_family"] == {
        "id": None,
        "name": "carbon",
        "status": "pending",
    }
