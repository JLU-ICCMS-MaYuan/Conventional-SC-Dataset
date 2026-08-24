import os


os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-author-roles-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from backend.ingest.upload_jobs import CHUNK_SYSTEM_PROMPT, SUMMARY_SYSTEM_PROMPT, _normalize_draft


def test_normalize_draft_preserves_valid_author_roles_in_author_order():
    draft = _normalize_draft({
        "paper": {
            "authors": ["Ying Sun", "Jian Lv", "Hanyu Liu"],
            "corresponding_authors": ["hanyu liu", "Unknown Author"],
            "co_first_authors": ["Jian Lv", "Ying Sun"],
            "paper_type": "review",
        },
    })

    assert draft["paper"]["corresponding_authors"] == ["Hanyu Liu"]
    assert draft["paper"]["co_first_authors"] == ["Ying Sun", "Jian Lv"]


def test_author_role_prompts_require_explicit_contribution_evidence():
    assert "corresponding_authors" in CHUNK_SYSTEM_PROMPT
    assert "co_first_authors" in SUMMARY_SYSTEM_PROMPT
    assert "不得按作者顺序猜测" in CHUNK_SYSTEM_PROMPT
    assert "不能根据作者顺序猜测" in SUMMARY_SYSTEM_PROMPT
