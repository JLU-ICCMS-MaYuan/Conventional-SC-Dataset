"""Tests for inspiration.retrieval — strategy dataclass and registry."""
import pytest
from backend.rag.rag.inspiration.retrieval import (
    RetrievalStrategy,
    RETRIEVAL_STRATEGIES,
    get_strategy,
)


class TestRetrievalStrategy:
    def test_create_strategy(self):
        s = RetrievalStrategy(
            name="test",
            section_filter=["conclusion"],
            semantic_boost=["gap", "future work"],
            kg_enabled=False,
        )
        assert s.name == "test"
        assert s.kg_enabled is False
        assert s.kg_filter is None

    def test_create_with_kg(self):
        s = RetrievalStrategy(
            name="analogy",
            section_filter=["discussion"],
            semantic_boost=["charge transfer"],
            kg_enabled=True,
            kg_filter={"by_elements": True},
        )
        assert s.kg_enabled is True
        assert s.kg_filter == {"by_elements": True}


class TestRetrievalRegistry:
    def test_all_five_modes_registered(self):
        expected = {
            "gap_detector",
            "analogy_engine",
            "contradiction_catalyst",
            "composition_walker",
            "counterfactual_reasoner",
        }
        assert set(RETRIEVAL_STRATEGIES.keys()) == expected

    def test_gap_detector_no_kg(self):
        s = RETRIEVAL_STRATEGIES["gap_detector"]
        assert s.kg_enabled is False
        assert s.section_filter == []  # Curator 替代了 section 过滤

    def test_analogy_engine_has_kg(self):
        s = RETRIEVAL_STRATEGIES["analogy_engine"]
        assert s.kg_enabled is True
        assert s.kg_filter is not None

    def test_all_strategies_have_queries(self):
        for name, s in RETRIEVAL_STRATEGIES.items():
            assert len(s.semantic_boost) > 0, f"{name} should have semantic_boost keywords"


class TestGetStrategy:
    def test_valid_mode(self):
        s = get_strategy("gap_detector")
        assert s.name == "文献缺口探测"

    def test_unknown_mode_fallback(self):
        s = get_strategy("nonexistent")
        assert s.name == "文献缺口探测"  # fallback to gap_detector

    def test_empty_mode_raises(self):
        with pytest.raises(ValueError):
            get_strategy("")
