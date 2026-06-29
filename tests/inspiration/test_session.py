"""Tests for inspiration.session data classes."""
import json
import pytest
from backend.rag.rag.inspiration.session import (
    InspirationSession,
    IdeaCard,
    EvidenceFragment,
    FeasibilityScore,
    ModeResult,
    ReviewVerdict,
)

class TestInspirationSession:
    def test_create_default(self):
        s = InspirationSession(user_question="有什么新方向？")
        assert s.session_id is not None
        assert len(s.session_id) == 32  # uuid4 hex (without dashes)
        assert s.user_question == "有什么新方向？"
        assert s.history == []
        assert s.current_mode is None
        assert s.collected_ideas == []
        assert s.mode_history == []

    def test_to_dict_and_from_dict(self):
        s = InspirationSession(
            user_question="测试",
            current_mode="gap_detector",
            mode_history=["gap_detector"],
        )
        d = s.to_dict()
        restored = InspirationSession.from_dict(d)
        assert restored.session_id == s.session_id
        assert restored.user_question == s.user_question
        assert restored.current_mode == "gap_detector"
        assert restored.mode_history == ["gap_detector"]

    def test_check_exit(self):
        s = InspirationSession(user_question="测试")
        assert s.check_exit("退出") is True
        assert s.check_exit("不用探索了") is True
        assert s.check_exit("继续分析") is False

    def test_serialize_with_ideas(self):
        card = IdeaCard(
            title="测试点子",
            fragments=[EvidenceFragment(paper_id=74, quoted_text="原文...", section="discussion")],
            reasoning_chain="因为...所以...",
            assumptions=["假设1"],
            feasibility=FeasibilityScore(overall=4, theory=5, synthesis=3, measurement=4),
        )
        s = InspirationSession(user_question="测试", collected_ideas=[card])
        d = s.to_dict()
        assert len(d["collected_ideas"]) == 1
        restored = InspirationSession.from_dict(d)
        assert restored.collected_ideas[0].title == "测试点子"
        assert restored.collected_ideas[0].fragments[0].paper_id == 74
        assert restored.collected_ideas[0].feasibility.overall == 4


class TestIdeaCard:
    def test_create_minimal(self):
        card = IdeaCard(
            title="方向1",
            fragments=[],
            reasoning_chain="推理",
            assumptions=[],
        )
        assert card.feasibility is None
        assert card.title == "方向1"

    def test_create_with_review(self):
        card = IdeaCard(
            title="方向1",
            fragments=[EvidenceFragment(paper_id=1, quoted_text="text", section="results")],
            reasoning_chain="推理",
            assumptions=["假设1"],
            feasibility=FeasibilityScore(overall=3, theory=4, synthesis=2, measurement=3),
        )
        assert card.feasibility.overall == 3


class TestModeResult:
    def test_create(self):
        mr = ModeResult(
            primary_mode="gap_detector",
            secondary_modes=["analogy_engine"],
            confidence=0.85,
            search_queries=["hydrogen superconductors future work"],
            rationale="用户问研究方向",
        )
        assert mr.primary_mode == "gap_detector"
        assert len(mr.secondary_modes) == 1


class TestReviewVerdict:
    def test_create(self):
        rv = ReviewVerdict(
            flaws=[{"severity": "medium", "description": "缺少稳定性论证"}],
            feasibility_score=3,
            revised_idea="修正后的文本",
            dimensions={"theory": 4, "synthesis": 2, "measurement": 3},
        )
        assert rv.feasibility_score == 3
        assert len(rv.flaws) == 1
