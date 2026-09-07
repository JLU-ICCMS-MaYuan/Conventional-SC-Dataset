import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import models
from backend.api.material_state_export import build_material_state_export
from backend.database import Base
from backend.ingest.form_definitions import definition_checksum


def _definition(key, target_kind, *, record_type=None, method_code=None, property_code=None):
    data = {
        "definition_key": key, "version": 1, "target_kind": target_kind,
        "module_code": "superconductive_properties", "record_type": record_type,
        "method_code": method_code, "property_code": property_code,
        "core_schema": {}, "json_schema": {"type": "object"}, "ui_schema": {},
    }
    return models.FormDefinition(**data, status="published", checksum=definition_checksum(data))


def test_export_is_self_contained_and_json_serializable():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    paper = models.Paper(id=1, title="LaH10", year=2026, review_status="approved", content_revision=1, approved_revision=1, superconductor_kind="unknown")
    system = models.ChemicalSystem(id=1, paper_id=1, paper_revision=1, system_key="H-La", elements_list=["H", "La"], element_count=2)
    material = models.Superconductor(id=1, paper_id=1, paper_revision=1, chemical_system_id=1, chemical_formula="LaH10", formula_normalized="H10La", composition_key="H:10|La:1", display_name="LaH10", elements_list=["H", "La"], composition={"H": 10, "La": 1}, element_ratio={"H": 10 / 11, "La": 1 / 11})
    state = models.MaterialState(id=1, state_key="state-1", paper_id=1, paper_revision=1, superconductor_id=1, state_kind="theoretical", crystal_system="unknown", material_dimensionality="unknown", pressure_value_gpa=200)
    structure = models.StructureModel(id=1, paper_id=1, paper_revision=1, material_state_id=1, structure_format="cif", structure_text="data_LaH10", structure_hash="a" * 64, nuclear_treatment="unknown", source_locator="LaH10.cif")
    module_definition = _definition("module.superconductive_properties", "property_module")
    record_definition = _definition("record.superconductive_properties.predicted_tc.allen_dynes", "property_record", record_type="predicted_tc", method_code="allen_dynes", property_code="tc")
    module = models.PropertyModule(id=1, module_key="m1", paper_id=1, paper_revision=1, material_state_id=1, module_code="superconductive_properties", definition_key=module_definition.definition_key, definition_version=1, display_order=0, metadata_json={})
    record = models.PropertyRecord(id=1, record_key="tc-1", paper_id=1, paper_revision=1, material_state_id=1, module_id=1, record_type="predicted_tc", property_code="tc", definition_id=2, definition_key=record_definition.definition_key, definition_version=1, name_raw="Tc", value_kind="number", value_raw="250 K", value_number=250, canonical_unit="K", method_code="allen_dynes", is_representative=True, structure_key="1", payload_json={"calculation_conditions": {}, "parameters": {"mu_star": {"value_number": 0.1, "unit": "1"}}}, source_fingerprint="b" * 64, record_checksum="c" * 64)
    evidence = models.PaperEvidence(id=1, paper_id=1, paper_revision=1, paper_chunk_id=1, field_path="material_states[0].tc", section="Results", page_start=3, page_end=3, quote="Tc reaches 250 K")
    link = models.PropertyRecordEvidence(record_id=1, paper_evidence_id=1, paper_id=1, paper_revision=1, field_path="value_number", evidence_role="primary")
    db.add_all([paper, system, material, state, structure, module_definition, record_definition, module, record, evidence, link])
    db.commit()

    payload = build_material_state_export(db, paper_id=1, state_key="state-1", user=None)
    json.dumps(payload)
    assert payload["chemical_system"]["system_key"] == "H-La"
    assert payload["material_state"]["structures"][0]["content"] == "data_LaH10"
    exported_record = payload["property_modules"][0]["records"][0]
    assert exported_record["payload"]["parameters"]["mu_star"]["value_number"] == 0.1
    assert exported_record["evidences"][0]["quote"] == "Tc reaches 250 K"
    assert {item["definition_key"] for item in payload["definitions"]} == {module_definition.definition_key, record_definition.definition_key}
