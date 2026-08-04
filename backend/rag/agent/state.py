"""Agent 状态定义"""
from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph Agent 共享状态"""
    messages: Annotated[list, add_messages]   # 对话历史 + tool call/results
    tool_results: dict[str, Any]              # 本轮 tool 执行结果汇总
    iteration: int                            # 当前轮数
