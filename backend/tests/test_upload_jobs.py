import json
import os

import pytest


os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-upload-jobs-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from backend.ingest.upload_jobs import (
    CHUNK_SYSTEM_PROMPT,
    PUBLIC_CHUNK_RESULT_FIELDS,
    SUMMARY_SYSTEM_PROMPT,
    _chunks_with_preamble,
    _normalize_draft,
)
from backend.api.rag import _property_values, _validate_draft


def test_chunks_keep_first_and_next_page_numbers():
    markdown = """<!-- page: 1 -->
Title and abstract contain enough text to remain as the paper preamble.

## Results
<!-- page: 2 -->
The superconducting transition reaches 203 K under pressure, with enough text for a result chunk.
"""

    chunks = _chunks_with_preamble(markdown)

    assert chunks
    assert chunks[0].source_page == 1
    assert any(chunk.source_page == 2 for chunk in chunks)


def test_normalize_draft_flattens_evidenced_text_lists():
    evidence = {"section": "Methods", "page": 2, "quote": "We solve the equations."}
    draft = _normalize_draft({
        "paper": {
            "paper_type": "theoretical",
            "theoretical_subtype": "method",
            "research_materials": [{"material": "Example2H3", "evidence": evidence}],
            "methodology": [{"method": "Eliashberg equations", "evidence": evidence}],
        },
        "key_properties": [{"material": "Example2H3", "name": "Tc", "value": 42}],
    })

    assert draft["paper"]["research_materials"] == ["Example2H3"]
    assert draft["paper"]["methodology"] == ["Eliashberg equations"]
    assert draft["field_evidence"]["research_materials"] == [evidence]
    assert draft["field_evidence"]["methodology"] == [evidence]
    assert draft["material_states"][0]["tc_results"][0]["value_raw"] == "42"


def test_normalize_draft_preserves_structure_candidates_for_user_confirmation():
    candidate = {
        "candidate_id": "candidate-1",
        "status": "valid",
        "confirmation": "unreviewed",
        "material_state_ref": "unassigned:file-1",
        "representations": {"conventional": {"cif": {"text": "data_test"}}},
    }
    draft = _normalize_draft({"paper": {"paper_type": "review"}, "structure_candidates": [candidate]})

    assert draft["structure_candidates"] == [candidate]


def test_referenced_materials_remain_internal_and_are_removed_from_final_draft():
    evidence = {"section": "Introduction", "page": 1, "quote": "LaH10 was reported previously."}
    draft = _normalize_draft({
        "paper": {
            "paper_type": "theoretical",
            "research_materials": ["Li2MgH16"],
            "referenced_materials": [{"material": "LaH10", "evidence": evidence}],
        },
        "field_evidence": {"referenced_materials": [evidence]},
    })

    assert "referenced_materials" in CHUNK_SYSTEM_PROMPT
    assert "referenced_materials" not in PUBLIC_CHUNK_RESULT_FIELDS
    assert "referenced_materials" not in draft["paper"]
    assert "referenced_materials" not in draft["field_evidence"]


def test_normalize_legacy_li2mgh16_properties_into_scientific_material_state():
    evidence = {
        "section": "Main text",
        "page": 3,
        "quote": "Clathrate structure of Li2MgH16 with the space group Fd-3m at 300 GPa",
    }
    draft = _normalize_draft({
        "paper": {
            "paper_type": "theoretical",
            "theoretical_subtype": "calculation",
            "research_materials": ["Li2MgH16"],
        },
        "key_properties": [
            {
                "material": "Fd-3m-Li2MgH16",
                "name": "superconducting transition temperature",
                "name_raw": "Tc",
                "value": 351,
                "unit": "K",
                "condition": {"pressure": 300, "pressure_unit": "GPa"},
                "article_type": "t",
                "evidence": evidence,
            },
            {
                "material": "Li2MgH16",
                "name": "crystal structure",
                "name_raw": "space group",
                "value": "Fd-3m",
                "condition": {"pressure": 300, "pressure_unit": "GPa"},
                "article_type": "t",
                "evidence": evidence,
            },
            {
                "material": "Li2MgH16",
                "name": "electron-phonon coupling parameter",
                "name_raw": "λ",
                "value": 3.35,
                "condition": {"pressure": {"value": 300, "unit": "GPa"}},
                "article_type": "t",
                "evidence": evidence,
            },
        ],
    })

    assert "key_properties" not in draft
    assert len(draft["material_states"]) == 1
    state = draft["material_states"][0]
    assert state["material"] == "Li2MgH16"
    assert state["pressure_value_gpa"] == 300
    assert state["pressure_raw"] == "300"
    assert state["pressure_unit_raw"] == "GPa"
    assert state["reported_space_group_symbol"] == "Fd-3m"
    assert state["reported_space_group_number"] == 227
    assert state["calculation_context"]["lambda_ep"] == 3.35
    assert state["calculation_context"]["omega_log_k"] is None
    assert state["tc_results"][0]["value_raw"] == "351"
    assert state["tc_results"][0]["tc_value_k"] == 351


def test_property_values_prefer_user_edited_raw_value():
    value_min, value_max, value_raw = _property_values({"value": 42, "value_raw": "50-55"})

    assert (value_min, value_max, value_raw) == (50.0, 55.0, "50-55")


@pytest.mark.parametrize(
    ("paper_type", "subtype"),
    [
        ("theoretical", "calculation"),
        ("theoretical", "method"),
        ("theoretical", "theory"),
        ("experimental", None),
        ("review", None),
    ],
)
def test_normalize_draft_keeps_supported_full_paper_classifications(paper_type, subtype):
    draft = _normalize_draft({
        "paper": {"paper_type": paper_type, "theoretical_subtype": subtype},
        "key_properties": [],
    })
    assert draft["paper"]["paper_type"] == paper_type
    assert draft["paper"]["theoretical_subtype"] == subtype


def test_summary_prompt_defines_mixed_theory_experiment_tie_breaker():
    assert "理论和实验同等重要、无法分主次，也归 experimental" in SUMMARY_SYSTEM_PROMPT
    assert "新算法、新模型、新研究工具归 method" in SUMMARY_SYSTEM_PROMPT
    assert "不能只凭化学式猜测" in SUMMARY_SYSTEM_PROMPT
    assert "reported_space_group_number" in SUMMARY_SYSTEM_PROMPT
    assert "lambda_ep" in SUMMARY_SYSTEM_PROMPT
    assert "omega_log_k" in SUMMARY_SYSTEM_PROMPT
    assert "pressure_value_gpa" in SUMMARY_SYSTEM_PROMPT


def test_chunk_prompt_defines_evidence_scope_without_restricting_material_vocabulary():
    assert "scope" in CHUNK_SYSTEM_PROMPT
    assert "current_paper" in CHUNK_SYSTEM_PROMPT
    assert "referenced_work" in CHUNK_SYSTEM_PROMPT
    assert "材料类型 value 允许自由文本" in CHUNK_SYSTEM_PROMPT


def test_legacy_chunk_cache_is_reread_with_scoped_evidence_contract(tmp_path, monkeypatch):
    from backend.ingest import upload_jobs
    from backend.ingest.chunker import Chunk

    monkeypatch.setattr(upload_jobs, "artifact_directory", lambda _task_id: tmp_path)
    chunk = Chunk(0, 0, "Introduction", None, "content", 2)
    cache = tmp_path / "chunks/00000.json"
    cache.parent.mkdir()
    cache.write_text(json.dumps({
        "paper_type_evidence": [{
            "candidate": "experimental",
            "quote": "Subsequent experimental work found two states.",
        }],
    }), encoding="utf-8")
    calls = []

    def complete_json(_system_prompt, _prompt):
        calls.append(True)
        return {
            "paper_type_evidence": [{
                "candidate": "experimental", "scope": "referenced_work",
                "quote": "Subsequent experimental work found two states.",
            }],
        }

    monkeypatch.setattr(upload_jobs, "complete_json", complete_json)

    result = upload_jobs._read_chunk("e" * 32, chunk)

    assert calls == [True]
    assert result["_schema_version"] == upload_jobs.CHUNK_RESULT_SCHEMA_VERSION
    assert result["paper_type_evidence"][0]["scope"] == "referenced_work"
    assert upload_jobs._read_chunk("e" * 32, chunk) == result
    assert calls == [True]


def test_submission_rejects_unknown_paper_type_but_accepts_custom_material_type():
    draft = _normalize_draft({
        "paper": {
            "title": "Example",
            "paper_type": "experimental",
            "research_materials": ["Example2H3"],
        },
        "sc_type": "new_family",
        "key_properties": [{
            "material": "Example2H3",
            "name": "critical_temperature",
            "value": 42,
            "article_type": "e",
            "superconductor_type": "new_family",
        }],
    })
    _validate_draft(draft)
    draft["paper"]["paper_type"] = "unknown"
    with pytest.raises(Exception) as exc_info:
        _validate_draft(draft)
    assert getattr(exc_info.value, "status_code", None) == 400
