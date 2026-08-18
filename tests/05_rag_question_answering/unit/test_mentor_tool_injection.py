"""Mentor 公共构造器的工具物理隔离。"""

from __future__ import annotations

import pytest

pytest.importorskip("langgraph")

from backend.rag.agent.mentor import build_graph


def test_llm_only_graph_has_no_tool_execution_node() -> None:
    graph = build_graph(tools=[])

    assert "tools" not in graph.get_graph().nodes


def test_tool_enabled_graph_has_tool_execution_node() -> None:
    graph = build_graph()

    assert "tools" in graph.get_graph().nodes
