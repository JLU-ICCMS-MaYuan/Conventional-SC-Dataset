"""Inspiration Agent 会话状态与核心数据类。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceFragment:
    """点子的灵感来源文献片段。"""
    paper_id: int
    quoted_text: str
    section: str = ""


@dataclass
class FeasibilityScore:
    """点子在三个维度的可行性评分。"""
    overall: int  # 1-5
    theory: int   # 理论自洽性 1-5
    synthesis: int  # 合成可达性 1-5
    measurement: int  # 测量可验证性 1-5


@dataclass
class IdeaCard:
    """包含证据链的研究点子。"""
    title: str
    fragments: list[dict] = field(default_factory=list)
    reasoning_chain: str = ""
    assumptions: list[str] = field(default_factory=list)
    feasibility: dict | None = None


@dataclass
class ModeResult:
    """ModeRouter 的输出。"""
    primary_mode: str
    secondary_modes: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    confidence: float = 1.0
    search_queries: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class ReviewVerdict:
    """DualReviewer 的输出。"""
    flaws: list[dict] = field(default_factory=list)
    feasibility_score: int = 3
    revised_idea: str = ""
    dimensions: dict = field(default_factory=dict)


MODE_LABELS: dict[str, str] = {
    "gap_detector": "文献缺口探测",
    "analogy_engine": "类比推荐引擎",
    "contradiction_catalyst": "矛盾证据催化",
    "composition_walker": "成分空间漫步",
    "counterfactual_reasoner": "反事实推理",
}


@dataclass
class InspirationSession:
    """探索模式会话状态。"""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    user_question: str = ""
    history: list[dict] = field(default_factory=list)
    current_mode: str | None = None
    collected_ideas: list[dict] = field(default_factory=list)
    rag_data: str = ""
    mode_history: list[str] = field(default_factory=list)

    @property
    def mode_label(self) -> str:
        if self.current_mode is None:
            return "未确定"
        return MODE_LABELS.get(self.current_mode, self.current_mode)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_question": self.user_question,
            "history": self.history.copy(),
            "current_mode": self.current_mode,
            "collected_ideas": self.collected_ideas.copy(),
            "rag_data": self.rag_data,
            "mode_history": self.mode_history.copy(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "InspirationSession":
        return cls(
            session_id=d.get("session_id", uuid.uuid4().hex),
            user_question=d.get("user_question", ""),
            history=d.get("history", []),
            current_mode=d.get("current_mode"),
            collected_ideas=d.get("collected_ideas", []),
            rag_data=d.get("rag_data", ""),
            mode_history=d.get("mode_history", []),
        )

    def check_exit(self, user_response: str) -> bool:
        exit_keywords = {"退出", "不用探索", "取消探索", "算了"}
        return any(kw in user_response for kw in exit_keywords)

    def add_idea(self, idea: dict) -> None:
        self.collected_ideas.append(idea)
