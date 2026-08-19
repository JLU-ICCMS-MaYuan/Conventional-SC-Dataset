import os

import pytest


os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-upload-jobs-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from backend.ingest.upload_jobs import SUMMARY_SYSTEM_PROMPT, _chunks_with_preamble, _normalize_draft
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
    assert draft["key_properties"][0]["value_raw"] == "42"


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
