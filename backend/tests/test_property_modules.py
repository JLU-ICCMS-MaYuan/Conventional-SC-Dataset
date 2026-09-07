import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend import models
from backend.database import Base
from backend.ingest.form_definitions import definition_checksum
from backend.ingest.property_modules import PropertyValidationError, persist_property_modules, validate_record


def _definition():
    data = {
        "definition_key": "record.superconductive_properties.predicted_tc.allen_dynes",
        "version": 1,
        "target_kind": "property_record",
        "module_code": "superconductive_properties",
        "record_type": "predicted_tc",
        "method_code": "allen_dynes",
        "property_code": "tc",
        "core_schema": {},
        "json_schema": {
            "type": "object",
            "properties": {"calculation_conditions": {"type": "object"}},
            "required": ["calculation_conditions"],
            "additionalProperties": False,
        },
        "ui_schema": {},
    }
    return models.FormDefinition(**data, status="published", checksum=definition_checksum(data))


def _module_definition():
    data = {
        "definition_key": "module.superconductive_properties",
        "version": 1,
        "target_kind": "property_module",
        "module_code": "superconductive_properties",
        "record_type": None,
        "method_code": None,
        "property_code": None,
        "core_schema": {},
        "json_schema": {"type": "object"},
        "ui_schema": {},
    }
    return models.FormDefinition(**data, status="published", checksum=definition_checksum(data))


def _record(key="tc-1", *, representative=False, evidences=None):
    return {
        "record_key": key,
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
        "is_representative": representative,
        "payload": {"calculation_conditions": {}},
        "evidences": evidences or [],
    }


def _module(records):
    return {
        "module_key": "module-superconductive",
        "module_code": "superconductive_properties",
        "definition_key": "module.superconductive_properties",
        "definition_version": 1,
        "display_order": 0,
        "records": records,
    }


def test_persistence_applies_explicit_deletion_and_saves_same_revision_evidence():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add_all([_definition(), _module_definition()])
            session.add(models.PaperEvidence(id=7, paper_id=1, paper_revision=2, paper_chunk_id=1, field_path="source", quote="Tc is 250 K"))
            await session.flush()
            await persist_property_modules(
                session,
                paper_id=1,
                paper_revision=2,
                material_state_id=10,
                modules=[_module([_record(evidences=[{"paper_evidence_id": 7, "field_path": "value_number"}])])],
            )
            await session.flush()
            links = (await session.execute(select(models.PropertyRecordEvidence))).scalars().all()
            assert [(item.paper_evidence_id, item.field_path) for item in links] == [(7, "value_number")]

            await persist_property_modules(
                session,
                paper_id=1,
                paper_revision=2,
                material_state_id=10,
                modules=[],
                deleted_record_keys=["tc-1"],
                deleted_module_keys=["module-superconductive"],
            )
            await session.flush()
            assert (await session.execute(select(models.PropertyModule))).scalars().all() == []
            assert (await session.execute(select(models.PropertyRecord))).scalars().all() == []
        await engine.dispose()

    asyncio.run(scenario())


def test_persistence_rejects_cross_revision_evidence():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add_all([_definition(), _module_definition()])
            session.add(models.PaperEvidence(id=7, paper_id=1, paper_revision=1, paper_chunk_id=1, field_path="source", quote="old"))
            await session.flush()
            with pytest.raises(PropertyValidationError) as error:
                await persist_property_modules(
                    session,
                    paper_id=1,
                    paper_revision=2,
                    material_state_id=10,
                    modules=[_module([_record(evidences=[{"paper_evidence_id": 7}])])],
                )
            assert error.value.issues[0].code == "cross_revision_reference"
        await engine.dispose()

    asyncio.run(scenario())


def test_range_with_missing_bound_returns_located_validation_error():
    record = _record()
    record.update({"value_kind": "range", "value_number": None, "value_min": 10, "value_max": None})
    with pytest.raises(PropertyValidationError) as error:
        validate_record(record)
    assert error.value.issues[0].field.endswith("value_kind")
    assert error.value.issues[0].code == "schema_validation_failed"


def test_tc_requires_explicit_kelvin_and_nonnegative_value():
    record = _record()
    record.update({"canonical_unit": None, "value_number": -1})
    with pytest.raises(PropertyValidationError) as error:
        validate_record(record)
    fields = {issue.field for issue in error.value.issues}
    assert "record.canonical_unit" in fields
    assert "record.value_number" in fields
