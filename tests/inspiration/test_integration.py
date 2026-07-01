"""Integration tests for inspiration pipeline — marker pipeline + session lifecycle."""
import json
import pytest
from backend.rag.rag.inspiration.session import InspirationSession
from backend.rag.rag.inspiration.mode_router import parse_mode_result
from backend.rag.rag.inspiration.evidence import parse_idea_cards
from backend.rag.rag.inspiration.reviewer import parse_review_verdicts


class TestFullMarkerPipeline:
    """Test complete marker parsing pipeline — no LLM dependencies."""

    def test_evidence_then_review_markers(self):
        evidence_text = """基于数据库分析，我发现两个方向：

## 方向一：LaH4 的理论预测与实验缺失
<!--IDEA_CARD
{
  "title": "LaH4 稳定相的理论预测与实验验证缺口",
  "fragments": [{"paper_id": 74, "quoted_text": "LaH4 has been predicted...", "section": "conclusion"}],
  "reasoning_chain": "理论预测 LaH4 在 >100 GPa 下稳定但缺乏实验验证 → 可设计 DAC 实验",
  "assumptions": ["LaH4 在 100-200 GPa 可合成"]
}
-->
## 方向二：Be掺杂的笼状氢化物
<!--IDEA_CARD
{
  "title": "Be 掺杂对笼状氢化物 Tc 的影响",
  "fragments": [{"paper_id": 120, "quoted_text": "Be doping may enhance...", "section": "discussion"}],
  "reasoning_chain": "Be 的电负性可能调节电子态密度 → 探索 La-Be-H 三元体系",
  "assumptions": ["Be 可以部分替代 La"]
}
-->"""

        review_text = """审稿意见：

**方向一审核：**
<!--REVIEW
{
  "flaws": [{"severity": "medium", "description": "未给出具体合成压力窗口"}],
  "feasibility_score": 4,
  "revised_idea": "在 100-200 GPa 用 DAC + 激光加热合成 LaH4...",
  "dimensions": {"theory": 5, "synthesis": 3, "measurement": 4}
}
-->

**方向二审核：**
<!--REVIEW
{
  "flaws": [{"severity": "high", "description": "Be 的毒性需要特别防护"}, {"severity": "medium", "description": "未讨论 Be 与 H 的优先反应"}],
  "feasibility_score": 2,
  "revised_idea": "...",
  "dimensions": {"theory": 3, "synthesis": 1, "measurement": 3}
}
-->"""

        cards = parse_idea_cards(evidence_text)
        verdicts = parse_review_verdicts(review_text)

        assert len(cards) == 2
        assert cards[0]["title"].startswith("LaH4")
        assert len(verdicts) == 2
        assert verdicts[0]["feasibility_score"] == 4
        assert verdicts[1]["feasibility_score"] == 2
        assert len(verdicts[1]["flaws"]) == 2


class TestSessionLifecycle:
    """Test session lifecycle."""

    def test_full_session_flow(self):
        s = InspirationSession(user_question="La-H 体系还有什么方向？")
        s.current_mode = "gap_detector"
        s.mode_history.append("gap_detector")

        # Add ideas as dicts (production pattern)
        s.add_idea({"title": "点子1", "fragments": []})
        s.add_idea({"title": "点子2", "fragments": []})
        assert len(s.collected_ideas) == 2

        # Serialize
        d = s.to_dict()
        assert d["current_mode"] == "gap_detector"
        assert len(d["collected_ideas"]) == 2

        # JSON round-trip
        json_str = json.dumps(d, ensure_ascii=False)
        loaded = json.loads(json_str)
        restored = InspirationSession.from_dict(loaded)
        assert restored.session_id == s.session_id
        assert len(restored.collected_ideas) == 2
        assert restored.collected_ideas[0]["title"] == "点子1"

    def test_mode_switch(self):
        s = InspirationSession(user_question="测试")
        s.current_mode = "gap_detector"
        s.mode_history.append("gap_detector")

        # User switches mode
        s.current_mode = "composition_walker"
        s.mode_history.append("composition_walker")

        assert len(s.mode_history) == 2
        assert s.current_mode == "composition_walker"


class TestModeRouterFallback:
    def test_parse_invalid_json_returns_default(self):
        result = parse_mode_result("not json")
        assert result.primary_mode == "gap_detector"

    def test_parse_empty_primary_mode(self):
        response = json.dumps({
            "primary_mode": "",
            "secondary_modes": [],
            "confidence": 0,
            "search_queries": [],
            "rationale": "",
        })
        result = parse_mode_result(response)
        assert result.primary_mode == ""  # preserved as-is


class TestEndToEndDictFlow:
    """Test the dict-based data flow pattern used in production."""

    def test_parse_then_add_then_serialize(self):
        # Step 1: EvidenceBuilder produces text with markers
        evidence_text = """<!--IDEA_CARD
{"title": "test idea", "fragments": [{"paper_id": 1, "quoted_text": "...", "section": "results"}], "reasoning_chain": "R", "assumptions": ["A1"]}
-->"""
        cards = parse_idea_cards(evidence_text)
        assert len(cards) == 1

        # Step 2: Cards are added to session (as dicts)
        s = InspirationSession(user_question="test")
        s.current_mode = "gap_detector"
        for card in cards:
            s.add_idea(card)

        # Step 3: Session is serialized for <!--IS:--> marker
        d = s.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        assert "test idea" in json_str

        # Step 4: Session is restored from marker
        restored = InspirationSession.from_dict(json.loads(json_str))
        assert len(restored.collected_ideas) == 1
        assert restored.collected_ideas[0]["title"] == "test idea"
