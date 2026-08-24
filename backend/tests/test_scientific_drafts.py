import asyncio
import os


os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-scientific-drafts-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from backend import models
from backend.ingest.scientific_drafts import persist_scientific_draft
from backend.services.structure_candidates import build_structure_candidate


class _EmptyResult:
    def scalar_one_or_none(self):
        return None


class _RecordingAsyncSession:
    def __init__(self):
        self.added = []
        self._next_id = 1

    async def execute(self, _statement):
        return _EmptyResult()

    def add(self, entity):
        if getattr(entity, "id", None) is None and hasattr(entity, "id"):
            entity.id = self._next_id
            self._next_id += 1
        self.added.append(entity)

    async def flush(self):
        return None


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
    calculation = next(item for item in session.added if isinstance(item, models.CalculationContext))
    tc_result = next(item for item in session.added if isinstance(item, models.TcResult))
    general_property = next(item for item in session.added if isinstance(item, models.SuperconductorProperty))

    assert superconductor.composition_key == "H:16|Li:2|Mg:1"
    assert float(state.pressure_value_gpa) == 300
    assert not hasattr(state, "phase_label")
    assert state.reported_space_group_symbol == "Fd-3m"
    assert state.reported_space_group_number == 227
    assert not any(isinstance(item, models.StructureModel) for item in session.added)
    assert float(calculation.lambda_ep) == 3.35
    assert calculation.omega_log_k is None
    assert calculation.missing_structure_reason
    assert float(tc_result.tc_value_k) == 351
    assert tc_result.calculation_context_id == calculation.id
    assert general_property.material_state_id == state.id
    assert {target.kind for target in targets} == {None, "tc", "property"}


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
