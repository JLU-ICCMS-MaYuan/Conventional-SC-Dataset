import json
import os

import pytest


os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-upload-jobs-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from backend.ingest.upload_jobs import (
    _build_ai_suggestions,
    CHUNK_SYSTEM_PROMPT,
    PUBLIC_CHUNK_RESULT_FIELDS,
    SUMMARY_SYSTEM_PROMPT,
    _classification_scope_evidence,
    _chunks_with_preamble,
    _normalize_draft,
    _summary_classification_candidates,
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


def test_chinese_ai_suggestions_do_not_replace_english_canonical_draft(monkeypatch):
    canonical = _normalize_draft({
        "paper": {
            "title": "Original English Title",
            "summary": "Lead becomes superconducting near 6 K.",
            "methodology": ["Electrical resistance measurement"],
            "material_families": [{"name": "Elemental superconductors"}],
        },
        "material_states": [{
            "material": "Pb",
            "structure_families": [{"name": "Close-packed metal"}],
            "properties": [{"name": "critical current", "value_raw": "1.2", "unit": "A"}],
        }],
        "classification_evidence": [{"quote": "\u539f\u59cb\u4e2d\u6587\u8bc1\u636e"}],
    })

    def localized_response(_system_prompt, _user_prompt):
        return {
            "paper": {
                "summary": "\u94c5\u5728\u7ea66 K\u65f6\u8fdb\u5165\u8d85\u5bfc\u6001\u3002",
                "methodology": ["\u7535\u963b\u6d4b\u91cf"],
                "material_families": [{"name": "\u5355\u8d28\u8d85\u5bfc\u4f53"}],
            },
            "material_states": [{
                "structure_families": [{"name": "\u5bc6\u5806\u79ef\u91d1\u5c5e"}],
                "properties": [{"name": "\u4e34\u754c\u7535\u6d41"}],
            }],
        }

    monkeypatch.setattr("backend.ingest.upload_jobs.complete_json", localized_response)

    suggestions = _build_ai_suggestions(canonical, "zh")

    assert canonical["paper"]["summary"] == "Lead becomes superconducting near 6 K."
    assert canonical["paper"]["methodology"] == ["Electrical resistance measurement"]
    assert suggestions["paper"]["title"] == "Original English Title"
    assert suggestions["paper"]["summary"] == "\u94c5\u5728\u7ea66 K\u65f6\u8fdb\u5165\u8d85\u5bfc\u6001\u3002"
    assert suggestions["paper"]["methodology"] == ["\u7535\u963b\u6d4b\u91cf"]
    assert suggestions["material_states"][0]["material"] == "Pb"
    assert suggestions["material_states"][0]["structure_families"][0]["name"] == "\u5bc6\u5806\u79ef\u91d1\u5c5e"
    assert suggestions["classification_evidence"][0]["quote"] == "\u539f\u59cb\u4e2d\u6587\u8bc1\u636e"
    assert _build_ai_suggestions(canonical, "en")["paper"]["methodology"] == [
        "Electrical resistance measurement",
    ]


def test_llm_draft_cannot_supply_citation_extraction():
    raw = {
        "paper": {"paper_type": "review"},
        "citation_extraction": {
            "status": "succeeded",
            "references": [{"raw_citation": "forged citation"}],
        },
    }

    worker_draft = _normalize_draft(raw, preserve_citation_extraction=False)
    stored_draft = _normalize_draft(raw)

    assert worker_draft["citation_extraction"] is None
    assert stored_draft["citation_extraction"]["references"][0]["raw_citation"] == "forged citation"


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


def test_normalize_draft_drops_phase_label_without_migrating_it_to_space_group():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical", "research_materials": ["Li2MgH16"]},
        "material_states": [{
            "material": "Li2MgH16",
            "phase_label": "clathrate",
            "reported_space_group_symbol": None,
            "reported_space_group_number": None,
            "state_kind": "theoretical",
        }],
    })

    state = draft["material_states"][0]
    assert "phase_label" not in state
    assert state["reported_space_group_symbol"] is None
    assert state["reported_space_group_number"] is None


def test_referenced_materials_remain_internal_and_are_removed_from_final_draft():
    evidence = {"section": "Introduction", "page": 1, "quote": "LaH10 was reported previously."}
    draft = _normalize_draft({
        "paper": {
            "paper_type": "theoretical",
            "research_materials": ["Li2MgH16"],
            "referenced_materials": [{"material": "LaH10", "evidence": evidence}],
        },
        "field_evidence": {"referenced_materials": [evidence]},
        "material_states": [
            {"material": "Li2MgH16", "scope": "current_paper"},
            {"material": "LaH10", "scope": "referenced_work"},
        ],
    })

    assert "referenced_materials" in CHUNK_SYSTEM_PROMPT
    assert "referenced_materials" not in PUBLIC_CHUNK_RESULT_FIELDS
    assert "referenced_materials" not in draft["paper"]
    assert "referenced_materials" not in draft["field_evidence"]
    assert [state["material"] for state in draft["material_states"]] == ["Li2MgH16"]
    assert "scope" not in draft["material_states"][0]


def test_referenced_classification_candidates_are_internal_only():
    candidates = [{
        "_source": {"file_id": "main", "section": "Results", "page_start": 3, "page_end": 3},
        "material_states": [{
            "material": "Li2MgH16",
            "scope": "current_paper",
            "material_family": {
                "name": "氢基超导体", "scope": "referenced_work", "page": 1,
                "quote": "LaH10 is a known hydride superconductor.",
            },
            "structure_families": [
                {"name": "笼状结构", "scope": "current_paper", "page": 3, "quote": "We find a clathrate."},
                {"name": "层状结构", "scope": "referenced_work", "page": 1, "quote": "Previous layered phases."},
            ],
        }, {
            "material": "LaH10", "scope": "referenced_work", "page": 1,
            "quote": "LaH10 was reported previously.",
        }],
    }]

    summarized = _summary_classification_candidates(candidates)
    assert [state["material"] for state in summarized[0]["material_states"]] == ["Li2MgH16"]
    # 分块候选阶段仍可保留状态级证据，最终草稿归一化时才提升到论文级。
    assert summarized[0]["material_states"][0]["material_family"] is None
    assert [item["name"] for item in summarized[0]["material_states"][0]["structure_families"]] == ["笼状结构"]

    evidence = _classification_scope_evidence(candidates)
    assert {(item["raw_name"], item["scope"]) for item in evidence} == {
        ("Li2MgH16", "current_paper"),
        ("氢基超导体", "referenced_work"),
        ("笼状结构", "current_paper"),
        ("层状结构", "referenced_work"),
        ("LaH10", "referenced_work"),
    }
    referenced = next(item for item in evidence if item["raw_name"] == "LaH10")
    assert referenced["page_start"] == 1
    assert referenced["quote"] == "LaH10 was reported previously."


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
    assert "phase_label" not in SUMMARY_SYSTEM_PROMPT


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


def test_submission_rejects_unknown_paper_type_but_accepts_pending_material_family():
    draft = _normalize_draft({
        "paper": {
            "title": "Example",
            "year": 2024,
            "paper_type": "experimental",
            "research_materials": ["Example2H3"],
            "material_families": [
                {"id": None, "name": "new_family", "status": "pending"}
            ],
        },
        "material_states": [{
            "material": "Example2H3",
            "tc_results": [{"tc_value_k": 42, "result_kind": "experimental"}],
        }],
    })
    _validate_draft(draft)
    draft["paper"]["paper_type"] = "unknown"
    with pytest.raises(Exception) as exc_info:
        _validate_draft(draft)
    assert getattr(exc_info.value, "status_code", None) == 400


def test_submission_requires_paper_year():
    draft = _normalize_draft({
        "paper": {
            "title": "Example",
            "paper_type": "review",
            "material_families": [
                {"id": None, "name": "new_family", "status": "pending"}
            ],
        },
        "material_states": [],
    })

    with pytest.raises(Exception) as exc_info:
        _validate_draft(draft)

    assert getattr(exc_info.value, "status_code", None) == 400
    assert getattr(exc_info.value, "detail", {}).get("code") == "year_required"


def test_parse_partial_draft_accepts_complete_json():
    from backend.ingest.upload_jobs import _parse_partial_draft

    draft = _parse_partial_draft('{"paper": {"title": "T"}, "material_states": []}')

    assert draft == {"paper": {"title": "T"}, "material_states": []}


def test_parse_partial_draft_drops_llm_citation_extraction():
    from backend.ingest.upload_jobs import _parse_partial_draft

    draft = _parse_partial_draft(
        '{"paper": {"title": "T"}, "citation_extraction": {"status": "succeeded"}}',
    )

    assert draft is not None
    assert "citation_extraction" not in draft


def test_parse_partial_draft_repairs_truncated_array_and_string():
    from backend.ingest.upload_jobs import _parse_partial_draft

    truncated = '{"paper": {"title": "Potential high-Tc", "authors": ["Hanyu Liu", "Ivan I. Nau'
    draft = _parse_partial_draft(truncated)
    assert draft is not None
    assert draft["paper"]["title"] == "Potential high-Tc"
    assert draft["paper"]["authors"] == ["Hanyu Liu"]

    mid_value = '{"paper": {"title": "Potential hig'
    draft = _parse_partial_draft(mid_value)
    assert draft is not None
    assert draft["paper"] == {}


def test_parse_partial_draft_rejects_non_draft_text():
    from backend.ingest.upload_jobs import _parse_partial_draft

    assert _parse_partial_draft("") is None
    assert _parse_partial_draft("no json here") is None
    assert _parse_partial_draft('{"unrelated": 1}') is None


def test_build_candidate_draft_merges_first_candidates():
    from backend.ingest.upload_jobs import _build_candidate_draft

    chunks = [
        {
            "result": {
                "metadata": {"title": "T1", "doi": "10.1/a", "authors": ["A", "B"], "journal": "J"},
                "paper_type_evidence": [
                    {"candidate": "experimental", "scope": "current_paper", "quote": "q"},
                ],
                "methodology": [{"value": "CALYPSO"}, {"value": "CALYPSO"}, {"value": "DFT"}],
                "key_findings": [{"value": "203 K"}],
                "material_states": [
                    {
                        "material": "LaH10", "scope": "current_paper",
                        "material_family": {"name": "hydride", "scope": "current_paper"},
                        "structure_families": [{"name": "fcc", "is_primary": True, "scope": "current_paper"}],
                        "evidence": {"page": 1, "quote": "x"},
                    },
                    {"material": "Referenced", "scope": "referenced_work"},
                ],
            },
        },
        {
            "result": {
                "metadata": {"title": "T1-other", "authors": ["A", "C"]},
                "research_materials": [{"value": "LaH10"}],
            },
        },
        {"result": None},
    ]

    draft = _build_candidate_draft(chunks)

    assert draft["paper"]["title"] == "T1"
    assert draft["paper"]["doi"] == "10.1/a"
    assert draft["paper"]["authors"] == ["A", "B", "C"]
    assert draft["paper"]["paper_type"] == "experimental"
    assert draft["paper"]["methodology"] == ["CALYPSO", "DFT"]
    assert draft["paper"]["key_finding"] == "203 K"
    assert draft["paper"]["research_materials"] == ["LaH10"]
    assert len(draft["material_states"]) == 1
    state = draft["material_states"][0]
    assert state["material"] == "LaH10"
    assert draft["paper"]["material_families"] == [
        {"id": None, "name": "hydride", "status": "pending"}
    ]
    assert "material_family" not in state
    assert state["structure_families"][0]["name"] == "fcc"
    assert "evidence" not in state and "scope" not in state


def test_element_count_locked_value_is_not_recomputed():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{
            "material": "LaH10",
            "element_count": 5,
            "element_count_locked": True,
        }],
    })

    state = draft["material_states"][0]
    assert state["element_count"] == 5
    assert state["element_count_locked"] is True


def test_element_count_recomputed_from_formula_when_not_locked():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{"material": "LaH10"}],
    })

    assert draft["material_states"][0]["element_count"] == 2


def test_element_count_loose_fallback_handles_variable_formula():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{"material": "LaHx (x = 1–12) 150 GPa"}],
    })

    assert draft["material_states"][0]["element_count"] == 2


def test_element_count_preserves_ai_value_when_formula_unparseable():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{"material": "!!!", "element_count": 4}],
    })

    assert draft["material_states"][0]["element_count"] == 4


def test_space_group_number_looks_up_full_spglib_table():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{"material": "LaH10", "reported_space_group_symbol": "Fm-3m"}],
    })

    assert draft["material_states"][0]["reported_space_group_number"] == 225


def test_space_group_number_stays_none_for_non_standard_symbol():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{"material": "LaH10", "reported_space_group_symbol": "clathrate-I"}],
    })

    assert draft["material_states"][0]["reported_space_group_number"] is None


def test_legacy_state_superconductor_kind_is_promoted_to_paper_and_removed_from_states():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [
            {"material": "LaH10", "superconductor_kind": "常规"},
            {"material": "MgB2", "superconductor_kind": "metallic"},
        ],
    })

    assert draft["paper"]["superconductor_kind"] == "conventional"
    assert all("superconductor_kind" not in state for state in draft["material_states"])


def test_legacy_conflicting_state_superconductor_kinds_become_unknown():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [
            {"material": "LaH10", "superconductor_kind": "conventional"},
            {"material": "YBa2Cu3O7", "superconductor_kind": "unconventional"},
        ],
    })

    assert draft["paper"]["superconductor_kind"] == "unknown"


def test_tc_method_free_text_becomes_other_with_custom_value():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{
            "material": "LaH10",
            "tc_results": [
                {"tc_value_k": 250, "tc_method": "Allen-Dynes"},
                {"tc_value_k": 260, "tc_method": "mcmillan"},
            ],
        }],
    })

    results = draft["material_states"][0]["tc_results"]
    assert results[0]["tc_method"] == "other"
    assert results[0]["tc_method_custom"] == "Allen-Dynes"
    assert results[1]["tc_method"] == "mcmillan"
    assert results[1]["tc_method_custom"] is None


def test_tc_result_calculation_context_is_numeric_normalized():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{
            "material": "LaH10",
            "tc_results": [{
                "tc_value_k": 250,
                "tc_method": "mcmillan",
                "calculation_context": {"lambda_ep": "1.2", "omega_log_k": "850", "mu_star": "0.1"},
            }],
        }],
    })

    context = draft["material_states"][0]["tc_results"][0]["calculation_context"]
    assert context["lambda_ep"] == 1.2
    assert context["omega_log_k"] == 850.0
    assert context["mu_star"] == 0.1


def test_crystal_system_whitelists_values_and_maps_chinese_aliases():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [
            {"material": "LaH10", "crystal_system": "perovskite"},
            {"material": "MgB2", "crystal_system": "立方"},
        ],
    })

    assert draft["material_states"][0]["crystal_system"] == "unknown"
    assert draft["material_states"][1]["crystal_system"] == "cubic"


def test_crystal_system_is_overridden_by_authoritative_space_group_number():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{
            "material": "LaH10",
            "crystal_system": "cubic",
            "reported_space_group_number": 139,
        }],
    })

    assert draft["material_states"][0]["crystal_system"] == "tetragonal"


def test_crystal_system_keeps_ai_value_when_space_group_number_missing():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical"},
        "material_states": [{"material": "LaH10", "crystal_system": "Hexagonal"}],
    })

    assert draft["material_states"][0]["crystal_system"] == "hexagonal"


def test_methodology_inference_mcmillan_marks_conventional_and_fills_tc_method():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical", "methodology": ["McMillan equation"]},
        "material_states": [{
            "material": "LaH10",
            "superconductor_kind": "unknown",
            "tc_results": [{"tc_value_k": 250, "result_kind": "theoretical", "tc_method": "unknown"}],
        }],
    })

    assert draft["paper"]["superconductor_kind"] == "conventional"
    state = draft["material_states"][0]
    assert state["tc_results"][0]["tc_method"] == "mcmillan"


def test_methodology_inference_multiple_methods_keep_tc_method_unknown():
    draft = _normalize_draft({
        "paper": {
            "paper_type": "theoretical",
            "methodology": ["McMillan equation", "numerical solution of the Eliashberg equations"],
        },
        "material_states": [{
            "material": "LaH10",
            "tc_results": [{"tc_value_k": 250, "result_kind": "theoretical"}],
        }],
    })

    assert draft["paper"]["superconductor_kind"] == "conventional"
    state = draft["material_states"][0]
    assert state["tc_results"][0]["tc_method"] == "unknown"


def test_methodology_inference_ignores_non_discriminative_text():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical", "methodology": ["superconductivity calculations"]},
        "material_states": [{
            "material": "LaH10",
            "tc_results": [{"tc_value_k": 250, "result_kind": "theoretical"}],
        }],
    })

    assert draft["paper"]["superconductor_kind"] == "unknown"
    state = draft["material_states"][0]
    assert state["tc_results"][0]["tc_method"] == "unknown"


def test_methodology_inference_does_not_override_unconventional():
    draft = _normalize_draft({
        "paper": {"paper_type": "experimental", "methodology": ["McMillan equation"]},
        "material_states": [{
            "material": "YBa2Cu3O7",
            "superconductor_kind": "unconventional",
        }],
    })

    assert draft["paper"]["superconductor_kind"] == "unconventional"


def test_methodology_inference_leaves_experimental_tc_untouched():
    draft = _normalize_draft({
        "paper": {"paper_type": "experimental", "methodology": ["McMillan equation"]},
        "material_states": [{
            "material": "YBa2Cu3O7",
            "tc_results": [{"tc_value_k": 92, "result_kind": "experimental"}],
        }],
    })

    assert draft["material_states"][0]["tc_results"][0]["tc_method"] == "experimental"


def test_methodology_inference_allen_dynes_wins_over_mcmillan():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical", "methodology": ["Allen-Dynes modified McMillan"]},
        "material_states": [{
            "material": "LaH10",
            "tc_results": [{"tc_value_k": 250, "result_kind": "theoretical"}],
        }],
    })

    assert draft["paper"]["superconductor_kind"] == "conventional"
    state = draft["material_states"][0]
    assert state["tc_results"][0]["tc_method"] == "allen_dynes"


def test_methodology_inference_never_creates_tc_results():
    draft = _normalize_draft({
        "paper": {"paper_type": "theoretical", "methodology": ["McMillan equation"]},
        "material_states": [{"material": "LaH10"}],
    })

    assert draft["paper"]["superconductor_kind"] == "conventional"
    state = draft["material_states"][0]
    assert state["tc_results"] == []


# --- Issue #58：分段对解析噪声的鲁棒性（超长 ## 行判为正文而非章节标题） ---

# 实测真实标题上界 204 字符、被误判正文下界 389 字符，阈值 300 落在两者之间。
# 被误判段落的文字原先只存在于 section_name（_split_by_h2 不把标题行放进 body），
# 截断会永久丢失该文字，故改为归入正文。
_MISDETECTED_HEADING = (
    "34 show that transition-metal hydrides are extremely promising. Thus, we decided "
    "to perform a systematic evolutionary search for new phases in the Th-H system "
    "under pressure. As we show below, one of the new hydrides is predicted to be a "
    "unique high-temperature superconductor. " + "Additional discussion text. " * 40
)


def test_overlong_h2_line_becomes_body_text_and_inherits_section_name():
    from backend.ingest.chunker import chunk_paper

    assert len(_MISDETECTED_HEADING) > 300
    markdown = f"""## RESULTS
The pressure-composition phase diagram was explored with enough text to form a chunk.

## {_MISDETECTED_HEADING}
To determine the stability field of the predicted phases we performed extra calculations.
"""

    chunks = chunk_paper(markdown, paper_id=1)

    probe = "transition-metal hydrides are extremely promising"
    assert any(probe in chunk.content for chunk in chunks), "被误判的正文必须进入 content"
    assert not any(probe in (chunk.section_name or "") for chunk in chunks), \
        "被误判的正文不得作为 section_name"
    assert all((chunk.section_name or "") == "RESULTS" for chunk in chunks), \
        "超长行后的内容应沿用前一个真实章节名"


def test_real_h2_headings_still_become_section_names():
    from backend.ingest.chunker import chunk_paper

    # 实测真实标题范围 65–204 字符
    long_real = "KEYWORDS: High-T superconductivity, ThH10, USPEX, DFT, Eliashberg theory, hydrides"
    assert 65 <= len(long_real) <= 204
    # 每节正文需超过 50 tokens，否则会被既有 _merge_small_chunks 并入前一节
    markdown = f"""## RESULTS
{"The pressure-composition phase diagram was explored in detail. " * 6}

## {long_real}
{"Keyword section body text preserved as its own chunk. " * 6}
"""

    chunks = chunk_paper(markdown, paper_id=1)

    names = {chunk.section_name for chunk in chunks}
    assert "RESULTS" in names
    assert long_real in names, "真实标题必须仍作为 section_name"


def test_markdown_without_h2_headings_falls_back_to_whole_text():
    from backend.ingest.chunker import chunk_paper

    markdown = "Plain body text with no second level headings but long enough to keep."

    chunks = chunk_paper(markdown, paper_id=1)

    assert chunks
    assert all((chunk.section_name or "") == "全文" for chunk in chunks)


def test_all_overlong_h2_lines_still_produce_chunks():
    from backend.ingest.chunker import chunk_paper

    markdown = f"""## {_MISDETECTED_HEADING}

## {_MISDETECTED_HEADING}
"""

    chunks = chunk_paper(markdown, paper_id=1)

    assert chunks, "全部 ## 行都被判为正文时不得产出零块"
    probe = "transition-metal hydrides are extremely promising"
    assert any(probe in chunk.content for chunk in chunks)


def test_overlong_h2_before_any_real_section_uses_whole_text_name():
    from backend.ingest.chunker import chunk_paper

    markdown = f"""## {_MISDETECTED_HEADING}
Body text following the misdetected paragraph with enough characters to survive.

## RESULTS
Real results section body text long enough to be kept as a chunk.
"""

    chunks = chunk_paper(markdown, paper_id=1)

    probe = "transition-metal hydrides are extremely promising"
    holder = next(chunk for chunk in chunks if probe in chunk.content)
    assert holder.section_name == "全文", "首个真实章节之前的误判段落归入「全文」"


def test_fit_column_truncates_to_storage_limit():
    from backend.api.rag import _fit_column

    assert _fit_column(None, 500) is None
    assert _fit_column("short", 500) == "short"
    assert _fit_column("x" * 500, 500) == "x" * 500
    long_value = "y" * 1389
    assert len(_fit_column(long_value, 500)) == 500
