import pytest

from backend.ingest.upload_contracts import (
    SCIENTIFIC_DRAFT_SCHEMA_VERSION,
    UploadContractError,
    convert_legacy_scientific_draft,
    convert_legacy_state,
    validate_manifest,
)


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


def test_issue90_legacy_scientific_state_conversion_is_one_way_and_idempotent():
    source = {
        "tc_results": [{
            "result_kind": "experimental", "tc_method": "experimental",
            "tc_value_k": 203.0, "value_raw": "203 K", "evidences": [{"id": 7}],
            "evidence": {"page": 4, "quote": "Tc reaches 203 K."},
        }],
        "properties": [{"name": "density of states", "value": 1.5, "unit": "states/eV"}],
    }

    converted = convert_legacy_state(source)

    assert converted["schema_version"] == SCIENTIFIC_DRAFT_SCHEMA_VERSION
    assert "tc_results" not in converted and "properties" not in converted
    assert [item["module_code"] for item in converted["property_modules"]] == [
        "superconductive_properties", "electronic_properties",
    ]
    tc = converted["property_modules"][0]["records"][0]
    assert tc["method_code"] == "resistivity"
    assert tc["evidences"] == [{"id": 7}]
    assert tc["evidence"] == {"page": 4, "quote": "Tc reaches 203 K."}
    assert convert_legacy_state(converted) == converted
    assert "property_modules" not in source


def test_issue90_legacy_scientific_state_conversion_rejects_unknown_or_lossy_input():
    with pytest.raises(UploadContractError) as version_error:
        convert_legacy_state({"schema_version": 99, "property_modules": []})
    assert version_error.value.code == "unsupported_scientific_schema_version"

    with pytest.raises(UploadContractError) as range_error:
        convert_legacy_state({"properties": [{"name": "gap", "value_min": 1.0}]})
    assert range_error.value.code == "legacy_scientific_conversion_failed"


def test_issue90_legacy_conversion_preserves_zero_false_and_range_raw_values():
    converted = convert_legacy_state({
        "tc_results": [{
            "result_kind": "theoretical", "tc_method": "mcmillan",
            "tc_value_k": 0,
        }],
        "properties": [
            {"name": "stable", "value": False},
            {"name": "gap", "value_min": 0, "value_max": 1},
        ],
    })
    records = [
        record
        for module in converted["property_modules"]
        for record in module["records"]
    ]

    assert [record["value_raw"] for record in records] == ["0", "False", "0-1"]
    assert records[1]["value_boolean"] is False


def test_issue90_scientific_draft_conversion_upgrades_every_state():
    converted = convert_legacy_scientific_draft({
        "paper": {"title": "example"},
        "material_states": [{"tc_results": []}, {"property_modules": []}],
    })

    assert converted["scientific_schema_version"] == SCIENTIFIC_DRAFT_SCHEMA_VERSION
    assert all(
        state["schema_version"] == SCIENTIFIC_DRAFT_SCHEMA_VERSION
        for state in converted["material_states"]
    )


def test_issue90_current_state_discards_stale_legacy_arrays():
    converted = convert_legacy_state({
        "schema_version": SCIENTIFIC_DRAFT_SCHEMA_VERSION,
        "property_modules": [],
        "tc_results": [{"tc_value_k": 99}],
        "properties": [{"name": "stale", "value": 1}],
    })

    assert converted["property_modules"] == []
    assert "tc_results" not in converted
    assert "properties" not in converted
