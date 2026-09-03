"""
MentorGraph — 交互式研究助理

图结构:
  START → mentor ──── 问问题 ──→ wait_user → END
           │   ▲
           │   └── search ←──┘
           │   (调 tool 查资料后回到 mentor)
           │
           └── 回答完成 ──→ END
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from backend.rag.agent.state import AgentState
from backend.rag.agent.tools import ALL_TOOLS
from backend.rag.llm_client import get_langchain_llm


SYSTEM_PROMPT = """你是超导材料研究助理，风格是苏格拉底式的——通过提问引导学生自己思考。

## 你的能力
你可以调取知识图谱和文献数据库来获取：
- 材料物性数据（Tc、压力等）
- 论文上下文（谁研究过什么）
- 文献原文片段（具体方法、结论）

## 对话规则（重要）
1. 对话历史中的上一轮你已经问过的问题，不要重复问
2. 用户的新回复是对你上一轮问题的回应，直接基于新信息行动
3. 如果用户提供了足够具体的约束 → 查资料 + 给出分析，不要再问
4. 每轮只做一件事：要么问一个新问题，要么查资料后给出分析
5. 用中文交流"""

ROUTE_PROMPT = """看完整对话。最后一句话属于：
- "wait": 在问学生问题，需要等待回复
- "tool": 需要调用工具查资料
- "end": 给出了最终建议或分析，对话完成

只回答一个词。"""


def _build_llm() -> ChatOpenAI:
    return get_langchain_llm()


# ═══════════════════════════════════════════════
# 节点
# ═══════════════════════════════════════════════

def mentor_node(state: AgentState, tools: list | None = None) -> dict:
    """助理节点：看完整对话 + tool 能查到什么 → 决定做什么"""
    selected_tools = ALL_TOOLS if tools is None else list(tools)
    llm = _build_llm()
    if selected_tools:
        llm = llm.bind_tools(selected_tools)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


# ═══════════════════════════════════════════════
# 路由
# ═══════════════════════════════════════════════

def router(state: AgentState) -> Literal["tools", "wait_user", "__end__"]:
    """看助理的最后一条消息，判断下一步"""
    iteration = state.get("iteration", 0)

    last = state["messages"][-1] if state["messages"] else None

    # 助理说 "call material_info" 这类 → 去执行 tool
    if last and getattr(last, "tool_calls", None):
        if iteration >= 5:  # 最多5次 tool 调用
            return "__end__"
        return "tools"

    # 助理输出的是文本 → 用 LLM 判断是提问还是结论
    if last and hasattr(last, "content") and last.content:
        judge = _build_llm().invoke(
            list(state["messages"]) + [HumanMessage(content=ROUTE_PROMPT)]
        )
        verdict = judge.content.strip().lower()
        if "wait" in verdict:
            return "wait_user"

    return "__end__"


def _after_tools(state: AgentState) -> dict:
    """每次 tool 调用后计数器 +1"""
    return {"iteration": state.get("iteration", 0) + 1}


# ═══════════════════════════════════════════════
# 构建图
# ═══════════════════════════════════════════════

def build_graph(tools: list | None = None):
    """构建 Mentor graph；传空列表可物理禁用全部工具。"""
    selected_tools = ALL_TOOLS if tools is None else list(tools)
    workflow = StateGraph(AgentState)

    workflow.add_node("mentor", lambda state: mentor_node(state, selected_tools))
    workflow.add_node("wait_user", lambda s: {})

    workflow.set_entry_point("mentor")

    if selected_tools:
        workflow.add_node("tools", ToolNode(selected_tools))
        workflow.add_conditional_edges(
            "mentor", router,
            {"tools": "tools", "wait_user": "wait_user", "__end__": END},
        )
        # tools → _after_tools(计数+1) → mentor
        workflow.add_node("after_tools", _after_tools)
        workflow.add_edge("tools", "after_tools")
        workflow.add_edge("after_tools", "mentor")
    else:
        workflow.add_conditional_edges(
            "mentor", router,
            {"tools": END, "wait_user": "wait_user", "__end__": END},
        )
    workflow.add_edge("wait_user", END)    # 问题提出 → 暂停

    return workflow.compile()


TOOL_NAMES_CN = {
    "search_papers": "搜索论文",
    "paper_context": "获取论文上下文",
    "material_info": "查询材料信息",
    "explore_graph": "探索知识图谱",
    "paper_path": "查找论文路径",
    "search_literature": "检索文献",
    "query_properties": "查询物性数据",
}

_graph = build_graph()


# ═══════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════

def run(question: str, prev_messages: list | None = None) -> dict:
    """运行一轮

    prev_messages: 上一轮返回的 messages 链，None = 新对话
    """
    if prev_messages:
        # 始终以 SystemMessage 开头，保留可见消息
        clean = [SystemMessage(content=SYSTEM_PROMPT)]
        for m in prev_messages:
            if isinstance(m, (SystemMessage, HumanMessage)):
                clean.append(m)
            elif isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                # 重建纯文本 AIMessage，去掉 tool_calls 属性
                clean.append(AIMessage(content=m.content))
        msgs = clean + [HumanMessage(content=question)]
    else:
        msgs = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]

    result = _graph.invoke(
        {"messages": msgs, "iteration": 0, "tool_results": {}},
        config={"recursion_limit": 30},
    )

    answer = ""
    # 找最后一个有内容且无 tool_calls 的 AIMessage
    for m in reversed(result.get("messages", [])):
        if isinstance(m, AIMessage) and m.content:
            if not getattr(m, "tool_calls", None):
                answer = m.content
                break
            # 如果只有带 tool_calls 的消息，取最后一个有内容的
            if not answer:
                answer = m.content

    return {"answer": answer, "messages": result.get("messages", [])}


async def run_stream(question: str, prev_messages: list | None = None):
    """流式运行（yield event），供前端 SSE 使用"""
    if prev_messages:
        clean = [SystemMessage(content=SYSTEM_PROMPT)]
        for m in prev_messages:
            if isinstance(m, (SystemMessage, HumanMessage)):
                clean.append(m)
            elif isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                clean.append(AIMessage(content=m.content))
        msgs = clean + [HumanMessage(content=question)]
    else:
        msgs = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]

    state = {"messages": msgs, "iteration": 0, "tool_results": {}}

    async for event in _graph.astream_events(state, version="v2"):
        kind = event.get("event", "")

        if kind == "on_chain_start":
            name = event.get("name", "")
            if name == "mentor":
                yield {"type": "status", "data": {"message": "💭 分析中..."}}
            elif name == "tools":
                yield {"type": "status", "data": {"message": "🔧 执行工具..."}}

        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield {"type": "token", "data": chunk.content}

        elif kind == "on_tool_start":
            raw_name = event.get("name", "")
            label = TOOL_NAMES_CN.get(raw_name, raw_name)
            yield {
                "type": "tool_start",
                "data": {
                    "name": label,
                    "input": event.get("data", {}).get("input", {}),
                },
            }

        elif kind == "on_tool_end":
            raw_name = event.get("name", "")
            label = TOOL_NAMES_CN.get(raw_name, raw_name)
            output = event.get("data", {}).get("output")
            yield {
                "type": "tool_end",
                "data": {
                    "name": label,
                    "output": str(output)[:500] if output else "",
                },
            }

    yield {"type": "done", "data": {}}


# ═══════════════════════════════════════════════
# 交互式测试
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("超导研究助理 — 交互式对话 (quit 退出)")
    print("=" * 50)

    state = None
    while True:
        q = input("\n👤 你: ").strip()
        if q.lower() == "quit":
            break
        r = run(q, prev_messages=state)
        state = r["messages"]
        print(f"\n🤖 助理: {r['answer']}")
