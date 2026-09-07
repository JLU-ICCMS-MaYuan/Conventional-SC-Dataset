import json

import pytest

from backend.ingest.property_modules import PropertyValidationError, validate_record
from backend.ingest.upload_contracts import convert_legacy_state


def _tc(**overrides):
    value = {
        "record_key": "tc-1", "module_code": "superconductive_properties", "record_type": "predicted_tc",
        "property_code": "tc", "name_raw": "Tc", "value_kind": "number", "value_raw": "250 K",
        "value_number": 250, "canonical_unit": "K", "method_code": "allen_dynes",
        "payload": {"calculation_conditions": {}, "parameters": {}}
    }
    value.update(overrides)
    return value


def test_issue90_record_requires_matching_conditions():
    with pytest.raises(PropertyValidationError) as error:
        validate_record(_tc(payload={"experimental_conditions": {}}))
    assert error.value.issues[0].code == "invalid_condition_type"


def test_issue90_record_checksum_is_stable_and_payload_is_copied():
    source = _tc()
    result = validate_record(source)
    source["payload"]["parameters"]["mu_star"] = 0.2
    assert result["payload"]["parameters"] == {}
    assert len(result["record_checksum"]) == 64


def test_issue90_legacy_conversion_is_single_direction_and_non_mutating():
    old = {"tc_results": [{"tc_method": "allen_dynes", "tc_value_k": 250, "value_raw": "250"}], "properties": []}
    converted = convert_legacy_state(old)
    assert "property_modules" not in old
    assert converted["property_modules"][0]["records"][0]["record_type"] == "predicted_tc"

