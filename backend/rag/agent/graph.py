"""
Inspiration Agent — 三段式交互图

图结构:
  START → clarify ⇄ design ⇄ discuss → END

Stage1 澄清: 了解兴趣/背景/约束，问到信息足够为止
Stage2 设计: 查文献 → 生成研究方案和 idea
Stage3 讨论: 审稿评分 → 和用户讨论→ 可回到设计或结束
"""

from __future__ import annotations

import asyncio
import re as _re
from typing import Any, Literal, Annotated, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages


class InspirationState(TypedDict):
    messages: Annotated[list, add_messages]
    stage: str                        # 当前阶段: clarify / design / discuss
    mode: str                         # 思考模式
    search_queries: list[str]         # 搜索词
    retrieval_result: dict | None     # 检索结果
    curated_chunks: list[dict] | None # 筛选后 chunks
    ideas: list[dict]                 # IdeaCard 列表
    user_constraints: str             # 用户约束（从对话中提取）
    iteration: int


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ═══════════════════════════════════════════════
# Stage 1: 提问与澄清
# ═══════════════════════════════════════════════

CLARIFY_PROMPT = """你是超导材料研究顾问。当前处于「提问与澄清」阶段。

## 判断标准（按优先级）
以下条件满足任意两条即可进入下一阶段:
1. 用户说了研究方法 (DFT/实验/ML 等)
2. 用户说了材料体系 (氢化物/铜氧化物/铁基等)
3. 用户说了具体约束 (压力范围/元素偏好/性能目标等)

## 规则
- 如果满足≥2条 → 回复 "READY:" 开头，总结需求，进入方案设计
- 如果只满足0-1条 → 问 1 个关键问题
- 不要在用户已提供足够信息后继续追问
- 用中文"""


def clarify_node(state: InspirationState) -> dict:
    """Stage1: 了解用户 → 决定是否进入 Stage2"""
    from openai import OpenAI
    from backend.rag.config import settings

    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    resp = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "system", "content": CLARIFY_PROMPT}] +
                 [{"role": "user" if getattr(m, "type", "") in ("human", "user")
                   else "assistant", "content": m.content}
                  for m in state["messages"] if hasattr(m, "content")],
        temperature=0.3, max_tokens=500, stream=False)

    answer = resp.choices[0].message.content or ""
    is_ready = "READY:" in answer
    return {"messages": [{"role": "assistant", "content": answer}],
            "stage": "design" if is_ready else "clarify",
            "iteration": state.get("iteration", 0) + 1}


def clarify_router(state: InspirationState) -> Literal["clarify", "design", "__end__"]:
    """Stage1 路由: 信息够了 → design，不够 → 暂停等回复"""
    if state.get("stage") == "design":
        return "design"
    return "clarify_end"  # 暂停 → 等用户回复


# ═══════════════════════════════════════════════
# Stage 2: 方案设计
# ═══════════════════════════════════════════════

def design_router_node(state: InspirationState) -> dict:
    """进入 Stage2: 先选思考模式 + 生成搜索词"""
    from backend.rag.inspiration.mode_router import route_mode

    question = ""
    for m in state["messages"]:
        if getattr(m, "type", "") in ("human", "user"):
            question = m.content

    _MAP = {"human": "user", "ai": "assistant", "system": "system"}
    history = [{"role": _MAP.get(getattr(m, "type", ""), "user"),
                "content": m.content}
               for m in state["messages"] if hasattr(m, "content")]

    mode_result = _run_async(route_mode(question, history))
    return {"mode": mode_result.primary_mode,
            "search_queries": mode_result.search_queries}


def design_search_node(state: InspirationState) -> dict:
    from backend.rag.inspiration.retrieval import execute_retrieval
    result = _run_async(execute_retrieval(
        mode=state["mode"], search_queries=state["search_queries"]))
    return {"retrieval_result": result}


def design_curator_node(state: InspirationState) -> dict:
    from backend.rag.inspiration.curator import curate_papers
    question = ""
    for m in state["messages"]:
        if getattr(m, "type", "") in ("human", "user"):
            question = m.content
    curation = _run_async(curate_papers(question, state["retrieval_result"] or {}))
    return {"curated_chunks": curation.get("chunks", [])}


def design_evidence_node(state: InspirationState) -> dict:
    from backend.rag.inspiration.evidence import parse_idea_cards
    from backend.rag.inspiration.session import MODE_LABELS
    from backend.rag.inspiration.retrieval import format_rag_context
    from backend.rag.inspiration.prompts import EVIDENCE_BUILDER_SYSTEM, build_explore_prompt
    from openai import OpenAI
    from backend.rag.config import settings

    question = ""
    for m in state["messages"]:
        if getattr(m, "type", "") in ("human", "user"):
            question = m.content
    rag_context = format_rag_context(state["retrieval_result"] or {})
    mode_label = MODE_LABELS.get(state["mode"], state["mode"])
    prompt = build_explore_prompt(
        question=question, mode=state["mode"], mode_label=mode_label,
        rationale="", rag_context=rag_context, history=[])
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    resp = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "system", "content": EVIDENCE_BUILDER_SYSTEM},
                  {"role": "user", "content": prompt}],
        temperature=0.7, max_tokens=3500, stream=False)
    full_text = resp.choices[0].message.content or ""
    cards = parse_idea_cards(full_text)
    clean_text = _re.sub(r'<!--IDEA_CARD[\s\S]*?-->', '', full_text).strip()
    return {"ideas": cards, "messages": [{"role": "assistant", "content": clean_text}],
            "stage": "discuss"}


# ═══════════════════════════════════════════════
# Stage 3: 方案讨论
# ═══════════════════════════════════════════════

DISCUSS_SYSTEM = """你是超导材料研究顾问。当前处于「方案讨论」阶段。

你刚刚给用户提出了研究方案。现在应该:
1. 简要总结方案要点
2. 邀请用户反馈: "你觉得这个方向怎么样？有什么想调整的吗？"
3. 如果用户提出修改意见 → 回复 "REVISE: 用户想调整xxx"，触发方案修改
4. 如果用户满意 → 给出具体的下一步行动建议
5. 用中文"""


def discuss_node(state: InspirationState) -> dict:
    """Stage3: 讨论方案 → 用户反馈 → revise / done"""
    from backend.rag.inspiration.reviewer import parse_review_verdicts
    from backend.rag.inspiration.prompts import REVIEWER_SYSTEM
    from openai import OpenAI
    from backend.rag.config import settings

    ideas = state.get("ideas", [])

    # 如果刚进入 Stage3，先审稿 + 总结
    evidence_text = ""
    for m in state["messages"]:
        if hasattr(m, "content") and not getattr(m, "tool_calls", None):
            evidence_text = m.content

    review_text = ""
    if ideas and evidence_text:
        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        resp = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "system", "content": REVIEWER_SYSTEM},
                      {"role": "user", "content": f"请审核以下研究点子的可行性。\n\n{evidence_text}"}],
            temperature=0.3, max_tokens=1000, stream=False)
        review_text = resp.choices[0].message.content or ""
        parse_review_verdicts(review_text)

    # 生成讨论回复
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    resp = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "system", "content": DISCUSS_SYSTEM}] +
                 [{"role": "user" if getattr(m, "type", "") in ("human", "user")
                   else "assistant", "content": m.content}
                  for m in state["messages"] if hasattr(m, "content")],
        temperature=0.5, max_tokens=800, stream=False)

    answer = resp.choices[0].message.content or ""
    if review_text:
        answer = f"## 审稿意见\n\n{review_text}\n\n---\n\n{answer}"

    is_revise = "REVISE:" in answer

    return {"messages": [{"role": "assistant", "content": answer}],
            "stage": "design" if is_revise else "discuss",
            "iteration": state.get("iteration", 0) + 1}


def discuss_router(state: InspirationState) -> Literal["design", "discuss_end", "__end__"]:
    if state.get("stage") == "design":
        return "design"
    return "discuss_end"


# ═══════════════════════════════════════════════
# 构建图
# ═══════════════════════════════════════════════

def build_graph():
    w = StateGraph(InspirationState)

    # Stage1 节点
    w.add_node("clarify", clarify_node)
    w.add_node("clarify_end", lambda s: {})  # 暂停标记

    # Stage2 子流水线
    w.add_node("design_router", design_router_node)
    w.add_node("design_search", design_search_node)
    w.add_node("design_curator", design_curator_node)
    w.add_node("design_evidence", design_evidence_node)

    # Stage3 节点
    w.add_node("discuss", discuss_node)
    w.add_node("discuss_end", lambda s: {})

    # 入口
    w.set_entry_point("clarify")

    # Stage1 → Stage2 或暂停
    w.add_conditional_edges("clarify", clarify_router, {
        "design": "design_router",
        "clarify_end": "clarify_end",
    })
    w.add_edge("clarify_end", END)

    # Stage2 线性流水线
    w.add_edge("design_router", "design_search")
    w.add_edge("design_search", "design_curator")
    w.add_edge("design_curator", "design_evidence")
    w.add_edge("design_evidence", "discuss")

    # Stage3 → 改方案 / 暂停
    w.add_conditional_edges("discuss", discuss_router, {
        "design": "design_router",  # ← 用户不满意，重新设计
        "discuss_end": "discuss_end",
    })
    w.add_edge("discuss_end", END)

    return w.compile()


_graph = build_graph()


# ═══════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════

def run(question: str, prev_messages: list | None = None) -> dict:
    """运行一轮。prev_messages 为上一轮的完整消息链"""
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if prev_messages:
            msgs = list(prev_messages) + [HumanMessage(content=question)]
        else:
            msgs = [HumanMessage(content=question)]

        state: InspirationState = {
            "messages": msgs, "stage": "clarify", "mode": "",
            "search_queries": [], "retrieval_result": None,
            "curated_chunks": None, "ideas": [],
            "user_constraints": "", "iteration": 0}
        result = _graph.invoke(state, config={"recursion_limit": 30})
    finally:
        loop.close()

    answer = ""
    for m in reversed(result.get("messages", [])):
        if hasattr(m, "content") and m.content:
            answer = m.content
            break

    return {"answer": answer, "stage": result.get("stage", ""),
            "mode": result.get("mode", ""),
            "ideas": result.get("ideas", []),
            "messages": result.get("messages", [])}
