"""
brainstorm.py — 头脑风暴会话管理 + 子 Agent。

基于 superpowers:brainstorming 技能的 6 步流程，适配学术 RAG 场景。
最终交付物: 面向用户的计划表（结构化 Markdown 文档）。

流程: 探索上下文 → 一次一问澄清 → 提出 2-3 路径 → 逐节呈现 → 写计划书 → 自审
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from openai import OpenAI

from backend.rag.config import settings


class BrainstormPhase(IntEnum):
    EXPLORE = 1     # 探索上下文 — 了解数据库覆盖范围
    CLARIFY = 2     # 一次一问澄清需求（可循环多轮）
    PROPOSE = 3     # 提出 2-3 条路径 + 权衡 + 推荐
    PRESENT = 4     # 逐节呈现选定路径的方案
    DOCUMENT = 5    # 写面向用户的计划书
    REVIEW = 6      # AI 自审计划书 + 修正


PHASE_LABELS: dict[int, str] = {
    1: "探索上下文",
    2: "澄清需求",
    3: "提出路径",
    4: "逐节呈现",
    5: "撰写计划",
    6: "自审修正",
}

# ── 各阶段 Prompt 模板 ─────────────────────────────────────────────

PHASE_PROMPTS: dict[int, str] = {
    BrainstormPhase.EXPLORE: """你是学术头脑风暴助手，帮助研究者规划科研方向。

当前阶段: {phase_label} (第{phase}步/共{total}步)

## 你的任务

用户想探索的方向: "{user_question}"

数据库概况: {db_context}

## 规则

1. 用 1-2 句话总结你对用户方向的理解
2. 基于数据库实际覆盖情况，告诉用户"当前数据库中这个领域有 X 篇论文、Y 种超导体"
3. 提出一个关键澄清问题（选择题，2-4 个选项）

## 禁止

- 禁止在探索阶段就进行分析或提议
- 禁止输出超过 4 句话
- 你没有检索工具可用

## 输出格式

复述理解 → 数据库概况 → 一个选择题 → 等待用户选择""",

    BrainstormPhase.CLARIFY: """当前阶段: {phase_label} (第{phase}步/共{total}步)

## 已收集的用户需求
{collected_info}

## 规则（superpowers:brainstorming 模式）

- **一次只问一个问题**，优先选择题
- 逐步深入，直到信息足够（通常 3-5 轮）
- **禁止**: 一次性问多个问题、跳到分析、给出结论
- 信息足够后输出 [PHASE_COMPLETE]

## 本轮任务

基于已有回答，提出下一个澄清问题。不要问之前已经问过的。""",

    BrainstormPhase.PROPOSE: """当前阶段: {phase_label} (第{phase}步/共{total}步)

## 用户需求
{collected_info}

## 检索到的数据与文献
{search_results}

## 规则

- 提出 **恰好 2-3 条** 具体可行的思路/方向
- 每条包含: 标题 + 可行性 + 关键文献支撑 [PID_xxx] + 推荐理由
- 推荐其中一条并说明原因
- **最后必须询问用户选择哪条深入**

## 输出格式

### 路径 1: [标题]
- 可行性: 高/中/低
- 支撑: [PID_xxx]
- 理由: [一句话]

### 路径 2: [标题]
...

**推荐:** 路径 X，因为...

请选择一条深入。""",

    BrainstormPhase.PRESENT: """当前阶段: {phase_label} (第{phase}步/共{total}步)

## 选定路径
{selected_path}

## 检索到的数据与文献
{search_results}

## 规则（逐节呈现）

- 当前只呈现 **第 {present_section} 节**（共 {total_sections} 节）
- **禁止一次性呈现所有小节**
- 每节呈现后等待用户确认（"好的"/"继续"）再前进

## 小节顺序
1. 背景与研究现状
2. 候选材料/方法
3. 预期挑战与风险
4. 下一步具体建议""",

    BrainstormPhase.DOCUMENT: """当前阶段: {phase_label} (第{phase}步/共{total}步)

## 待整合的内容

用户需求: {collected_info}
选定路径: {selected_path}
已讨论的小节内容: 前 4 节

## 规则

将所有讨论内容整合为一份**面向用户的计划表**。结构如下:

```markdown
# [研究方向] 研究计划

## 1. 核心问题
[一句话]

## 2. 背景与研究现状
[已有的关键发现 + 文献引用]

## 3. 候选方案
[2-3 条路径对比，含可行性]

## 4. 推荐路径
[详细方案: 方法 → 预期结果 → 风险]

## 5. 下一步行动
[具体的、可执行的步骤清单]
```

## 禁止
- 不要只是重复之前的对话
- 文献必须标注 [PID_xxx]
- 下一步行动必须具体可执行（不是"进一步研究"）""",

    BrainstormPhase.REVIEW: """当前阶段: {phase_label} (第{phase}步/共{total}步)

## 刚生成的计划书内容

{search_results}

## 你的任务 — AI 自审

逐项检查计划书:

| 检查项 | 标准 |
|--------|------|
| 完整性 | 5 个章节都有实际内容，无 "TODO"/"待定" |
| 一致性 | 推荐路径与候选方案分析一致，不自相矛盾 |
| 可执行性 | 下一步行动是具体的、有优先级的、可操作的 |
| 引用准确性 | [PID_xxx] 都指向真实文献，无编造 |

## 规则

1. 如果发现不足，**直接在原文上修改**，然后输出修正后的完整计划书
2. 如果全部合格，在计划书末尾追加 "## ✅ AI 自审通过"
3. 计划书末尾输出 [BRAINSTORM_END]

只输出完整的计划书（修正版或原版+通过标记）。""",
}


# ── 子 Agent Tool 定义 ─────────────────────────────────────────────

BRAINSTORM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_kg",
            "description": "查询超导材料的结构化数据（Tc、压力、λ、ωlog、N(Ef)等物理参数）",
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
            "description": "在超导文献全文数据库中搜索相关文本片段",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询词"
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
    present_section: int = 0
    clarify_rounds: int = 0
    plan_document: str = ""  # Phase 5 生成的计划书

    @property
    def total_phases(self) -> int:
        return 6

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
            "plan_document": self.plan_document,
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
            plan_document=d.get("plan_document", ""),
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
            total=self.total_phases,
            max_clarify=self.max_clarify_rounds,
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

    def check_advance(self, response: str) -> bool:
        """检查是否推进到下一阶段。"""
        if self.phase == BrainstormPhase.EXPLORE:
            # 用户回答了澄清问题后推进
            return True
        elif self.phase == BrainstormPhase.CLARIFY:
            # [PHASE_COMPLETE] 或达到最大轮数
            return "[PHASE_COMPLETE]" in response or self.clarify_rounds >= self.max_clarify_rounds
        elif self.phase == BrainstormPhase.PROPOSE:
            # 用户选择了路径
            return False  # 由外部调用者根据用户输入判断
        elif self.phase == BrainstormPhase.PRESENT:
            # 4 节全部通过
            return self.present_section >= self.total_sections
        elif self.phase == BrainstormPhase.DOCUMENT:
            # 计划书生成完成
            return True
        elif self.phase == BrainstormPhase.REVIEW:
            # 自审完成
            return "[BRAINSTORM_END]" in response
        return False

    def advance_phase(self):
        """推进到下一阶段。"""
        self.phase = BrainstormPhase(self.phase + 1)
        if self.phase == BrainstormPhase.PRESENT:
            self.present_section = 1
        elif self.phase == BrainstormPhase.REVIEW:
            self.present_section = 0


async def run_brainstorm_subagent(
    session: BrainstormSession,
    user_message: str,
    db_context: str,
):
    """Brainstorm 子 Agent 内部循环（async generator）。

    各阶段行为:
    - Phase 1 (EXPLORE): 纯对话，无工具，基于数据库概况提问
    - Phase 2 (CLARIFY): 纯对话，无工具，一次一问
    - Phase 3 (PROPOSE): Function Calling，最多 3 轮搜索
    - Phase 4 (PRESENT): Function Calling，逐节深入搜索
    - Phase 5 (DOCUMENT): Function Calling，补充检索后生成计划书
    - Phase 6 (REVIEW): 纯对话，自审计划书

    Yields:
        {"type": "brainstorm_status"/"status", "data": {"action": str, "message": str}}
        {"type": "result", "data": {"phase": int, "content": str, "search_results": str, "is_complete": bool}}
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

    # ── token 限制 ──
    if session.phase <= BrainstormPhase.CLARIFY:
        phase_max_tokens = 400
    elif session.phase == BrainstormPhase.PROPOSE:
        phase_max_tokens = 1000
    else:
        phase_max_tokens = 2000

    # Phase 1 & 2 & 6: 纯对话，不使用工具
    no_tool_phases = {BrainstormPhase.EXPLORE, BrainstormPhase.CLARIFY, BrainstormPhase.REVIEW}

    if session.phase in no_tool_phases:
        yield {"type": "brainstorm_status", "data": {"action": "thinking", "message": "正在思考分析..."}}

        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            temperature=0.3,
            max_tokens=phase_max_tokens,
        )
        content = response.choices[0].message.content or ""

        # Phase 5 (DOCUMENT) 和 Phase 6 (REVIEW): 保存计划书
        if session.phase == BrainstormPhase.DOCUMENT:
            session.plan_document = content
        elif session.phase == BrainstormPhase.REVIEW:
            session.plan_document = content  # 更新为修正版

        yield {
            "type": "result",
            "data": {
                "phase": int(session.phase),
                "content": content,
                "search_results": session.plan_document if session.phase == BrainstormPhase.REVIEW else "",
                "is_complete": session.check_advance(content),
            }
        }
        return

    # Phase 3 & 4 & 5: Function Calling
    max_rounds = settings.brainstorm_max_agent_rounds
    search_results_parts: list[str] = []

    for _round in range(max_rounds):
        yield {"type": "brainstorm_status", "data": {"action": "thinking", "message": "正在思考分析..."}}

        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            tools=BRAINSTORM_TOOLS,
            temperature=0.3,
            max_tokens=phase_max_tokens,
        )

        choice = response.choices[0]
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
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
            yield {"type": "brainstorm_status", "data": {"action": "generating", "message": "正在生成回答..."}}
            content = choice.message.content or ""

            if session.phase == BrainstormPhase.DOCUMENT:
                session.plan_document = content

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

    # 超过最大轮数，强制生成
    yield {"type": "brainstorm_status", "data": {"action": "generating", "message": "正在汇总生成回答..."}}
    final_response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages + [{"role": "user", "content": "请基于已收集的信息，输出你当前阶段的回答。"}],
        temperature=0.3,
        max_tokens=phase_max_tokens,
    )
    content = final_response.choices[0].message.content or ""
    if session.phase == BrainstormPhase.DOCUMENT:
        session.plan_document = content

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
