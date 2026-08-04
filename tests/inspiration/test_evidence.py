"""Tests for inspiration.evidence — IDEA_CARD marker parsing."""
from backend.rag.rag.inspiration.evidence import parse_idea_cards


class TestParseIdeaCards:
    def test_single_card(self):
        text = """一些对话文本。
<!--IDEA_CARD
{
  "title": "LaH4 的理论与实验缺口",
  "fragments": [{"paper_id": 74, "quoted_text": "原文", "section": "discussion"}],
  "reasoning_chain": "因为X所以Y",
  "assumptions": ["压力 200 GPa"]
}
-->
后续对话。"""
        cards = parse_idea_cards(text)
        assert len(cards) == 1
        assert cards[0]["title"] == "LaH4 的理论与实验缺口"
        assert len(cards[0]["fragments"]) == 1
        assert cards[0]["fragments"][0]["paper_id"] == 74

    def test_multiple_cards(self):
        text = """<!--IDEA_CARD
{"title": "点子1", "fragments": [], "reasoning_chain": "R1", "assumptions": []}
-->
中间文本
<!--IDEA_CARD
{"title": "点子2", "fragments": [], "reasoning_chain": "R2", "assumptions": []}
-->"""
        cards = parse_idea_cards(text)
        assert len(cards) == 2
        assert cards[0]["title"] == "点子1"
        assert cards[1]["title"] == "点子2"

    def test_no_cards(self):
        text = "纯文本，没有 marker。"
        cards = parse_idea_cards(text)
        assert cards == []

    def test_malformed_card_skipped(self):
        text = """<!--IDEA_CARD
{invalid json
-->
<!--IDEA_CARD
{"title": "valid", "fragments": [], "reasoning_chain": "R", "assumptions": []}
-->"""
        cards = parse_idea_cards(text)
        assert len(cards) == 1
        assert cards[0]["title"] == "valid"
