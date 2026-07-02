"""Tests for inspiration.reviewer — REVIEW marker parsing."""
from backend.rag.rag.inspiration.reviewer import parse_review_verdicts


class TestParseReviewVerdicts:
    def test_single_review(self):
        text = """<!--REVIEW
{
  "flaws": [{"severity": "high", "description": "缺少稳定性论证"}],
  "feasibility_score": 3,
  "revised_idea": "修正后",
  "dimensions": {"theory": 4, "synthesis": 2, "measurement": 3}
}
-->"""
        verdicts = parse_review_verdicts(text)
        assert len(verdicts) == 1
        assert verdicts[0]["feasibility_score"] == 3
        assert len(verdicts[0]["flaws"]) == 1

    def test_multiple_reviews(self):
        text = """<!--REVIEW
{"flaws": [], "feasibility_score": 4, "revised_idea": "A", "dimensions": {"theory": 4, "synthesis": 4, "measurement": 4}}
-->
文本
<!--REVIEW
{"flaws": [], "feasibility_score": 2, "revised_idea": "B", "dimensions": {"theory": 2, "synthesis": 2, "measurement": 2}}
-->"""
        verdicts = parse_review_verdicts(text)
        assert len(verdicts) == 2
        assert verdicts[0]["feasibility_score"] == 4
        assert verdicts[1]["feasibility_score"] == 2

    def test_no_reviews(self):
        text = "纯文本。"
        verdicts = parse_review_verdicts(text)
        assert verdicts == []

    def test_malformed_skipped(self):
        text = """<!--REVIEW
{broken
-->
<!--REVIEW
{"flaws": [], "feasibility_score": 5, "revised_idea": "ok", "dimensions": {"theory": 5, "synthesis": 5, "measurement": 5}}
-->"""
        verdicts = parse_review_verdicts(text)
        assert len(verdicts) == 1
        assert verdicts[0]["feasibility_score"] == 5
