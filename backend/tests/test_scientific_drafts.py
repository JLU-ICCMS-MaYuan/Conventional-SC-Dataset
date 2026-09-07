import asyncio
import os


os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-scientific-drafts-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from backend import models
from backend.ingest.form_definitions import definition_checksum
from backend.ingest.property_modules import EXPERIMENTAL_METHODS, THEORETICAL_METHODS
from backend.ingest.scientific_drafts import _property_modules_for_state, persist_scientific_draft
from backend.services.structure_candidates import build_structure_candidate


class _EmptyResult:
    def __init__(self, values=()):
        self._values = list(values)

    def scalar_one_or_none(self):
        return self._values[0] if self._values else None

    def scalars(self):
        return self

    def all(self):
        return list(self._values)


def _published_definition(definition_id, definition_key, module_code, **overrides):
    data = {
        "definition_key": definition_key,
        "version": 1,
        "target_kind": "property_module",
        "module_code": module_code,
        "record_type": None,
        "method_code": None,
        "property_code": None,
        "core_schema": {},
        "json_schema": {"type": "object", "additionalProperties": True},
        "ui_schema": {},
    }
    data.update(overrides)
    return models.FormDefinition(
        id=definition_id,
        status="published",
        checksum=definition_checksum(data),
        **data,
    )


def _published_definitions():
    definitions = []
    definition_id = 1
    for module_code in models.PROPERTY_MODULE_CODES:
        definitions.append(_published_definition(
            definition_id,
            f"module.{module_code}",
            module_code,
        ))
        definition_id += 1
        definitions.append(_published_definition(
            definition_id,
            f"record.{module_code}.custom",
            module_code,
            target_kind="property_record",
            record_type="property",
            property_code="custom",
        ))
        definition_id += 1
    for method_code in sorted(THEORETICAL_METHODS):
        definitions.append(_published_definition(
            definition_id,
            f"record.superconductive_properties.predicted_tc.{method_code}",
            "superconductive_properties",
            target_kind="property_record",
            record_type="predicted_tc",
            method_code=method_code,
            property_code="tc",
            json_schema={
                "type": "object",
                "properties": {
                    "calculation_conditions": {"type": "object"},
                    "parameters": {"type": "object"},
                },
                "required": ["calculation_conditions"],
                "additionalProperties": True,
            },
        ))
        definition_id += 1
    for method_code in sorted(EXPERIMENTAL_METHODS):
        definitions.append(_published_definition(
            definition_id,
            f"record.superconductive_properties.measured_tc.{method_code}",
            "superconductive_properties",
            target_kind="property_record",
            record_type="measured_tc",
            method_code=method_code,
            property_code="tc",
            json_schema={
                "type": "object",
                "properties": {"experimental_conditions": {"type": "object"}},
                "required": ["experimental_conditions"],
                "additionalProperties": True,
            },
        ))
        definition_id += 1
    return definitions


class _RecordingAsyncSession:
    def __init__(self):
        self.added = []
        self._next_id = 1
        self._definitions = _published_definitions()

    async def execute(self, statement):
        descriptions = getattr(statement, "column_descriptions", ())
        entity = descriptions[0].get("entity") if descriptions else None
        if entity is models.FormDefinition:
            return _EmptyResult(self._definitions)
        if entity in {
            models.PropertyModule,
            models.PropertyRecord,
            models.PropertyRecordEvidence,
        }:
            return _EmptyResult(item for item in self.added if isinstance(item, entity))
        return _EmptyResult()

    def add(self, entity):
        if getattr(entity, "id", None) is None and hasattr(entity, "id"):
            entity.id = self._next_id
            self._next_id += 1
        self.added.append(entity)

    async def flush(self):
        return None


def test_v2_property_modules_preserve_payload_and_standard_property_identity():
    state = {
        "schema_version": 2,
        "calculation_context": {"k_grid": "legacy-must-not-win"},
        "experimental_context": {"sample_label": "legacy-must-not-win"},
        "property_modules": [{
            "module_key": "electronic-main",
            "module_code": "electronic_properties",
            "records": [{
                "record_key": "dos-1",
                "record_type": "property",
                "property_code": "density_of_states",
                "definition_key": "record.electronic_properties.property.density_of_states",
                "payload": {
                    "calculation_conditions": {"k_grid": "24x24x24"},
                    "parameters": {"smearing": {"value_number": 0.02, "unit": "eV"}},
                },
            }],
        }],
    }

    modules = _property_modules_for_state(state)

    record = modules[0]["records"][0]
    assert record["property_code"] == "density_of_states"
    assert record["definition_key"] == "record.electronic_properties.property.density_of_states"
    assert record["payload"] == state["property_modules"][0]["records"][0]["payload"]
    assert modules is not state["property_modules"]


def test_li2mgh16_draft_persists_conditioned_scientific_entity_graph():
    evidence = {
        "section": "Results",
        "page": 3,
        "quote": "Fd-3m Li2MgH16 has lambda=3.35 and Tc=351 K at 300 GPa.",
    }
    draft = {
        "material_states": [{
            "material": "Li2MgH16",
            "pressure_value_gpa": 300,
            "pressure_raw": "300",
            "pressure_unit_raw": "GPa",
            "state_kind": "theoretical",
            "reported_space_group_symbol": "Fd-3m",
            "reported_space_group_number": 227,
            "space_group_evidence": evidence,
            "structure": None,
            "calculation_context": {
                "phonon_nuclear_treatment": "unknown",
                "lambda_ep": 3.35,
                "omega_log_k": None,
                "evidence": evidence,
            },
            "experimental_context": None,
            "tc_results": [{
                "result_kind": "theoretical",
                "tc_method": "unknown",
                "tc_value_k": 351,
                "tc_min_k": None,
                "tc_max_k": None,
                "value_raw": "351",
                "unit_raw": "K",
                "evidence": evidence,
            }],
            "properties": [{
                "name": "density_of_states",
                "name_raw": "H-dominated density of states",
                "value": 2,
                "value_raw": "almost twice that of MgH16",
                "unit": None,
                "evidence": evidence,
            }],
        }],
    }
    session = _RecordingAsyncSession()
    paper = models.Paper(id=17, content_revision=1)

    targets = asyncio.run(persist_scientific_draft(session, paper, draft))

    superconductor = next(item for item in session.added if isinstance(item, models.Superconductor))
    state = next(item for item in session.added if isinstance(item, models.MaterialState))
    records = [item for item in session.added if isinstance(item, models.PropertyRecord)]
    tc_result = next(item for item in records if item.record_type == "predicted_tc")
    general_property = next(item for item in records if item.record_type == "property")

    assert superconductor.composition_key == "H:16|Li:2|Mg:1"
    assert float(state.pressure_value_gpa) == 300
    assert not hasattr(state, "phase_label")
    assert state.reported_space_group_symbol == "Fd-3m"
    assert state.reported_space_group_number == 227
    assert not any(isinstance(item, models.StructureModel) for item in session.added)
    assert float(tc_result.value_number) == 351
    assert tc_result.payload_json["calculation_conditions"] == {
        "phonon_nuclear_treatment": "unknown",
    }
    assert float(tc_result.payload_json["parameters"]["lambda_ep"]["value_number"]) == 3.35
    assert "omega_log_k" not in tc_result.payload_json["parameters"]
    assert general_property.material_state_id == state.id
    assert general_property.property_code == "custom"
    assert {target.kind for target in targets} == {None, "property_record"}
    assert not any(isinstance(item, (
        models.CalculationContext,
        models.TcResult,
        models.SuperconductorProperty,
    )) for item in session.added)


def test_confirmed_structure_candidate_persists_conventional_cif():
    source_text = "data_Cu\n_cell_length_a 3.6\n_cell_length_b 3.6\n_cell_length_c 3.6\n_cell_angle_alpha 90\n_cell_angle_beta 90\n_cell_angle_gamma 90\n_symmetry_space_group_name_H-M 'P 1'\n_symmetry_Int_Tables_number 1\nloop_\n _atom_site_label\n _atom_site_type_symbol\n _atom_site_fract_x\n _atom_site_fract_y\n _atom_site_fract_z\n Cu1 Cu 0 0 0\n"
    candidate = build_structure_candidate(
        structure_format="cif",
        structure_text=source_text,
        source={"file_id": "cif-1", "filename": "Cu.cif", "page": 1, "quote": "attached Cu structure"},
        material_state_ref="material_states[0]",
    )
    candidate["confirmation"] = "confirmed"
    candidate["status"] = "confirmed"
    candidate["validation"]["atom_count"] = 999
    session = _RecordingAsyncSession()
    paper = models.Paper(id=18, content_revision=1)

    targets = asyncio.run(persist_scientific_draft(session, paper, {
        "material_states": [{"material": "Cu", "state_kind": "experimental"}],
        "structure_candidates": [candidate],
    }))

    structure = next(item for item in session.added if isinstance(item, models.StructureModel))
    assert structure.material_state_id
    assert structure.structure_format == "cif"
    assert structure.geometry_method.startswith("pymatgen.") or structure.geometry_method == "identity_fallback"
    assert structure.atom_count == 1
    assert structure.source_locator == "attachment: Cu.cif"
    assert any(target.kind == "structure" and target.entity is structure for target in targets)


def test_tc_level_calculation_conditions_and_parameters_persist_per_record():
    evidence = {
        "section": "Results",
        "page": 5,
        "quote": "Allen-Dynes Tc=24 K with lambda=1.2, omega_log=120 K, mu*=0.13.",
    }
    draft = {
        "material_states": [{
            "material": "MgB2",
            "state_kind": "theoretical",
            "schema_version": 2,
            "property_modules": [{
                "module_key": "superconductive-main",
                "module_code": "superconductive_properties",
                "definition_key": "module.superconductive_properties",
                "definition_version": 1,
                "records": [
                    {
                        "record_key": "tc-allen-dynes",
                        "module_code": "superconductive_properties",
                        "record_type": "predicted_tc",
                        "property_code": "tc",
                        "definition_key": "record.superconductive_properties.predicted_tc.allen_dynes",
                        "definition_version": 1,
                        "name_raw": "Tc",
                        "value_kind": "number",
                        "value_number": 24,
                        "value_raw": "24",
                        "canonical_unit": "K",
                        "method_code": "allen_dynes",
                        "payload": {
                            "calculation_conditions": {},
                            "parameters": {
                                "lambda_ep": {"value_number": 1.2, "unit": "1"},
                                "omega_log_k": {"value_number": 120, "unit": "K"},
                                "mu_star": {"value_number": 0.13, "unit": "1"},
                            },
                        },
                        "evidence": evidence,
                    },
                    {
                        "record_key": "tc-mcmillan",
                        "module_code": "superconductive_properties",
                        "record_type": "predicted_tc",
                        "property_code": "tc",
                        "definition_key": "record.superconductive_properties.predicted_tc.mcmillan",
                        "definition_version": 1,
                        "name_raw": "Tc",
                        "value_kind": "number",
                        "value_number": 21,
                        "value_raw": "21",
                        "canonical_unit": "K",
                        "method_code": "mcmillan",
                        "payload": {
                            "calculation_conditions": {},
                            "parameters": {
                                "lambda_ep": {"value_number": 0.8, "unit": "1"},
                                "mu_star": {"value_number": 0.1, "unit": "1"},
                            },
                        },
                    },
                ],
            }],
        }],
    }
    session = _RecordingAsyncSession()
    paper = models.Paper(id=19, content_revision=1)

    targets = asyncio.run(persist_scientific_draft(session, paper, draft))

    tc_results = [item for item in session.added if isinstance(item, models.PropertyRecord)]
    assert len(tc_results) == 2
    first, second = tc_results
    assert first.payload_json is not second.payload_json
    assert first.payload_json["calculation_conditions"] == {}
    assert second.payload_json["calculation_conditions"] == {}
    assert float(first.payload_json["parameters"]["lambda_ep"]["value_number"]) == 1.2
    assert float(first.payload_json["parameters"]["omega_log_k"]["value_number"]) == 120
    assert float(first.payload_json["parameters"]["mu_star"]["value_number"]) == 0.13
    assert float(second.payload_json["parameters"]["lambda_ep"]["value_number"]) == 0.8
    assert "omega_log_k" not in second.payload_json["parameters"]
    assert float(second.payload_json["parameters"]["mu_star"]["value_number"]) == 0.1
    assert any(target.kind == "property_record" and target.entity is first for target in targets)
    assert not any(isinstance(item, (models.CalculationContext, models.TcResult)) for item in session.added)


def test_theoretical_tc_without_entry_context_copies_shared_state_parameters():
    draft = {
        "material_states": [{
            "material": "LaH10",
            "state_kind": "theoretical",
            "calculation_context": {
                "lambda_ep": 2.5,
                "omega_log_k": 900,
                "mu_star": 0.1,
            },
            "tc_results": [
                {
                    "result_kind": "theoretical",
                    "tc_method": "isotropic_eliashberg",
                    "tc_value_k": 250,
                    "value_raw": "250",
                    "unit_raw": "K",
                },
                {
                    "result_kind": "theoretical",
                    "tc_method": "mcmillan",
                    "tc_value_k": 240,
                    "value_raw": "240",
                    "unit_raw": "K",
                    "calculation_context": {
                        "lambda_ep": None,
                        "omega_log_k": None,
                        "mu_star": None,
                    },
                },
            ],
        }],
    }
    session = _RecordingAsyncSession()
    paper = models.Paper(id=20, content_revision=1)

    asyncio.run(persist_scientific_draft(session, paper, draft))

    tc_results = [item for item in session.added if isinstance(item, models.PropertyRecord)]
    assert len(tc_results) == 2
    assert float(tc_results[0].payload_json["parameters"]["lambda_ep"]["value_number"]) == 2.5
    assert float(tc_results[0].payload_json["parameters"]["omega_log_k"]["value_number"]) == 900
    assert float(tc_results[0].payload_json["parameters"]["mu_star"]["value_number"]) == 0.1
    assert tc_results[0].payload_json is not tc_results[1].payload_json
    assert tc_results[1].payload_json["parameters"] == tc_results[0].payload_json["parameters"]
    assert not any(isinstance(item, (models.CalculationContext, models.TcResult)) for item in session.added)


def test_experimental_tc_never_persists_calculation_context():
    session = _RecordingAsyncSession()
    paper = models.Paper(id=25, content_revision=1)

    asyncio.run(persist_scientific_draft(session, paper, {
        "material_states": [{
            "material": "Pb",
            "tc_results": [{
                "result_kind": "theoretical",
                "tc_method": "experimental",
                "tc_value_k": 7.2,
                "value_raw": "7.2",
                "unit_raw": "K",
                "calculation_context": {"lambda_ep": 1.5, "omega_log_k": 100, "mu_star": 0.1},
            }],
        }],
    }))

    tc_result = next(item for item in session.added if isinstance(item, models.PropertyRecord))
    assert tc_result.method_code == "resistivity"
    assert tc_result.record_type == "measured_tc"
    assert tc_result.payload_json["experimental_conditions"] == {}
    assert "calculation_conditions" not in tc_result.payload_json
    assert not any(isinstance(item, (models.CalculationContext, models.TcResult)) for item in session.added)


def test_draft_element_count_takes_precedence_over_formula_count():
    draft = {
        "paper": {"superconductor_kind": "unconventional"},
        "material_states": [
            {"material": "MgB2", "element_count": 5},
            {"material": "LaH10"},
        ],
    }
    session = _RecordingAsyncSession()
    paper = models.Paper(id=21, content_revision=1)

    asyncio.run(persist_scientific_draft(session, paper, draft))

    states = [item for item in session.added if isinstance(item, models.MaterialState)]
    assert states[0].element_count == 5
    assert states[1].element_count == 2


def test_superconductor_kind_is_not_persisted_on_material_states():
    draft = {
        "paper": {"superconductor_kind": "unconventional"},
        "material_states": [
            {"material": "Cu", "superconductor_kind": "unconventional"},
            {"material": "Fe", "superconductor_kind": "not-a-kind"},
            {"material": "Ni"},
        ],
    }
    session = _RecordingAsyncSession()
    paper = models.Paper(id=22, content_revision=1)

    asyncio.run(persist_scientific_draft(session, paper, draft))

    states = [item for item in session.added if isinstance(item, models.MaterialState)]
    assert paper.superconductor_kind == "unconventional"
    assert all(not hasattr(state, "superconductor_kind") for state in states)


def test_tc_method_code_is_authoritative_and_raw_method_text_is_preserved():
    draft = {
        "material_states": [{
            "material": "MgB2",
            "state_kind": "theoretical",
            "calculation_context": {"lambda_ep": 0.9},
            "tc_results": [
                {
                    "result_kind": "theoretical",
                    "tc_method": "other",
                    "tc_method_custom": "empirical formula fit",
                    "tc_value_k": 30,
                    "value_raw": "30",
                    "unit_raw": "K",
                },
                {
                    "result_kind": "theoretical",
                    "tc_method": "mcmillan",
                    "tc_method_custom": "should be dropped",
                    "tc_value_k": 25,
                    "value_raw": "25",
                    "unit_raw": "K",
                },
            ],
        }],
    }
    session = _RecordingAsyncSession()
    paper = models.Paper(id=23, content_revision=1)

    asyncio.run(persist_scientific_draft(session, paper, draft))

    tc_results = [item for item in session.added if isinstance(item, models.PropertyRecord)]
    assert tc_results[0].method_code == "other"
    assert tc_results[0].method_raw == "empirical formula fit"
    assert tc_results[1].method_code == "mcmillan"
    assert tc_results[1].method_raw == "should be dropped"
    assert not any(isinstance(item, models.TcResult) for item in session.added)


def test_crystal_system_persisted_with_whitelist_fallback():
    draft = {
        "material_states": [
            {"material": "MgB2", "crystal_system": "hexagonal"},
            {"material": "Cu", "crystal_system": "cubiccc"},
            {"material": "Ni"},
        ],
    }
    session = _RecordingAsyncSession()
    paper = models.Paper(id=24, content_revision=1)

    asyncio.run(persist_scientific_draft(session, paper, draft))

    states = [item for item in session.added if isinstance(item, models.MaterialState)]
    assert states[0].crystal_system == "hexagonal"
    assert states[1].crystal_system == "unknown"
    assert states[2].crystal_system == "unknown"
