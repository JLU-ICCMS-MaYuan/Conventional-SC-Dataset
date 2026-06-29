"""Tests for inspiration.mode_router — LLM mode routing."""
import json
import pytest
from backend.rag.rag.inspiration.mode_router import parse_mode_result
from backend.rag.rag.inspiration.session import ModeResult


class TestParseModeResult:
    def test_valid_json(self):
        response = json.dumps({
            "primary_mode": "gap_detector",
            "secondary_modes": ["analogy_engine"],
            "confidence": 0.9,
            "search_queries": ["query1", "query2"],
            "rationale": "用户问研究方向空白",
        })
        result = parse_mode_result(response)
        assert isinstance(result, ModeResult)
        assert result.primary_mode == "gap_detector"
        assert len(result.search_queries) == 2
        assert result.confidence == 0.9

    def test_fallback_on_invalid_json(self):
        result = parse_mode_result("invalid json {{{")
        assert result.primary_mode == "gap_detector"
        assert result.confidence == 0.0
        assert "解析失败" in result.rationale

    def test_fallback_on_missing_fields(self):
        response = json.dumps({"primary_mode": "composition_walker"})
        result = parse_mode_result(response)
        assert result.primary_mode == "composition_walker"
        assert result.search_queries == []
        assert result.secondary_modes == []

    def test_fallback_on_empty_string(self):
        result = parse_mode_result("")
        assert result.primary_mode == "gap_detector"

    def test_unknown_mode_preserved(self):
        response = json.dumps({
            "primary_mode": "nonexistent_mode",
            "secondary_modes": [],
            "confidence": 0.5,
            "search_queries": [],
            "rationale": "test",
        })
        result = parse_mode_result(response)
        assert result.primary_mode == "nonexistent_mode"  # 保留原值，下游处理
