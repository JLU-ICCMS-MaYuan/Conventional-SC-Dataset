import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import models
from backend.database import Base
from backend.ingest.form_definitions import validate_definition_payload, definition_checksum
from backend.ingest.upload_contracts import SCIENTIFIC_DRAFT_SCHEMA_VERSION
from backend.ingest.property_modules import PropertyValidationError, record_checksum, validate_record
from backend.api import form_definitions as form_definition_api
from backend.services.form_definition_service import promote_custom_property
from backend.services.property_record_upgrade_service import apply_upgrade, preview_upgrade, rollback


ISSUE90_MATRIX = (
    Path(__file__).resolve().parents[2]
    / "tests/fixtures/issue90/form-definition-matrix.json"
)


def test_shared_form_definition_matrix_matches_backend_contract():
    matrix = json.loads(ISSUE90_MATRIX.read_text(encoding="utf-8"))

    assert matrix["schema_version"] == SCIENTIFIC_DRAFT_SCHEMA_VERSION
    for definition in matrix["definitions"]:
        validate_definition_payload(definition)


def test_definition_rejects_executable_schema_keywords():
    try:
        validate_definition_payload({"json_schema": {"$ref": "https://example.invalid/schema"}})
    except Exception as exc:
        assert exc.issues[0].code == "unsupported_schema_keyword"
    else:
        raise AssertionError("应拒绝远程 Schema 引用")


def test_definition_checksum_changes_when_schema_changes():
    base = {"definition_key": "record.test", "version": 1, "target_kind": "property_record", "module_code": "electronic_properties", "json_schema": {}, "core_schema": {}, "ui_schema": {}}
    assert definition_checksum(base) != definition_checksum({**base, "json_schema": {"type": "object"}})


def _definition(**overrides):
    value = {
        "definition_key": "record.superconductive_properties.predicted_tc.allen_dynes",
        "version": 1,
        "target_kind": "property_record",
        "module_code": "superconductive_properties",
        "record_type": "predicted_tc",
        "method_code": "allen_dynes",
        "property_code": "tc",
        "core_schema": {"type": "object", "properties": {"canonical_unit": {"const": "K"}}},
        "json_schema": {
            "type": "object",
            "properties": {
                "calculation_conditions": {"type": "object"},
                "solver_tolerance": {"type": "number", "maximum": 1},
            },
            "required": ["calculation_conditions"],
            "additionalProperties": False,
        },
        "ui_schema": {"fields": [{"pointer": "/solver_tolerance", "control": "number"}]},
        "status": "published",
    }
    value.update(overrides)
    value["checksum"] = definition_checksum(value)
    return SimpleNamespace(**value)


def _record(**overrides):
    value = {
        "record_key": "tc-1",
        "module_code": "superconductive_properties",
        "record_type": "predicted_tc",
        "property_code": "tc",
        "definition_key": "record.superconductive_properties.predicted_tc.allen_dynes",
        "definition_version": 1,
        "name_raw": "Tc",
        "value_kind": "number",
        "value_raw": "250 K",
        "value_number": 250,
        "canonical_unit": "K",
        "method_code": "allen_dynes",
        "payload": {"calculation_conditions": {}, "solver_tolerance": 0.1},
    }
    value.update(overrides)
    return value


def test_record_rejects_retired_or_mismatched_definition_and_full_schema():
    with pytest.raises(PropertyValidationError) as retired:
        validate_record(_record(), _definition(status="retired"))
    assert {issue.code for issue in retired.value.issues} == {"definition_not_available"}

    mismatched = _definition(method_code="mcmillan", property_code="not_tc")
    with pytest.raises(PropertyValidationError) as identity:
        validate_record(_record(), mismatched)
    assert any(issue.field.endswith("method_code") for issue in identity.value.issues)
    assert any(issue.field.endswith("property_code") for issue in identity.value.issues)

    with pytest.raises(PropertyValidationError) as schema:
        validate_record(_record(payload={"calculation_conditions": {}, "solver_tolerance": 2}), _definition())
    assert any(issue.field.endswith("solver_tolerance") for issue in schema.value.issues)


def test_definition_payload_accepts_declarative_ui_and_rejects_invalid_references():
    payload = vars(_definition()).copy()
    payload.pop("checksum")
    payload["json_schema"] = {
        "type": "object",
        "properties": {
            "calculation_conditions": {
                "type": "object",
                "title": "计算 Conditions",
                "properties": {"calculation_code": {"type": "string"}},
            },
            "parameters": {
                "type": "object",
                "properties": {
                    "mu_star": {"type": "number"},
                    "extensions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"field_key": {"type": "string"}},
                        },
                    },
                },
            },
            "solver_tolerance": {"type": "number"},
        },
    }
    payload["ui_schema"] = {
        "fields": [
            {"pointer": "/payload/calculation_conditions/calculation_code"},
            {"pointer": "/payload/parameters/mu_star"},
            {"pointer": "/payload/parameters/extensions/0/field_key"},
            {"pointer": "/solver_tolerance"},
            {"pointer": "/canonical_unit"},
        ]
    }
    validate_definition_payload(payload)

    for pointer in (
        "/missing",
        "/payload/missing/value",
        "/payload/calculation_conditions/missing",
        "/payload/parameters/extensions/not-an-index/field_key",
    ):
        payload["ui_schema"] = {"fields": [{"pointer": pointer, "control": "text"}]}
        with pytest.raises(PropertyValidationError) as error:
            validate_definition_payload(payload)
        assert error.value.issues[-1].code == "definition_invalid"


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def _db_definition(version, *, status="published", schema=None):
    data = {
        "definition_key": "record.superconductive_properties.predicted_tc.allen_dynes",
        "version": version,
        "target_kind": "property_record",
        "module_code": "superconductive_properties",
        "record_type": "predicted_tc",
        "method_code": "allen_dynes",
        "property_code": "tc",
        "core_schema": {},
        "json_schema": schema or {"type": "object", "properties": {"calculation_conditions": {"type": "object"}}, "required": ["calculation_conditions"], "additionalProperties": False},
        "ui_schema": {},
    }
    return models.FormDefinition(**data, status=status, checksum=definition_checksum(data))


def test_definition_upgrade_round_trip_and_stale_event_rejection():
    db = _session()
    v1 = _db_definition(1)
    v2 = _db_definition(2, schema={"type": "object", "properties": {"calculation_conditions": {"type": "object"}, "solver": {"type": "number"}}, "required": ["calculation_conditions", "solver"], "additionalProperties": False})
    module = models.PropertyModule(id=1, module_key="m1", paper_id=1, paper_revision=1, material_state_id=1, module_code="superconductive_properties", definition_key="module.superconductive_properties", definition_version=1, display_order=0, metadata_json={})
    source = _record(payload={"calculation_conditions": {}})
    checksum = record_checksum(source)
    record = models.PropertyRecord(id=1, module=module, paper_id=1, paper_revision=1, material_state_id=1, record_key="tc-1", record_type="predicted_tc", property_code="tc", definition=v1, definition_key=v1.definition_key, definition_version=1, name_raw="Tc", value_kind="number", value_raw="250 K", value_number=250, canonical_unit="K", method_code="allen_dynes", is_representative=False, payload_json=source["payload"], source_fingerprint="a" * 64, record_checksum=checksum)
    db.add_all([v1, v2, module, record])
    db.flush()

    preview = preview_upgrade(record, v2, {"calculation_conditions": {}, "solver": 0.01})
    event = apply_upgrade(db, record, v2, 1, checksum, preview["preview_checksum"], {"calculation_conditions": {}, "solver": 0.01})
    db.flush()
    assert record.definition_version == 2
    reverse = rollback(db, record, event, 1, record.record_checksum)
    db.flush()
    assert record.definition_version == 1
    assert record.payload_json == {"calculation_conditions": {}}
    assert reverse.previous_event_id == event.id
    with pytest.raises(PropertyValidationError) as stale:
        rollback(db, record, event, 1, record.record_checksum)
    assert stale.value.issues[0].code == "definition_rollback_stale"


def test_custom_property_promotion_requires_approved_snapshot_and_is_idempotent():
    db = _session()
    paper = models.Paper(id=1, title="P", year=2026, review_status="approved", content_revision=2, approved_revision=2, superconductor_kind="unknown")
    module = models.PropertyModule(id=1, module_key="m1", paper_id=1, paper_revision=2, material_state_id=1, module_code="electronic_properties", definition_key="module.electronic_properties", definition_version=1, display_order=0, metadata_json={})
    record = models.PropertyRecord(id=1, module=module, paper_id=1, paper_revision=2, material_state_id=1, record_key="custom-1", record_type="property", property_code="custom", custom_property_key="opaque-1", definition_id=1, definition_key="record.electronic_properties.custom", definition_version=1, name_raw="Novel value", value_kind="number", value_raw="1.2 eV", value_number=1.2, unit_raw="eV", payload_json={}, source_fingerprint="b" * 64, record_checksum="c" * 64)
    db.add_all([paper, module, record])
    db.flush()
    request = dict(paper_id=1, record_key="custom-1", actor_id=7, operation_id="op-1", expected_paper_revision=2, source_checksum="c" * 64, target_property_code="novel_value", display_name="Novel value", module_code="electronic_properties", value_kind="number", canonical_unit=None)
    result = promote_custom_property(db, **request)
    again = promote_custom_property(db, **request)
    assert again == result
    assert record.property_code == "custom"
    assert record.definition_key == "record.electronic_properties.custom"
    with pytest.raises(PropertyValidationError) as conflict:
        promote_custom_property(db, **{**request, "target_property_code": "different"})
    assert conflict.value.issues[0].code == "property_promotion_conflict"


def test_upgrade_api_routes_and_located_400_error_contract():
    paths = {route.path for route in form_definition_api.promotion_router.routes}
    assert "/api/admin/papers/{paper_id}/property-records/{record_key}/definition-upgrade/preview" in paths
    assert "/api/admin/papers/{paper_id}/property-records/{record_key}/definition-upgrade/apply" in paths
    assert "/api/admin/papers/{paper_id}/property-records/{record_key}/definition-upgrade/rollback" in paths
    error = PropertyValidationError([
        form_definition_api.PropertyIssue("payload.parameters", "schema_validation_failed", "参数无效")
    ])
    response = form_definition_api._error(error)
    assert response.status_code == 400
    assert response.detail["issues"][0] == {
        "field": "payload.parameters", "code": "schema_validation_failed", "message": "参数无效",
    }
