from backend.ingest.form_definitions import validate_definition_payload, definition_checksum


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
