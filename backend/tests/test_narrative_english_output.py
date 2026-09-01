from backend.ingest.extractor import SYSTEM_PROMPT
from backend.ingest.upload_jobs import SUMMARY_SYSTEM_PROMPT
from backend.ingest.upload_jobs import _normalize_draft


def test_summary_prompt_requires_all_narrative_fields_in_english():
    for field in (
        "summary",
        "keywords_tags",
        "methodology",
        "key_finding",
        "research_motivation",
        "knowledge_graph_title",
    ):
        assert field in SUMMARY_SYSTEM_PROMPT
    assert "必须使用英文输出" in SUMMARY_SYSTEM_PROMPT
    assert "10-15 个英文词" in SUMMARY_SYSTEM_PROMPT


def test_prompts_forbid_unsupported_narrative_content():
    assert "缺少原文依据时返回空字符串或空数组" in SUMMARY_SYSTEM_PROMPT
    assert "不得编造" in SUMMARY_SYSTEM_PROMPT
    assert "100-200 words in English" in SYSTEM_PROMPT
    assert "5-10 English keywords" in SYSTEM_PROMPT


def test_normalized_draft_preserves_knowledge_graph_title():
    title = "First Discovery of Superconductivity in Mercury"
    draft = _normalize_draft({"paper": {"knowledge_graph_title": title}})
    assert draft["paper"]["knowledge_graph_title"] == title
