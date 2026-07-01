# Inspiration Agent 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将旧的 brainstorm 管线替换为领域专精的 Inspiration Agent（5 种思考模式 + 证据绑定 + 双角色自省）

**Architecture:** 分层切片架构：ModeRouter → Retrieval → EvidenceBuilder → DualReviewer，每层通过 dataclass 接口通信，engine.py 仅加路由分支

**Tech Stack:** Python 3.10+ / FastAPI SSE / OpenAI-compatible API (DeepSeek) / React + TypeScript

---

## 文件结构总览

```
backend/rag/rag/inspiration/        # 新建目录
├── __init__.py                     # 公开接口
├── session.py                      # InspirationSession + 数据类
├── prompts.py                      # 5 种模式 + 路由 + 证据 + 审核 prompt
├── mode_router.py                  # LLM 路由
├── retrieval.py                    # 5 种检索策略
├── evidence.py                     # 证据构建 + IdeaCard 解析
└── reviewer.py                     # 双角色自省

tests/inspiration/                  # 新建目录
├── __init__.py
├── test_session.py
├── test_retrieval.py
├── test_mode_router.py
├── test_evidence.py
├── test_reviewer.py
└── test_integration.py

backend/rag/rag/engine.py           # 修改：+~40 行路由分支
backend/rag/service.py              # 修改：brainstorm→explore 参数
backend/api/rag.py                  # 修改：+explore 字段
backend/rag/rag/brainstorm.py       # 修改：标 deprecated

frontend_test/src/hooks/useStreamingChat.ts  # 修改：新增 explore + SSE 事件
frontend_test/src/pages/RagPage.tsx          # 修改：探索按钮 + 证据卡片渲染
frontend_test/src/components/EvidenceCard.tsx # 新建
```

---

### Task 1: 测试目录 + Session 数据类测试

**Files:**
- Create: `tests/inspiration/__init__.py`
- Create: `tests/inspiration/test_session.py`

- [ ] **Step 1: 创建测试目录和测试文件**

```bash
mkdir -p tests/inspiration
touch tests/inspiration/__init__.py
```

- [ ] **Step 2: 编写 test_session.py——测试 InspirationSession 创建、序列化、反序列化**

```python
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
        assert len(s.session_id) == 36  # uuid4
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
```

- [ ] **Step 3: 运行测试，预期全部 FAIL（模块不存在）**

```bash
python -m pytest tests/inspiration/test_session.py -v
```
Expected: `ModuleNotFoundError: No module named 'backend.rag.rag.inspiration'`

---

### Task 2: session.py — 核心数据类

**Files:**
- Create: `backend/rag/rag/inspiration/__init__.py`
- Create: `backend/rag/rag/inspiration/session.py`

- [ ] **Step 1: 创建 __init__.py**

```python
"""Inspiration Agent — 领域专精的科研灵感激发引擎。

5 种思考模式 + 证据绑定 + 双角色自省。
"""
```

- [ ] **Step 2: 创建 session.py**

```python
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
    fragments: list[dict] = field(default_factory=list)  # [{paper_id, quoted_text, section}]
    reasoning_chain: str = ""
    assumptions: list[str] = field(default_factory=list)
    feasibility: dict | None = None  # {overall, theory, synthesis, measurement}


@dataclass
class ModeResult:
    """ModeRouter 的输出。"""
    primary_mode: str
    secondary_modes: list[str] = field(default_factory=list)
    confidence: float = 1.0
    search_queries: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class ReviewVerdict:
    """DualReviewer 的输出。"""
    flaws: list[dict] = field(default_factory=list)  # [{severity, description}]
    feasibility_score: int = 3
    revised_idea: str = ""
    dimensions: dict = field(default_factory=dict)  # {theory, synthesis, measurement}


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
    history: list[dict] = field(default_factory=list)  # [{role, content}]
    current_mode: str | None = None
    collected_ideas: list[dict] = field(default_factory=list)  # serialized IdeaCard
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
```

- [ ] **Step 3: 运行测试，预期全部 PASS**

```bash
python -m pytest tests/inspiration/test_session.py -v
```
Expected: 7 passed

- [ ] **Step 4: 提交**

```bash
git add tests/inspiration/ backend/rag/rag/inspiration/
git commit -m "feat: add InspirationSession + core data classes with tests"
```

---

### Task 3: prompts.py — 所有 Prompt 模板

**Files:**
- Create: `backend/rag/rag/inspiration/prompts.py`

- [ ] **Step 1: 创建 prompts.py**

```python
"""Inspiration Agent 的 Prompt 模板。

包含：模式路由 prompt、5 种模式检索 prompt、证据生成 prompt、审核 prompt。
"""

# ── ModeRouter Prompt ──────────────────────────────────────────────

MODE_ROUTER_SYSTEM = """你是氢化物超导研究灵感助手。根据用户问题，从以下 5 种思考模式中选择最合适的。

## 5 种模式

1. **gap_detector** — 文献缺口探测
   适用：用户想找未解决的研究问题、空白方向、还有什么可做的
   关键词：方向、空白、缺口、潜力、课题、未解决、还有什么

2. **analogy_engine** — 类比推荐
   适用：用户给一种成功策略或机制，想找可迁移到其他体系的方法
   关键词：类比、迁移、类似、借鉴、应用到、推广到

3. **contradiction_catalyst** — 矛盾催化
   适用：用户关注某材料的争议数据、反常现象、不同结论
   关键词：矛盾、差异、不一致、为什么不同、争议

4. **composition_walker** — 成分空间漫步
   适用：用户想基于已知化合物探索衍生/替换/掺杂组合
   关键词：替换、掺杂、三元、四元、衍生、候选、组合

5. **counterfactual_reasoner** — 反事实推理
   适用：颠覆性目标、非常规思路、突破性想法
   关键词：常压、突破、颠覆、新思路、非常规

## 输出格式
只返回 JSON：
{
  "primary_mode": "gap_detector",
  "secondary_modes": ["analogy_engine"],
  "confidence": 0.85,
  "search_queries": ["hydrogen-rich superconductors future research gaps", ...],
  "rationale": "为什么选择这个模式的一段中文解释"
}
"""


# ── 证据生成 Prompt ─────────────────────────────────────────────────

EVIDENCE_BUILDER_SYSTEM = """你是凝聚态物理学家，擅长基于文献提出新颖、具体的研究点子。

## 你的能力
你能查阅超导材料数据库中的论文和实验数据，在对话中自然引用文献来支撑你的观点。

## 你的风格
- 像有经验的导师一样和研究者对话
- 先理解对方的兴趣，再逐步深入
- 当你觉得有足够证据时，提出具体、新颖、有理有据的研究点子
- 引用数据时自然融入对话，不要像在读表格

## 引用格式
文献引用必须使用 [PID_xxx] 格式。例如："LaH₁₀ 在 250 GPa 下 Tc 达到 286 K [PID_74]。"

## 点子输出格式
当你提出一个具体的研究点子时，必须在点子后面用以下标记包裹结构化数据：

<!--IDEA_CARD
{
  "title": "点子的简短标题",
  "fragments": [
    {"paper_id": 74, "quoted_text": "引用的原文句子", "section": "discussion"}
  ],
  "reasoning_chain": "因为文献A中的X机制与文献B中的Y现象在物理上共有Z特征，所以可能...",
  "assumptions": ["假设1: 压力窗口 100-200 GPa", "假设2: ..."]
}
-->

## 关键规则
1. 每个数据点必须标注 [PID_xxx]
2. 明确区分"文献已有"和"你的推测"
3. 如果没有足够证据支持一个好点子，诚实说明"证据不足"
4. 每个点子都要有明确的推理链，不能是凭空猜测
5. 禁止重复文献中已完成的工作
"""


# ── 对话首条消息模板（含检索结果） ──────────────────────────────────

def build_explore_prompt(
    question: str,
    mode: str,
    mode_label: str,
    rationale: str,
    rag_context: str,
    history: list[dict] | None = None,
) -> str:
    """构建探索模式首条消息。"""
    mode_intro = f"[系统提示：用户正在使用探索模式（{mode_label}）。选择此模式的原因：{rationale}。请基于下面的数据库资料和你的专业知识，用对话的方式帮用户探索研究灵感。]"

    parts = [mode_intro]
    if rag_context:
        parts.append(f"\n数据库资料:\n{rag_context}")

    if history:
        history_lines = ["\n对话历史:"]
        for h in history[-6:]:
            role = "用户" if h["role"] == "user" else "助手"
            history_lines.append(f"{role}: {h['content']}")
        parts.append("\n".join(history_lines))

    parts.append(f"\n用户问题: {question}")
    return "\n\n".join(parts)


# ── Dual Reviewer Prompt ────────────────────────────────────────────

REVIEWER_SYSTEM = """你是挑剔的实验凝聚态物理学家。审核上面提出的研究点子，从实验可行性的角度找出潜在漏洞。

## 审核维度
1. **理论自洽性**：能带计算上是否可能？有没有明显违背物理原理的地方？
2. **合成可达性**：压力、温度、前驱物是否明确？是否在 DAC 技术极限内（~400 GPa）？
3. **测量可验证性**：Tc 是否在可测范围（>1 K）？信号能否被分辨？

## 输出格式
对每个点子，输出审核意见：

<!--REVIEW
{
  "flaws": [
    {"severity": "high", "description": "该笼结构在卸压过程中可能崩塌"},
    {"severity": "medium", "description": "缺少氢源和前驱体说明"}
  ],
  "feasibility_score": 3,
  "revised_idea": "修正后的描述...",
  "dimensions": {"theory": 4, "synthesis": 2, "measurement": 3}
}
-->

## 规则
- severity 为 high/medium/low
- feasibility_score 为 1-5 整数，5 表示可行性最高
- dimensions 中每项 1-5 整数
- 不要为了挑刺而挑刺，只指真正的问题
- 如果点子整体可行，可以给出 4-5 的高分
"""
```

- [ ] **Step 2: 提交**

```bash
git add backend/rag/rag/inspiration/prompts.py
git commit -m "feat: add inspiration agent prompt templates (router, evidence, reviewer)"
```

---

### Task 4: retrieval.py 测试

**Files:**
- Create: `tests/inspiration/test_retrieval.py`

- [ ] **Step 1: 编写测试**

```python
"""Tests for inspiration.retrieval — strategy dataclass and registry."""
import pytest
from backend.rag.rag.inspiration.retrieval import (
    RetrievalStrategy,
    RETRIEVAL_STRATEGIES,
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
        assert "conclusion" in s.section_filter

    def test_analogy_engine_has_kg(self):
        s = RETRIEVAL_STRATEGIES["analogy_engine"]
        assert s.kg_enabled is True
        assert s.kg_filter is not None

    def test_all_strategies_have_queries(self):
        for name, s in RETRIEVAL_STRATEGIES.items():
            assert len(s.semantic_boost) > 0, f"{name} should have semantic_boost keywords"
```

- [ ] **Step 2: 运行测试，预期 FAIL**

```bash
python -m pytest tests/inspiration/test_retrieval.py -v
```

---

### Task 5: retrieval.py — 5 种检索策略

**Files:**
- Create: `backend/rag/rag/inspiration/retrieval.py`

- [ ] **Step 1: 创建 retrieval.py**

```python
"""Inspiration Agent 检索策略层。

5 种思考模式各有不同的检索策略（语义查询关键词 + 元数据过滤 + KG 开关），
但共享同一 RAG + KG 底层调用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalStrategy:
    """一种思考模式的检索策略配置。"""
    name: str
    section_filter: list[str] = field(default_factory=list)
    semantic_boost: list[str] = field(default_factory=list)
    kg_enabled: bool = False
    kg_filter: dict | None = None


RETRIEVAL_STRATEGIES: dict[str, RetrievalStrategy] = {
    "gap_detector": RetrievalStrategy(
        name="文献缺口探测",
        section_filter=["conclusion", "future_work", "outlook"],
        semantic_boost=[
            "research gap", "remains unclear", "future work",
            "beyond the scope", "requires further", "open question",
            "尚未解决", "有待研究", "需要进一步",
        ],
        kg_enabled=False,
    ),
    "analogy_engine": RetrievalStrategy(
        name="类比推荐引擎",
        section_filter=["discussion", "results"],
        semantic_boost=[
            "chemical precompression", "charge transfer",
            "electron-phonon coupling", "hydrogen cage",
            "mechanism", "chemical pressure",
        ],
        kg_enabled=True,
        kg_filter={"by_elements": True},
    ),
    "contradiction_catalyst": RetrievalStrategy(
        name="矛盾证据催化",
        section_filter=["results", "discussion"],
        semantic_boost=[
            "discrepancy", "different", "however",
            "unexpected", "anomalous", "contradiction",
            "不一致", "差异", "矛盾",
        ],
        kg_enabled=True,
        kg_filter={"by_formula": True, "cross_paper": True},
    ),
    "composition_walker": RetrievalStrategy(
        name="成分空间漫步",
        section_filter=[],
        semantic_boost=[
            "doping", "substitution", "ternary", "alloying",
            "掺杂", "替换", "三元", "四元",
        ],
        kg_enabled=True,
        kg_filter={"by_elements": True, "include_candidates": True},
    ),
    "counterfactual_reasoner": RetrievalStrategy(
        name="反事实推理",
        section_filter=[],
        semantic_boost=[
            "metastable", "pressure quenching", "template",
            "molecular cation", "quasi-hydrogen cage",
            "ambient pressure", "亚稳", "淬火", "常压",
        ],
        kg_enabled=True,
        kg_filter={"max_pressure": 10},
    ),
}


def get_strategy(mode: str) -> RetrievalStrategy:
    """获取指定模式的检索策略。

    Args:
        mode: 模式名（gap_detector 等）

    Returns:
        对应的 RetrievalStrategy，未知模式返回 gap_detector 策略

    Raises:
        ValueError: mode 为空字符串
    """
    if not mode:
        raise ValueError("mode must not be empty")
    return RETRIEVAL_STRATEGIES.get(mode, RETRIEVAL_STRATEGIES["gap_detector"])


async def execute_retrieval(
    mode: str,
    search_queries: list[str],
    top_k: int = 10,
) -> dict[str, Any]:
    """执行检索：RAG 语义搜索 + 可选 KG 查询。

    Args:
        mode: 思考模式
        search_queries: ModeRouter 生成的语义查询列表
        top_k: RAG 检索数量

    Returns:
        {"chunks": [...], "kg_results": [...], "mode": str}
    """
    strategy = get_strategy(mode)

    # 拼接 semantic_boost 到查询中
    boosted_query = " ".join(search_queries + strategy.semantic_boost)

    # ── RAG 检索 ──
    chunks: list[dict] = []
    try:
        from backend.rag.search.engine import search_semantic_only
        from backend.rag.rag.reranker import rerank_chunks

        sr = await search_semantic_only(boosted_query, top_k=top_k)
        raw_chunks = sr.get("chunks", [])
        if raw_chunks:
            chunks = await rerank_chunks(boosted_query, raw_chunks, top_k=min(5, len(raw_chunks)))
            if not chunks:
                chunks = raw_chunks[:5]
    except Exception:
        pass

    # ── KG 查询 ──
    kg_results: list[dict] = []
    if strategy.kg_enabled:
        try:
            from backend.rag.knowledge_graph import query as kg_query

            if strategy.kg_filter:
                if "max_pressure" in strategy.kg_filter:
                    kg_results = await kg_query("压力", operator="<",
                                                value=str(strategy.kg_filter["max_pressure"]))
                else:
                    kg_results = await kg_query("超导温度(AD)", operator=">", value="0")
                    kg_results.sort(
                        key=lambda r: float(r["object"]) if r["object"].replace(".", "", 1).isdigit() else 0,
                        reverse=True,
                    )
                    kg_results = kg_results[:20]
        except Exception:
            pass

    return {
        "chunks": chunks or [],
        "kg_results": kg_results,
        "mode": mode,
    }


def format_rag_context(retrieval_result: dict[str, Any]) -> str:
    """将检索结果格式化为 LLM 可读的文本。

    Args:
        retrieval_result: execute_retrieval 的返回值

    Returns:
        格式化的文本，包含 KG 数据和文献片段
    """
    parts = []

    kg_results = retrieval_result.get("kg_results", [])
    if kg_results:
        parts.append("【相关超导材料数据】")
        for r in kg_results[:15]:
            pid = f" [PID_{r['paper_id']}]" if r.get("paper_id") else ""
            parts.append(f"  {r['subject']}: {r['object']}K{pid}")

    chunks = retrieval_result.get("chunks", [])
    if chunks:
        parts.append("\n【相关文献片段】")
        for c in chunks[:5]:
            pid = f" [PID_{c['paper_id']}]" if c.get("paper_id") else ""
            parts.append(f"  {c['content'][:300]}{pid}")

    return "\n".join(parts) if parts else ""
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/inspiration/test_retrieval.py -v
```
Expected: 7 passed

- [ ] **Step 3: 提交**

```bash
git add tests/inspiration/test_retrieval.py backend/rag/rag/inspiration/retrieval.py
git commit -m "feat: add inspiration retrieval strategy registry (5 modes)"
```

---

### Task 6: mode_router.py 测试

**Files:**
- Create: `tests/inspiration/test_mode_router.py`

- [ ] **Step 1: 编写测试**

```python
"""Tests for inspiration.mode_router — LLM mode routing."""
import json
import pytest
from unittest.mock import patch, MagicMock
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

    def test_unknown_mode_maps_to_gap_detector(self):
        response = json.dumps({
            "primary_mode": "nonexistent_mode",
            "secondary_modes": [],
            "confidence": 0.5,
            "search_queries": [],
            "rationale": "test",
        })
        result = parse_mode_result(response)
        assert result.primary_mode == "nonexistent_mode"  # 保留原值，下游处理
```

- [ ] **Step 2: 运行测试，预期 FAIL**

```bash
python -m pytest tests/inspiration/test_mode_router.py -v
```

---

### Task 7: mode_router.py — LLM 模式路由

**Files:**
- Create: `backend/rag/rag/inspiration/mode_router.py`

- [ ] **Step 1: 创建 mode_router.py**

```python
"""Inspiration Agent 模式路由器。

用一次 LLM 调用判断用户问题适合哪种思考模式，同时生成针对性搜索查询。
"""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from backend.rag.config import settings
from backend.rag.rag.inspiration.session import ModeResult
from backend.rag.rag.inspiration.prompts import MODE_ROUTER_SYSTEM

logger = logging.getLogger(__name__)


def parse_mode_result(llm_response: str) -> ModeResult:
    """解析 LLM 返回的 JSON，安全降级。

    Args:
        llm_response: LLM 返回的文本（应包含一个 JSON 对象）

    Returns:
        ModeResult，解析失败时返回默认值 gap_detector
    """
    try:
        data = json.loads(llm_response)
        return ModeResult(
            primary_mode=data.get("primary_mode", "gap_detector"),
            secondary_modes=data.get("secondary_modes", []),
            confidence=float(data.get("confidence", 0.0)),
            search_queries=data.get("search_queries", []),
            rationale=data.get("rationale", "解析失败"),
        )
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"ModeResult parse failed: {e}")
        return ModeResult(
            primary_mode="gap_detector",
            confidence=0.0,
            search_queries=[],
            rationale=f"解析失败，默认使用缺口探测模式。原始响应: {llm_response[:200]}",
        )


async def route_mode(
    question: str,
    history: list[dict] | None = None,
) -> ModeResult:
    """LLM 判断用户问题最适合哪种思考模式。

    Args:
        question: 用户问题
        history: 对话历史

    Returns:
        ModeResult 包含模式选择和搜索查询
    """
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    # 构建消息
    messages: list[dict] = [
        {"role": "system", "content": MODE_ROUTER_SYSTEM},
    ]
    if history:
        messages.extend(history[-4:])  # 最近 4 轮
    messages.append({"role": "user", "content": f"用户问题: {question}"})

    try:
        resp = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=300,
        )
        content = resp.choices[0].message.content or ""
        return parse_mode_result(content)
    except Exception as e:
        logger.error(f"ModeRouter LLM call failed: {e}")
        return ModeResult(
            primary_mode="gap_detector",
            confidence=0.0,
            search_queries=[question],
            rationale=f"LLM 调用失败，默认使用缺口探测模式",
        )
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/inspiration/test_mode_router.py -v
```
Expected: 5 passed

- [ ] **Step 3: 提交**

```bash
git add tests/inspiration/test_mode_router.py backend/rag/rag/inspiration/mode_router.py
git commit -m "feat: add inspiration ModeRouter with LLM mode detection"
```

---

### Task 8: evidence.py + reviewer.py 测试

**Files:**
- Create: `tests/inspiration/test_evidence.py`
- Create: `tests/inspiration/test_reviewer.py`

- [ ] **Step 1: 编写 test_evidence.py**

```python
"""Tests for inspiration.evidence — IDEA_CARD marker parsing."""
from backend.rag.rag.inspiration.evidence import parse_idea_cards


class TestParseIdeaCards:
    def test_single_card(self):
        text = """一些对话文本。
<!--IDEA_CARD
{
  "title": "LaH₄ 的理论与实验缺口",
  "fragments": [{"paper_id": 74, "quoted_text": "原文", "section": "discussion"}],
  "reasoning_chain": "因为X所以Y",
  "assumptions": ["压力 200 GPa"]
}
-->
后续对话。"""
        cards = parse_idea_cards(text)
        assert len(cards) == 1
        assert cards[0]["title"] == "LaH₄ 的理论与实验缺口"
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
```

- [ ] **Step 2: 编写 test_reviewer.py**

```python
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
```

- [ ] **Step 3: 运行测试，预期 FAIL**

```bash
python -m pytest tests/inspiration/test_evidence.py tests/inspiration/test_reviewer.py -v
```

---

### Task 9: evidence.py — 证据构建

**Files:**
- Create: `backend/rag/rag/inspiration/evidence.py`

- [ ] **Step 1: 创建 evidence.py**

```python
"""Inspiration Agent 证据构建层。

生成自然对话 + 嵌入式 IdeaCard marker。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from openai import OpenAI

from backend.rag.config import settings
from backend.rag.rag.inspiration.session import InspirationSession
from backend.rag.rag.inspiration.prompts import (
    EVIDENCE_BUILDER_SYSTEM,
    build_explore_prompt,
)

logger = logging.getLogger(__name__)

IDEA_CARD_MARKER = "<!--IDEA_CARD"
IDEA_CARD_END = "-->"


def parse_idea_cards(text: str) -> list[dict]:
    """从文本中提取所有 IDEA_CARD JSON。

    Args:
        text: 包含 <!--IDEA_CARD ... --> marker 的文本

    Returns:
        解析成功的 IdeaCard dict 列表
    """
    cards: list[dict] = []
    idx = 0
    while True:
        start = text.find(IDEA_CARD_MARKER, idx)
        if start == -1:
            break
        json_start = start + len(IDEA_CARD_MARKER)
        end = text.find(IDEA_CARD_END, json_start)
        if end == -1:
            break
        try:
            card = json.loads(text[json_start:end].strip())
            cards.append(card)
        except json.JSONDecodeError:
            logger.warning("Failed to parse IDEA_CARD JSON")
        idx = end + len(IDEA_CARD_END)
    return cards


async def build_evidence_stream(
    session: InspirationSession,
    mode_result: Any,  # ModeResult
    retrieval_result: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    """流式生成对话 + IdeaCard。

    Args:
        session: 当前会话
        mode_result: ModeRouter 的输出
        retrieval_result: execute_retrieval 的输出

    Yields:
        SSE 事件 dict: token / evidence_card / status
    """
    from backend.rag.rag.inspiration.retrieval import format_rag_context
    from backend.rag.rag.inspiration.session import MODE_LABELS

    rag_context = format_rag_context(retrieval_result)
    mode_label = MODE_LABELS.get(mode_result.primary_mode, mode_result.primary_mode)

    prompt = build_explore_prompt(
        question=session.user_question,
        mode=mode_result.primary_mode,
        mode_label=mode_label,
        rationale=mode_result.rationale,
        rag_context=rag_context,
        history=session.history,
    )

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    messages: list[dict] = [
        {"role": "system", "content": EVIDENCE_BUILDER_SYSTEM},
    ]
    if session.history:
        messages.extend(session.history[-6:])
    messages.append({"role": "user", "content": prompt})

    full_text = ""
    try:
        stream = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full_text += delta.content
                yield {"type": "token", "data": delta.content}
    except Exception as e:
        logger.error(f"Evidence builder failed: {e}")
        yield {"type": "token", "data": f"\n\n抱歉，生成过程出现错误：{e}"}
        return

    # 提取 IdeaCard
    cards = parse_idea_cards(full_text)
    for card in cards:
        session.add_idea(card)
        yield {"type": "evidence_card", "data": card}

    # 保存生成上下文到会话历史
    session.history.append({"role": "user", "content": session.user_question})
    session.history.append({"role": "assistant", "content": full_text})
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/inspiration/test_evidence.py -v
```
Expected: 4 passed

- [ ] **Step 3: 提交**

```bash
git add tests/inspiration/test_evidence.py backend/rag/rag/inspiration/evidence.py
git commit -m "feat: add inspiration EvidenceBuilder with IDEA_CARD marker parsing"
```

---

### Task 10: reviewer.py — 双角色自省

**Files:**
- Create: `backend/rag/rag/inspiration/reviewer.py`

- [ ] **Step 1: 创建 reviewer.py**

```python
"""Inspiration Agent 双角色自省。

生成者（EvidenceBuilder）输出后，审稿人（DualReviewer）审核并提出漏洞。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from openai import OpenAI

from backend.rag.config import settings
from backend.rag.rag.inspiration.prompts import REVIEWER_SYSTEM

logger = logging.getLogger(__name__)

REVIEW_MARKER = "<!--REVIEW"
REVIEW_END = "-->"


def parse_review_verdicts(text: str) -> list[dict]:
    """从文本中提取所有 REVIEW JSON。

    Args:
        text: 包含 <!--REVIEW ... --> marker 的文本

    Returns:
        解析成功的 ReviewVerdict dict 列表
    """
    verdicts: list[dict] = []
    idx = 0
    while True:
        start = text.find(REVIEW_MARKER, idx)
        if start == -1:
            break
        json_start = start + len(REVIEW_MARKER)
        end = text.find(REVIEW_END, json_start)
        if end == -1:
            break
        try:
            verdict = json.loads(text[json_start:end].strip())
            verdicts.append(verdict)
        except json.JSONDecodeError:
            logger.warning("Failed to parse REVIEW JSON")
        idx = end + len(REVIEW_END)
    return verdicts


async def review_stream(
    evidence_text: str,
) -> AsyncIterator[dict[str, Any]]:
    """对生成的证据文本进行双角色自省。

    Args:
        evidence_text: EvidenceBuilder 的完整输出（含 IDEA_CARD marker）

    Yields:
        SSE 事件 dict: token / review_verdict / status
    """
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    review_prompt = f"""请审核以下研究点子的可行性。对每个点子，找出至少 2 个潜在漏洞。

{evidence_text}

请按格式输出审核意见。"""

    messages: list[dict] = [
        {"role": "system", "content": REVIEWER_SYSTEM},
        {"role": "user", "content": review_prompt},
    ]

    full_text = ""
    try:
        stream = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full_text += delta.content
                yield {"type": "token", "data": delta.content}
    except Exception as e:
        logger.error(f"Reviewer failed: {e}")
        yield {"type": "token", "data": f"\n\n审核过程出现错误：{e}"}
        return

    # 提取 ReviewVerdict
    verdicts = parse_review_verdicts(full_text)
    for verdict in verdicts:
        yield {"type": "review_verdict", "data": verdict}
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/inspiration/test_reviewer.py -v
```
Expected: 4 passed

- [ ] **Step 3: 提交**

```bash
git add tests/inspiration/test_reviewer.py backend/rag/rag/inspiration/reviewer.py
git commit -m "feat: add inspiration DualReviewer with REVIEW marker parsing"
```

---

### Task 11: integration test — 完整链路

**Files:**
- Create: `tests/inspiration/test_integration.py`

- [ ] **Step 1: 编写集成测试**

```python
"""Integration tests for inspiration pipeline — mock LLM, real retrieval."""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.rag.rag.inspiration.session import InspirationSession
from backend.rag.rag.inspiration.mode_router import route_mode, parse_mode_result
from backend.rag.rag.inspiration.retrieval import get_strategy, RETRIEVAL_STRATEGIES
from backend.rag.rag.inspiration.evidence import parse_idea_cards
from backend.rag.rag.inspiration.reviewer import parse_review_verdicts


MOCK_MODE_RESPONSE = json.dumps({
    "primary_mode": "gap_detector",
    "secondary_modes": ["composition_walker"],
    "confidence": 0.9,
    "search_queries": ["superconducting hydrides research gaps 2024"],
    "rationale": "用户问研究方向，最适合用缺口探测",
})


class TestFullMarkerPipeline:
    """测试完整 marker 解析管线——不依赖 LLM。"""

    def test_evidence_then_review_markers(self):
        evidence_text = """基于数据库分析，我发现两个方向：

## 方向一：LaH₄ 的理论预测与实验缺失
<!--IDEA_CARD
{
  "title": "LaH₄ 稳定相的理论预测与实验验证缺口",
  "fragments": [{"paper_id": 74, "quoted_text": "LaH₄ has been predicted...", "section": "conclusion"}],
  "reasoning_chain": "理论预测 LaH₄ 在 >100 GPa 下稳定但缺乏实验验证 → 可设计 DAC 实验",
  "assumptions": ["LaH₄ 在 100-200 GPa 可合成"]
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
  "revised_idea": "在 100-200 GPa 用 DAC + 激光加热合成 LaH₄...",
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
        assert cards[0]["title"].startswith("LaH₄")
        assert len(verdicts) == 2
        assert verdicts[0]["feasibility_score"] == 4
        assert verdicts[1]["feasibility_score"] == 2
        assert len(verdicts[1]["flaws"]) == 2


class TestSessionLifecycle:
    """测试会话生命周期。"""

    def test_full_session_flow(self):
        s = InspirationSession(user_question="La-H 体系还有什么方向？")
        s.current_mode = "gap_detector"
        s.mode_history.append("gap_detector")

        # 模拟添加点子
        s.add_idea({"title": "点子1", "fragments": []})
        s.add_idea({"title": "点子2", "fragments": []})
        assert len(s.collected_ideas) == 2

        # 序列化
        d = s.to_dict()
        assert d["current_mode"] == "gap_detector"
        assert len(d["collected_ideas"]) == 2

        # 反序列化
        restored = InspirationSession.from_dict(d)
        assert restored.session_id == s.session_id
        assert len(restored.collected_ideas) == 2

    def test_mode_switch(self):
        s = InspirationSession(user_question="测试")
        s.current_mode = "gap_detector"
        s.mode_history.append("gap_detector")

        # 用户切换模式
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
        assert result.primary_mode == ""  # 保留原值
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/inspiration/test_integration.py -v
```
Expected: 5 passed

- [ ] **Step 3: 提交**

```bash
git add tests/inspiration/test_integration.py
git commit -m "test: add inspiration integration tests (marker pipeline + session lifecycle)"
```

---

### Task 12: Engine + Service + API 集成

**Files:**
- Modify: `backend/rag/rag/engine.py`
- Modify: `backend/rag/service.py`
- Modify: `backend/api/rag.py`

- [ ] **Step 1: 修改 engine.py**

在 `ask_stream` 函数签名中添加 `explore: bool = False` 参数，并在 brainstorm 检测之前插入探索模式路由。

具体修改：

1. 替换导入：删除 brainstorm 导入，添加 inspiration 导入
2. 修改函数签名：`brainstorm: bool = False` → `explore: bool = False`
3. 在原先 brainstorm 路由位置（第 465-570 行），替换为探索模式路由

以下是需要替换的 engine.py 代码段（第 18-24 行导入部分）：

```python
# 旧导入
from backend.rag.rag.brainstorm import (
    BrainstormSession,
    BrainstormPhase,
    run_brainstorm_turn,
    _should_advance,
    _detect_path_selection,
)

# 新导入
from backend.rag.rag.inspiration.session import InspirationSession
from backend.rag.rag.inspiration.mode_router import route_mode
from backend.rag.rag.inspiration.retrieval import execute_retrieval, format_rag_context
from backend.rag.rag.inspiration.evidence import build_evidence_stream, parse_idea_cards
from backend.rag.rag.inspiration.reviewer import review_stream, parse_review_verdicts
```

标记常量替换：

```python
# 旧
BS_SESSION_MARKER = "<!--BS:"

# 新
IS_SESSION_MARKER = "<!--IS:"  # Inspiration Session marker
```

函数签名修改（第 438-445 行）：

```python
# 旧
async def ask_stream(
    question: str,
    top_k: int = 15,
    rerank_top_k: int = 5,
    model: str | None = None,
    history: list[dict] | None = None,
    brainstorm: bool = False,
):

# 新
async def ask_stream(
    question: str,
    top_k: int = 15,
    rerank_top_k: int = 5,
    model: str | None = None,
    history: list[dict] | None = None,
    explore: bool = False,
):
```

Brainstorm 路由替换（原第 465-570 行整块替换为）：

```python
    # ── Inspiration: 探索模式路由 ──
    is_session: InspirationSession | None = _try_restore_is_session(history, question)

    if is_session is None and explore:
        is_session = InspirationSession(user_question=question)

    if is_session is not None:
        if is_session.check_exit(question):
            yield {"type": "inspire_exit", "data": {"reason": "user_abort"}}
            done_msg = "已退出探索模式。"
            for char in done_msg:
                yield {"type": "token", "data": char}
            yield {"type": "done", "data": {"citations": [], "answer": done_msg,
                     "source": "inspire_exit", "papers": {}, "top10": []}}
            return

        # 首次进入：记录当前消息到历史
        if not is_session.history:
            is_session.history.append({"role": "user", "content": question})

        yield {
            "type": "inspire_enter",
            "data": {
                "session_id": is_session.session_id,
                "mode": is_session.current_mode or "pending",
                "mode_label": is_session.mode_label,
            }
        }

        # 1. ModeRouter
        yield {"type": "status", "data": {"action": "routing", "message": "正在分析问题并选择分析视角..."}}
        mode_result = await route_mode(question, is_session.history)

        is_session.current_mode = mode_result.primary_mode
        is_session.mode_history.append(mode_result.primary_mode)

        yield {
            "type": "inspire_mode",
            "data": {
                "mode": mode_result.primary_mode,
                "label": is_session.mode_label,
                "rationale": mode_result.rationale,
            }
        }

        # 2. Retrieval
        yield {"type": "status", "data": {"action": "searching", "message": "正在检索相关文献..."}}
        retrieval_result = await execute_retrieval(
            mode_result.primary_mode,
            mode_result.search_queries,
        )

        # 3. EvidenceBuilder（流式）
        yield {"type": "status", "data": {"action": "generating", "message": "正在生成研究点子..."}}
        evidence_text = ""
        async for event in build_evidence_stream(is_session, mode_result, retrieval_result):
            if event["type"] == "token":
                evidence_text += event["data"]
            yield event

        # 4. DualReviewer（流式）
        yield {"type": "status", "data": {"action": "reviewing", "message": "正在自我审核..."}}
        yield {"type": "token", "data": "\n\n---\n**🔍 审稿意见：**\n"}
        async for event in review_stream(evidence_text):
            yield event

        # 持久化 session marker + done
        is_json = json.dumps(is_session.to_dict(), ensure_ascii=False)
        session_marker = f"\n\n{IS_SESSION_MARKER}{is_json}-->"
        for char in session_marker:
            yield {"type": "token", "data": char}

        answer = evidence_text + session_marker
        yield {"type": "done", "data": {
            "citations": [],
            "answer": answer,
            "source": f"inspire_{mode_result.primary_mode}",
            "papers": {},
            "top10": [],
            "inspiration": is_session.to_dict(),
        }}
        return
```

同时，将 `_try_restore_bs_session` 替换为 `_try_restore_is_session`：

```python
def _try_restore_is_session(history: list[dict] | None, user_message: str = "") -> InspirationSession | None:
    """尝试从对话历史恢复 InspirationSession。

    从 AI 回答中的 <!--IS:json--> marker 恢复。
    """
    if not history:
        return None

    for h in reversed(history):
        if h["role"] == "assistant":
            content = h.get("content", "")
            if IS_SESSION_MARKER in content:
                try:
                    start = content.index(IS_SESSION_MARKER) + len(IS_SESSION_MARKER)
                    end = content.index("-->", start)
                    data = json.loads(content[start:end])
                    return InspirationSession.from_dict(data)
                except (json.JSONDecodeError, ValueError, KeyError):
                    pass
            break
    return None
```

- [ ] **Step 2: 修改 service.py**

将 `chat_stream` 函数的 `brainstorm` 参数改为 `explore`：

```python
# 第 125 行，修改参数和传递
async def chat_stream(
    question: str,
    top_k: int = 15,
    rerank_top_k: int = 5,
    history: list[dict[str, str]] | None = None,
    explore: bool = False,  # 曾用名 brainstorm
) -> AsyncIterator[dict[str, Any]]:
    _ensure_chat_available()
    try:
        from backend.rag.rag.engine import ask_stream

        async for event in ask_stream(
            question,
            top_k=top_k,
            rerank_top_k=rerank_top_k,
            history=history,
            explore=explore,
        ):
            yield event
    except (RagDataUnavailableError, RagChatUnavailableError):
        raise
    except Exception as exc:
        raise RagInternalError(str(exc)) from exc
```

- [ ] **Step 3: 修改 api/rag.py**

在 `RagChatRequest` 中添加 `explore` 字段，在 SSE 端点传递：

```python
class RagChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(15, ge=1, le=50)
    rerank_top_k: int = Field(5, ge=1, le=20)
    history: list[RagMessage] = Field(default_factory=list)
    explore: bool = Field(False, description="是否启用灵感探索模式")
```

SSE 端点传递（第 152 行）：

```python
# 旧
brainstorm=request.brainstorm,

# 新
explore=request.explore,
```

- [ ] **Step 4: Python 语法检查**

```bash
python -c "from backend.rag.rag.engine import ask_stream; print('engine OK')"
python -c "from backend.rag.service import chat_stream; print('service OK')"
```
Expected: 无错误输出

- [ ] **Step 5: 提交**

```bash
git add backend/rag/rag/engine.py backend/rag/service.py backend/api/rag.py
git commit -m "feat: integrate inspiration agent pipeline into engine/service/API"
```

---

### Task 13: brainstorm.py 标记废弃

**Files:**
- Modify: `backend/rag/rag/brainstorm.py`

- [ ] **Step 1: 修改模块 docstring**

将第 1-4 行的 docstring 替换为：

```python
"""
brainstorm.py — DEPRECATED: 已被 inspiration/ 模块替代。

此模块不再被 engine.py 调用，保留仅用于 git 历史追溯。
新功能请使用 backend.rag.rag.inspiration.* 。
"""
```

- [ ] **Step 2: Python 语法检查**

```bash
python -c "import backend.rag.rag.brainstorm; print('deprecated module still importable')"
```

- [ ] **Step 3: 提交**

```bash
git add backend/rag/rag/brainstorm.py
git commit -m "deprecate: mark brainstorm.py as deprecated in favor of inspiration module"
```

---

### Task 14: Frontend — useStreamingChat hook

**Files:**
- Modify: `frontend_test/src/hooks/useStreamingChat.ts`

- [ ] **Step 1: 更新 BrainstormState → InspirationState 类型**

```typescript
// 旧类型
interface BrainstormState {
  active: boolean
  phase: number
  phaseLabel: string
  totalPhases: number
  statusMessage: string
}

// 新类型
interface InspirationState {
  active: boolean
  mode: string
  modeLabel: string
  statusMessage: string
  sessionId: string
  ideasCount: number
}

// IdeaCard 证据卡片
interface IdeaCard {
  title: string
  fragments: Array<{ paper_id: number; quoted_text: string; section: string }>
  reasoning_chain: string
  assumptions: string[]
  feasibility?: { overall: number; theory: number; synthesis: number; measurement: number }
}

interface ReviewVerdict {
  flaws: Array<{ severity: string; description: string }>
  feasibility_score: number
  revised_idea: string
  dimensions: { theory: number; synthesis: number; measurement: number }
}
```

- [ ] **Step 2: 更新 CachedMeta 和状态**

```typescript
interface CachedMeta {
  papers: Record<string, PaperInfo>
  top10: any[]
  inspiration: InspirationState | null  // 曾用名 brainstorm
}

// 默认值
const defaultInspiration: InspirationState = {
  active: false, mode: '', modeLabel: '', statusMessage: '', sessionId: '', ideasCount: 0
}
```

- [ ] **Step 3: 更新 send 函数**

`send` 函数签名从 `(question: string, brainstorm = false)` 改为 `(question: string, explore = false)`：

```typescript
const send = useCallback(async (question: string, explore = false) => {
  // ... 前面代码不变 ...

  // API 调用
  const response = await api.postStream('/api/rag/chat/stream', {
    question: q, top_k: 15, rerank_top_k: 5, history, explore,
  })
```

- [ ] **Step 4: 更新 SSE 事件处理**

替换旧的 brainstorm 事件处理：

```typescript
// 旧事件: brainstorm_suggest, brainstorm_enter, brainstorm_phase, brainstorm_exit
// 新事件:
if (eventType === 'inspire_enter') {
  setInspiration({
    active: true,
    mode: data.mode,
    modeLabel: data.mode_label,
    sessionId: data.session_id,
    statusMessage: '正在分析...',
    ideasCount: 0,
  })
} else if (eventType === 'inspire_mode') {
  setInspiration(prev => ({ ...prev, mode: data.mode, modeLabel: data.label }))
} else if (eventType === 'evidence_card') {
  setInspiration(prev => ({ ...prev, ideasCount: prev.ideasCount + 1 }))
} else if (eventType === 'inspire_exit') {
  setInspiration(defaultInspiration)
} else if (eventType === 'status') {
  setInspiration(prev => prev.active ? { ...prev, statusMessage: data.message || '' } : prev)
}

// done 事件更新
if (data.inspiration) {
  const is: InspirationState = {
    active: true,
    mode: data.inspiration.current_mode || '',
    modeLabel: data.inspiration.mode_label || '',
    statusMessage: '',
    sessionId: data.inspiration.session_id || '',
    ideasCount: data.inspiration.collected_ideas?.length || 0,
  }
  setInspiration(is)
  finalInspiration = is
}

// 持久化
function saveMeta(cid: string, meta: CachedMeta) {
  localStorage.setItem(metaKey(cid), JSON.stringify(meta))
}
// ...
if (cid) saveMeta(cid, { papers: receivedPapers, top10: receivedTop10, inspiration: finalInspiration })
```

- [ ] **Step 5: TypeScript 编译检查**

```bash
cd frontend_test && npx tsc --noEmit --skipLibCheck src/hooks/useStreamingChat.ts 2>&1 | head -20
```
Expected: 无类型错误（可能有已存在的无关警告）

- [ ] **Step 6: 提交**

```bash
git add frontend_test/src/hooks/useStreamingChat.ts
git commit -m "feat: update useStreamingChat for inspiration agent (explore mode + new SSE events)"
```

---

### Task 15: Frontend — EvidenceCard 组件

**Files:**
- Create: `frontend_test/src/components/EvidenceCard.tsx`

- [ ] **Step 1: 创建 EvidenceCard 组件**

```typescript
import React from 'react'

interface EvidenceFragment {
  paper_id: number
  quoted_text: string
  section: string
}

interface ReviewVerdict {
  flaws: Array<{ severity: string; description: string }>
  feasibility_score: number
  revised_idea: string
  dimensions: { theory: number; synthesis: number; measurement: number }
}

interface IdeaCard {
  title: string
  fragments: EvidenceFragment[]
  reasoning_chain: string
  assumptions: string[]
  feasibility?: { overall: number; theory: number; synthesis: number; measurement: number }
}

interface EvidenceCardProps {
  idea: IdeaCard
  review?: ReviewVerdict
}

const severityColors: Record<string, string> = {
  high: '#e55',
  medium: '#f90',
  low: '#999',
}

const EvidenceCard: React.FC<EvidenceCardProps> = ({ idea, review }) => {
  return (
    <div style={{
      margin: '12px 0', border: '1px solid #e0e0e0', borderRadius: 12,
      backgroundColor: '#fafbff', overflow: 'hidden', fontSize: 13,
    }}>
      {/* 标题栏 */}
      <div style={{
        padding: '10px 14px', fontWeight: 600, fontSize: 14,
        backgroundColor: '#eef1ff', color: '#3b4da0',
        borderBottom: '1px solid #dde0f0',
      }}>
        💡 {idea.title}
      </div>

      {/* 证据片段 */}
      {idea.fragments.length > 0 && (
        <div style={{ padding: '10px 14px' }}>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#666', marginBottom: 6 }}>
            📎 灵感来源
          </div>
          {idea.fragments.map((f, i) => (
            <div key={i} style={{
              padding: '6px 10px', marginBottom: 6,
              backgroundColor: '#f5f5f5', borderRadius: 6,
              borderLeft: '3px solid #4d6bfe',
            }}>
              <div style={{ fontStyle: 'italic', color: '#333', lineHeight: 1.6 }}>
                "{f.quoted_text}"
              </div>
              <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
                [PID_{f.paper_id}] — {f.section}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 推理链 */}
      {idea.reasoning_chain && (
        <div style={{ padding: '10px 14px', borderTop: '1px solid #f0f0f0' }}>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#666', marginBottom: 4 }}>
            🔗 推理链
          </div>
          <div style={{ color: '#444', lineHeight: 1.6 }}>{idea.reasoning_chain}</div>
        </div>
      )}

      {/* 假设前提 */}
      {idea.assumptions.length > 0 && (
        <div style={{ padding: '10px 14px', borderTop: '1px solid #f0f0f0' }}>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#666', marginBottom: 4 }}>
            ⚠️ 假设前提
          </div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {idea.assumptions.map((a, i) => (
              <li key={i} style={{ color: '#666', marginBottom: 2 }}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 审稿意见 */}
      {review && (
        <div style={{ padding: '10px 14px', borderTop: '1px solid #f0e0e0', backgroundColor: '#fffaf5' }}>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#e55', marginBottom: 6 }}>
            🔍 审稿意见 (可行性: {'★'.repeat(review.feasibility_score)}{'☆'.repeat(5 - review.feasibility_score)})
          </div>
          {review.flaws.map((f, i) => (
            <div key={i} style={{
              padding: '4px 8px', marginBottom: 4,
              backgroundColor: '#fff', borderRadius: 4,
              borderLeft: `3px solid ${severityColors[f.severity] || '#999'}`,
              fontSize: 12,
            }}>
              <span style={{
                display: 'inline-block', padding: '1px 6px', borderRadius: 3,
                backgroundColor: severityColors[f.severity] || '#999',
                color: '#fff', fontSize: 10, marginRight: 6,
              }}>
                {f.severity.toUpperCase()}
              </span>
              {f.description}
            </div>
          ))}
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 12 }}>
            <span>理论: {'★'.repeat(review.dimensions.theory)}</span>
            <span>合成: {'★'.repeat(review.dimensions.synthesis)}</span>
            <span>测量: {'★'.repeat(review.dimensions.measurement)}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default EvidenceCard
export type { IdeaCard, ReviewVerdict, EvidenceFragment }
```

- [ ] **Step 2: TypeScript 编译检查**

```bash
cd frontend_test && npx tsc --noEmit --skipLibCheck src/components/EvidenceCard.tsx 2>&1 | head -20
```

- [ ] **Step 3: 提交**

```bash
git add frontend_test/src/components/EvidenceCard.tsx
git commit -m "feat: add EvidenceCard component for inspiration idea display"
```

---

### Task 16: Frontend — RagPage 探索按钮

**Files:**
- Modify: `frontend_test/src/pages/RagPage.tsx`

- [ ] **Step 1: 替换 brainstorm 为 inspiration 状态**

```typescript
// 从 useStreamingChat 解构
const {
  convs, activeId, messages, loading, papers, top10, streamRef,
  inspiration,  // 曾用名 brainstorm
  suggestMessage, setSuggestMessage,
  newConversation, switchConversation, deleteConversation, send,
} = useStreamingChat()
```

- [ ] **Step 2: 替换状态变量**

```typescript
// 旧
const [thinkMode, setThinkMode] = useState(false)

// 新 — 探索模式
const [exploreMode, setExploreMode] = useState(false)
```

- [ ] **Step 3: 更新 handleSend**

```typescript
// 旧
const handleSend = () => { const q = input; setInput(''); send(q, thinkMode) }

// 新
const handleSend = () => { const q = input; setInput(''); send(q, exploreMode) }
```

- [ ] **Step 4: 更新探索按钮**

```typescript
// 旧 thinkBtn
<button
  onClick={() => setThinkMode(!thinkMode)}
  style={{
    ...st.thinkBtn,
    backgroundColor: thinkMode ? '#4d6bfe' : '#fff',
    color: thinkMode ? '#fff' : '#999',
    borderColor: thinkMode ? '#4d6bfe' : '#e5e5e5',
  }}
  title={thinkMode ? '思索模式已开启' : '开启思索模式'}
>💡</button>

// 新 exploreBtn
<button
  onClick={() => setExploreMode(!exploreMode)}
  style={{
    ...st.thinkBtn,
    backgroundColor: exploreMode ? '#4d6bfe' : '#fff',
    color: exploreMode ? '#fff' : '#999',
    borderColor: exploreMode ? '#4d6bfe' : '#e5e5e5',
  }}
  title={exploreMode ? '探索模式已开启' : '开启探索模式'}
>🔬</button>
```

- [ ] **Step 5: 更新 placeholder 和 brainstorming bar**

```typescript
// placeholder
placeholder={exploreMode ? "说说你的研究兴趣，AI 帮你探索灵感..." : "问一个超导问题..."}

// 灵感探索模式状态栏（替换旧 brainstorm bar）
{inspiration.active && (
  <>
    <div style={st.bsBar}>
      <span style={st.bsLabel}>
        🔬 {inspiration.modeLabel}
        {inspiration.ideasCount > 0 && ` (已生成 ${inspiration.ideasCount} 个点子)`}
      </span>
    </div>
    {inspiration.statusMessage && (
      <div style={st.bsStatus}>
        <span style={st.bsStatusDot} />
        {inspiration.statusMessage}
      </div>
    )}
  </>
)}

{/* 普通模式状态提示 */}
{!inspiration.active && loading && inspiration.statusMessage && (
  <div style={st.normalStatus}>
    <span style={st.bsStatusDot} />
    {inspiration.statusMessage}
  </div>
)}
```

- [ ] **Step 6: 更新退出按钮**

```typescript
{inspiration.active && (
  <button
    onClick={() => send('退出')}
    style={st.bsExitBtn}
    title="退出探索模式"
  >
    退出探索
  </button>
)}
```

- [ ] **Step 7: TypeScript 编译检查**

```bash
cd frontend_test && npx tsc --noEmit --skipLibCheck src/pages/RagPage.tsx 2>&1 | head -20
```

- [ ] **Step 8: 提交**

```bash
git add frontend_test/src/pages/RagPage.tsx
git commit -m "feat: replace brainstorm button with explore button in RagPage"
```

---

### Task 17: 最终验证 + 清理

- [ ] **Step 1: 运行全部测试**

```bash
python -m pytest tests/inspiration/ -v
```
Expected: 全部 ~23 个测试通过

- [ ] **Step 2: 确认旧测试不被破坏**

```bash
python -m pytest tests/test_rag_internal_imports.py -v
```
Expected: 通过（确认 inspiration 模块可导入）

- [ ] **Step 3: Python 导入完整性检查**

```bash
python -c "
from backend.rag.rag.inspiration import InspirationSession, IdeaCard, ModeResult
from backend.rag.rag.inspiration.mode_router import route_mode, parse_mode_result
from backend.rag.rag.inspiration.retrieval import RETRIEVAL_STRATEGIES, execute_retrieval, get_strategy
from backend.rag.rag.inspiration.evidence import build_evidence_stream, parse_idea_cards
from backend.rag.rag.inspiration.reviewer import review_stream, parse_review_verdicts
print('All imports OK')
"
```

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "chore: final verification — all tests pass, imports clean"
```
```

