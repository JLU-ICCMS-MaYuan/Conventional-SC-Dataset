"""
brainstorm.py — 头脑风暴会话管理 + 子 Agent。

Brainstorm 子 Agent 内部可调用 search_kg 和 search_rag 两个工具，
通过 DeepSeek Function Calling 实现，最多 3 轮迭代。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from openai import OpenAI

from backend.rag.config import settings


class BrainstormPhase(IntEnum):
    EXPLORE = 1    # 探索上下文
    CLARIFY = 2    # 追问澄清（可循环）
    PROPOSE = 3    # 提出路径
    PRESENT = 4    # 逐节呈现方案
    SUMMARIZE = 5  # 收敛总结


PHASE_LABELS: dict[int, str] = {
    1: "探索上下文",
    2: "追问澄清",
    3: "提出路径",
    4: "逐节呈现",
    5: "收敛总结",
}

# ── 各阶段 Prompt 模板 ─────────────────────────────────────────────

PHASE_PROMPTS: dict[int, str] = {
    BrainstormPhase.EXPLORE: """你是学术头脑风暴助手。当前阶段: {phase_label} ({phase}/{total})

用户问题: "{user_question}"
数据库概况: {db_context}

你的任务:
1. 用1-2句话总结你对用户探索方向的理解
2. 提出一个关键澄清问题（只提一个），帮助缩小范围
   - 优先使用选择题（2-4个选项）
   - 选项应基于专业知识 + 数据库实际情况

先复述理解，再提问。只输出这些。""",

    BrainstormPhase.CLARIFY: """当前阶段: {phase_label} ({phase}/{total})

已收集信息:
{collected_info}

逐一追问关键问题。每个问题:
- 一次只问一个
- 优先选择题（2-4个选项）
- 基于已回答问题逐步深入
- 当你认为信息足够（通常3-5轮）后，输出 [PHASE_COMPLETE] 结束该阶段

本轮不要问之前已经问过的问题。""",

    BrainstormPhase.PROPOSE: """当前阶段: {phase_label} ({phase}/{total})

基于已收集的需求:
{collected_info}

检索结果:
{search_results}

提出2-3个具体可行的思路/方向。每条包含:
1. 思路标题（一句话）
2. 可行性评估（高/中/低，基于数据库实际数据）
3. 关键文献支撑（标注 [PID_xxx]）
4. 推荐理由

推荐其中一条并说明原因。最后询问用户选择哪条深入。""",

    BrainstormPhase.PRESENT: """当前阶段: {phase_label} ({phase}/{total})

已选定路径: {selected_path}

将选定路径分为以下小节，逐节呈现:
1. 背景与研究现状
2. 候选材料/方法
3. 预期挑战与风险
4. 下一步具体建议

每节呈现后等待用户确认，再继续下一节。
用户说"好的"、"继续"、"下一节"时前进到下一节。
当前正在呈现第 {present_section}/{total_sections} 节。""",

    BrainstormPhase.SUMMARIZE: """当前阶段: {phase_label} ({phase}/{total})

汇总本次头脑风暴:
- 讨论的问题与选定方向
- 关键结论
- 推荐的下一步行动
- 相关文献列表

输出结构化总结后加 [BRAINSTORM_END] 退出头脑风暴模式。只输出总结，不要加额外说明。""",
}

# ── 子 Agent Tool 定义 ─────────────────────────────────────────────

BRAINSTORM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_kg",
            "description": "查询超导材料的结构化数据（Tc、压力、λ、ωlog、N(Ef)等物理参数）。用于获取准确的数值数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "predicate": {
                        "type": "string",
                        "description": "查询的属性类型，如 '超导温度(AD)'、'压力'、'电声耦合lambda'"
                    },
                    "operator": {
                        "type": "string",
                        "enum": [">", "<", ">=", "<="],
                        "description": "数值比较运算符，默认 '>'"
                    },
                    "value": {
                        "type": "string",
                        "description": "比较阈值，如 '0' 表示获取所有大于0的记录"
                    },
                },
                "required": ["predicate"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_rag",
            "description": "在超导文献全文数据库中搜索相关文本片段。用于获取机理解释、背景知识、实验方法等文本信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词，如 'LaH10 clathrate structure mechanism'"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回的文献片段数量，默认5，最大20",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


@dataclass
class BrainstormSession:
    """头脑风暴会话状态。跨多轮对话持久化。"""

    phase: BrainstormPhase = BrainstormPhase.EXPLORE
    user_question: str = ""
    collected_info: list[str] = field(default_factory=list)
    paths: list[dict] = field(default_factory=list)
    selected_path: int | None = None
    present_section: int = 0  # Phase 4 当前小节 (1-indexed, 1-4)
    clarify_rounds: int = 0

    @property
    def total_sections(self) -> int:
        return 4

    @property
    def max_clarify_rounds(self) -> int:
        return settings.brainstorm_max_clarify_rounds

    @property
    def phase_label(self) -> str:
        return PHASE_LABELS.get(int(self.phase), "未知")

    def to_dict(self) -> dict:
        return {
            "phase": int(self.phase),
            "phase_label": self.phase_label,
            "user_question": self.user_question,
            "collected_info": self.collected_info.copy(),
            "paths": self.paths.copy(),
            "selected_path": self.selected_path,
            "present_section": self.present_section,
            "clarify_rounds": self.clarify_rounds,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BrainstormSession":
        return cls(
            phase=BrainstormPhase(d.get("phase", 1)),
            user_question=d.get("user_question", ""),
            collected_info=d.get("collected_info", []),
            paths=d.get("paths", []),
            selected_path=d.get("selected_path"),
            present_section=d.get("present_section", 0),
            clarify_rounds=d.get("clarify_rounds", 0),
        )

    def build_phase_prompt(
        self,
        user_message: str,
        db_context: str = "",
        search_results: str = "",
    ) -> str:
        """根据当前 phase 构建对应阶段的 system prompt。"""
        template = PHASE_PROMPTS.get(int(self.phase))
        if template is None:
            template = PHASE_PROMPTS[BrainstormPhase.EXPLORE]

        return template.format(
            phase_label=self.phase_label,
            phase=int(self.phase),
            total=5,
            user_question=self.user_question or user_message,
            db_context=db_context or "暂无数据库信息",
            collected_info="\n".join(f"- {info}" for info in self.collected_info) if self.collected_info else "暂无",
            search_results=search_results or "暂无检索结果",
            selected_path=self.paths[self.selected_path]["title"] if (self.paths and self.selected_path is not None) else "未选定",
            present_section=self.present_section,
            total_sections=self.total_sections,
        )

    def check_exit(self, user_response: str) -> bool:
        """检查用户是否要退出。"""
        exit_keywords = {"退出", "不用brainstorm", "不用头脑风暴", "取消", "算了"}
        return any(kw in user_response for kw in exit_keywords)

    def check_advance(self, user_response: str) -> bool:
        """检查是否推进到下一阶段。

        注意：此方法在 run_brainstorm_subagent 中被调用时，
        user_response 是 LLM 的输出内容（非用户输入）。
        EXPLORE 阶段 LLM 输出的是探索问题（用户尚未回答），
        PROPOSE 阶段 LLM 输出的是路径提议（用户尚未选择），
        因此这两个阶段应返回 False，由用户的下一条消息触发推进。
        """
        if self.phase == BrainstormPhase.EXPLORE:
            # Phase 1: LLM 生成探索问题，用户尚未回答，不推进
            return False
        elif self.phase == BrainstormPhase.CLARIFY:
            # Phase 2: [PHASE_COMPLETE] 或达到最大轮数
            if "[PHASE_COMPLETE]" in user_response:
                return True
            if self.clarify_rounds >= self.max_clarify_rounds:
                return True
            return False
        elif self.phase == BrainstormPhase.PROPOSE:
            # Phase 3: LLM 生成路径提议，用户尚未选择，不推进
            return False
        elif self.phase == BrainstormPhase.PRESENT:
            # Phase 4: 确认推进：第4节完成后推进
            if self.present_section >= self.total_sections:
                return True
            return "[SECTION_DONE]" in user_response
        elif self.phase == BrainstormPhase.SUMMARIZE:
            return "[BRAINSTORM_END]" in user_response
        return False

    def advance_phase(self):
        """推进到下一阶段。"""
        self.phase = BrainstormPhase(self.phase + 1)
        # Phase 4 进入时重置 section 计数
        if self.phase == BrainstormPhase.PRESENT:
            self.present_section = 1
        elif self.phase == BrainstormPhase.SUMMARIZE:
            self.present_section = 0


async def run_brainstorm_subagent(
    session: BrainstormSession,
    user_message: str,
    db_context: str,
):
    """Brainstorm 子 Agent 内部循环（async generator）。

    子 Agent 拥有工具 [search_kg, search_rag]，最多 3 轮 Function Calling。
    收集足够信息后生成当前阶段的回答。

    Yields:
        {"type": "brainstorm_status", "data": {"action": str, "message": str}}  — 状态更新
        {"type": "result", "data": {"phase": int, "content": str, "search_results": str, "is_complete": bool}}  — 最终结果
    """
    from typing import AsyncIterator

    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

    system_prompt = session.build_phase_prompt(
        user_message=user_message,
        db_context=db_context,
    )

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    max_rounds = settings.brainstorm_max_agent_rounds
    search_results_parts: list[str] = []

    for _round in range(max_rounds):
        yield {"type": "brainstorm_status", "data": {"action": "thinking", "message": "正在思考分析..."}}

        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            tools=BRAINSTORM_TOOLS,
            temperature=0.3,
            max_tokens=2000,
        )

        choice = response.choices[0]
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            # 处理工具调用
            messages.append(choice.message)
            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                if func_name == "search_kg":
                    yield {"type": "brainstorm_status", "data": {"action": "searching_kg", "message": "正在查询超导材料结构化数据..."}}
                    result = await _execute_kg_search(func_args)
                elif func_name == "search_rag":
                    yield {"type": "brainstorm_status", "data": {"action": "searching_rag", "message": "正在检索相关文献..."}}
                    result = await _execute_rag_search(func_args)
                else:
                    result = json.dumps({"error": f"未知工具: {func_name}"})

                search_results_parts.append(f"[{func_name}] {result[:500]}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            yield {"type": "brainstorm_status", "data": {"action": "analyzing", "message": "正在分析检索结果..."}}
        else:
            # 没有工具调用，获取文本回答
            yield {"type": "brainstorm_status", "data": {"action": "generating", "message": "正在生成回答..."}}
            content = choice.message.content or ""
            yield {
                "type": "result",
                "data": {
                    "phase": int(session.phase),
                    "content": content,
                    "search_results": "\n".join(search_results_parts),
                    "is_complete": session.check_advance(content),
                }
            }
            return

    # 超过最大轮数，强制生成回答
    yield {"type": "brainstorm_status", "data": {"action": "generating", "message": "正在汇总生成回答..."}}
    final_response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages + [{"role": "user", "content": "请基于已收集的信息，输出你当前阶段的回答。"}],
        temperature=0.3,
        max_tokens=2000,
    )
    content = final_response.choices[0].message.content or ""

    yield {
        "type": "result",
        "data": {
            "phase": int(session.phase),
            "content": content,
            "search_results": "\n".join(search_results_parts),
            "is_complete": session.check_advance(content),
        }
    }


async def _execute_kg_search(args: dict) -> str:
    """执行 KG 检索。"""
    try:
        from backend.rag.knowledge_graph import query as kg_query

        predicate = args.get("predicate", "超导温度(AD)")
        operator = args.get("operator", ">")
        value = args.get("value", "0")
        results = await kg_query(predicate, operator=operator, value=value)

        top10 = results[:10]
        return json.dumps(
            [
                {
                    "subject": r["subject"],
                    "predicate": r.get("predicate", predicate),
                    "object": r.get("object", ""),
                    "paper_id": r.get("paper_id"),
                }
                for r in top10
            ],
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


async def _execute_rag_search(args: dict) -> str:
    """执行 RAG 检索。"""
    try:
        from backend.rag.search.engine import search_semantic_only
        from backend.rag.rag.reranker import rerank_chunks

        query = args.get("query", "")
        top_k = min(args.get("top_k", 5), 20)
        search_result = await search_semantic_only(query, top_k=top_k)
        chunks = search_result.get("chunks", [])
        if chunks:
            chunks = await rerank_chunks(query, chunks, top_k=min(top_k, len(chunks)))

        return json.dumps(
            [
                {
                    "content": c.get("content", "")[:300],
                    "paper_id": c.get("paper_id"),
                    "section_name": c.get("section_name", ""),
                }
                for c in (chunks or [])
            ],
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})
