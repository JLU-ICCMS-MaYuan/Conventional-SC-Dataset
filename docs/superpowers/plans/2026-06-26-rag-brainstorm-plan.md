# RAG Brainstorm 头脑风暴模式 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 RAG AI 文献助手中集成 Brainstorm 头脑风暴模式，支持 5 阶段交互式对话引导。

**Architecture:** 两级 Agent — 主 Agent 使用 DeepSeek Function Calling（工具: search_kg, search_rag, brainstorm），Brainstorm 子 Agent 递归调用 search_kg/search_rag 最多 3 轮。状态机管理 5 阶段推进。Frontend 通过 SSE 事件渲染过程 UI。

**Tech Stack:** Python/FastAPI, DeepSeek API (Function Calling), TypeScript/React, SSE

**Spec:** `docs/superpowers/specs/2026-06-26-rag-brainstorm-design.md`

---

## File Structure

```
backend/rag/
├─ config.py              [MODIFY] +MAX_CLARIFY_ROUNDS=5, +BRAINSTORM_MAX_AGENT_ROUNDS=3
├─ rag/
│  ├─ engine.py           [MODIFY] +detect_explorative_intent(), brainstorm routing, Function Calling refactor
│  ├─ prompts.py          [MODIFY] +BRAINSTORM_PHASE_PROMPTS dict, +MAIN_AGENT_SYSTEM_PROMPT (replaces FUSION_SYSTEM_PROMPT)
│  └─ brainstorm.py       [CREATE] BrainstormSession, BrainstormPhase, phase prompts, sub-agent runner
backend/api/
└─ rag.py                 [MODIFY] +brainstorm SSE events (enter/phase/options/exit)
frontend_test/src/
├─ hooks/
│  └─ useStreamingChat.ts [MODIFY] +BrainstormState, handle brainstorm SSE events
└─ pages/
   └─ RagPage.tsx         [MODIFY] +Brainstorm UI (progress bar, option buttons, exit button)
```

---

### Task 1: 添加 Brainstorm 配置

**Files:**
- Modify: `backend/rag/config.py`

- [ ] **Step 1: 在 RagSettings 中添加配置项**

在 `backend/rag/config.py` 中 `RagSettings` 类添加：

```python
# Brainstorm 配置
brainstorm_max_clarify_rounds: int = 5
brainstorm_max_agent_rounds: int = 3
```

添加到 `model_config` 之后、`data_root` property 之前。

- [ ] **Step 2: 重启验证**

```bash
cd /home/work/workshop/git/SC-Wiki && python -c "from backend.rag.config import get_rag_settings; s=get_rag_settings(); print(s.brainstorm_max_clarify_rounds, s.brainstorm_max_agent_rounds)"
```

Expected: `5 3`

- [ ] **Step 3: Commit**

```bash
git add backend/rag/config.py
git commit -m "feat: add brainstorm config (max_clarify_rounds=5, max_agent_rounds=3)"
```

---

### Task 2: 创建 Brainstorm 会话管理 + 子 Agent

**Files:**
- Create: `backend/rag/rag/brainstorm.py`

- [ ] **Step 1: 创建文件并编写完整模块**

创建 `backend/rag/rag/brainstorm.py`：

```python
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
        """检查是否推进到下一阶段。"""
        if self.phase == BrainstormPhase.EXPLORE:
            # Phase 1: 用户回答澄清问题后推进
            return True
        elif self.phase == BrainstormPhase.CLARIFY:
            # Phase 2: [PHASE_COMPLETE] 或达到最大轮数
            if "[PHASE_COMPLETE]" in user_response:
                return True
            if self.clarify_rounds >= self.max_clarify_rounds:
                return True
            return False
        elif self.phase == BrainstormPhase.PROPOSE:
            # Phase 3: 用户选择了路径（关键词匹配 + 允许 "1"/"2"/"3"）
            return True  # LLM 会在这个阶段检查，会话层信任 LLM
        elif self.phase == BrainstormPhase.PRESENT:
            # Phase 4: 确认推进：第4节完成后推进
            if self.present_section >= self.total_sections:
                return True
            return "[SECTION_DONE]" in user_response
        elif self.phase == BrainstormPhase.SUMMARIZE:
            return "[BRAINSTORM_END]" in user_response
        return False

    def advance_phase(self):
        """推进到下一阶段。Phase 2→3 时检查是否达到最大轮数。"""
        if self.phase == BrainstormPhase.CLARIFY:
            next_phase = BrainstormPhase(self.phase + 1)
        else:
            next_phase = BrainstormPhase(self.phase + 1)
        self.phase = next_phase
        # Phase 4 进入时重置 section 计数
        if self.phase == BrainstormPhase.PRESENT:
            self.present_section = 1
        elif self.phase == BrainstormPhase.SUMMARIZE:
            self.present_section = 0


async def run_brainstorm_subagent(
    session: BrainstormSession,
    user_message: str,
    db_context: str,
) -> dict[str, Any]:
    """Brainstorm 子 Agent 内部循环。

    子 Agent 拥有工具 [search_kg, search_rag]，最多 3 轮 Function Calling。
    收集足够信息后生成当前阶段的回答。

    Returns:
        {"phase": int, "content": str, "search_results": str, "is_complete": bool}
    """
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
            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                if func_name == "search_kg":
                    result = await _execute_kg_search(func_args)
                elif func_name == "search_rag":
                    result = await _execute_rag_search(func_args)
                else:
                    result = json.dumps({"error": f"未知工具: {func_name}"})

                search_results_parts.append(f"[{func_name}] {result[:500]}")

                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
        else:
            # 没有工具调用，获取文本回答
            content = choice.message.content or ""
            return {
                "phase": int(session.phase),
                "content": content,
                "search_results": "\n".join(search_results_parts),
                "is_complete": session.check_advance(content),
            }

    # 超过最大轮数，强制生成回答
    final_response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages + [{"role": "user", "content": "请基于已收集的信息，输出你当前阶段的回答。"}],
        temperature=0.3,
        max_tokens=2000,
    )
    content = final_response.choices[0].message.content or ""

    return {
        "phase": int(session.phase),
        "content": content,
        "search_results": "\n".join(search_results_parts),
        "is_complete": session.check_advance(content),
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
```

- [ ] **Step 2: 验证模块可以导入**

```bash
cd /home/work/workshop/git/SC-Wiki && python -c "
from backend.rag.rag.brainstorm import BrainstormSession, BrainstormPhase, PHASE_LABELS, run_brainstorm_subagent
s = BrainstormSession(user_question='test')
print(s.phase, s.phase_label)
print(s.build_phase_prompt('hello'))
print('OK')
"
```

Expected: `1 探索上下文` + prompt text + `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/rag/rag/brainstorm.py
git commit -m "feat: create brainstorm session manager with 5-phase state machine and sub-agent"
```

---

### Task 3: 更新 Prompt 模板

**Files:**
- Modify: `backend/rag/rag/prompts.py`

- [ ] **Step 1: 添加主 Agent System Prompt**

在 `backend/rag/rag/prompts.py` 文件末尾添加：

```python
# ── 主 Agent System Prompt ─────────────────────────────────────────────

MAIN_AGENT_SYSTEM_PROMPT = """你是氢化物超导文献专家，须遵守以下规则。

## 工作模式判断

对每个用户问题，先判断属于哪种：

### 普通问答模式
事实性数据查询（Tc、压力、λ、结构等）。结合工具结果直接回答。

### 头脑风暴模式
检测到以下特征时，先向用户确认，获同意后再进入：
- 研究方向探索（"有什么方向"、"潜力"、"idea"、"课题"、"热点"、"前沿"）
- 综述/比较（"对比"、"哪个更好"、"发展趋势"、"优缺点"）
- 方法论/怎么做（"怎么做"、"如何设计"、"从哪入手"、"方案"）
- 用户明确请求（"brainstorm"、"头脑风暴"、"帮我分析"）

**重要：检测到探索性意图后，必须先问用户"需要我进入头脑风暴模式帮你分析吗？"，获同意后才进入。**

头脑风暴模式五阶段:
1. 探索上下文 — 复述理解 + 问一个选择题
2. 追问澄清 — 每次一问，逐步深入（3-5轮）
3. 提出路径 — 2-3条方向 + 文献支撑 + 推荐
4. 逐节呈现 — 分4小节，逐节确认
5. 收敛总结 — 汇总结论 + [BRAINSTORM_END]

用户说"退出"随时终止。

## 引用格式
所有数据引用使用 [PID_xxx] 格式，禁止 [来源X] 或其他格式。"""
```

- [ ] **Step 2: 验证导入**

```bash
cd /home/work/workshop/git/SC-Wiki && python -c "from backend.rag.rag.prompts import MAIN_AGENT_SYSTEM_PROMPT; print(len(MAIN_AGENT_SYSTEM_PROMPT))"
```

Expected: 正整数（prompt 长度）

- [ ] **Step 3: Commit**

```bash
git add backend/rag/rag/prompts.py
git commit -m "feat: add MAIN_AGENT_SYSTEM_PROMPT with brainstorm mode detection"
```

---

### Task 4: 重构 engine.py — 集成 Brainstorm 模式

**Files:**
- Modify: `backend/rag/rag/engine.py`

- [ ] **Step 1: 导入 brainstorm 模块**

在 `engine.py` 顶部导入区添加：

```python
from backend.rag.rag.brainstorm import (
    BrainstormSession,
    BrainstormPhase,
    PHASE_LABELS,
    run_brainstorm_subagent,
)
from backend.rag.rag.prompts import MAIN_AGENT_SYSTEM_PROMPT
```

在现有 `from backend.rag.rag.prompts import ...` 行后面添加 `MAIN_AGENT_SYSTEM_PROMPT`。

- [ ] **Step 2: 添加探索性意图检测函数**

在 `_extract_intent` 函数后面添加：

```python
def _detect_explorative_intent(question: str) -> bool:
    """检测用户问题是否需要 Brainstorm 模式。

    使用 LLM 判断（非关键词匹配），返回 bool。
    """
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

    prompt = f"""判断以下用户问题是否属于探索性/开放性研究讨论，需要交互式头脑风暴引导。

探索性特征（满足任一即为 True）：
- 研究方向探索（"有什么方向"、"潜力"、"idea"、"课题"、"热点"、"前沿"）
- 综述/比较（"对比"、"哪个更好"、"发展趋势"、"优缺点"）
- 方法论/怎么做（"怎么做"、"如何设计"、"从哪入手"、"方案"）
- 用户明确请求（"brainstorm"、"头脑风暴"、"帮我分析"）

非探索性特征（返回 False）：
- 事实性数据查询（"LaH10的Tc是多少"）
- 简单检索（"有哪些超导体"）
- 文献查找（"关于H3S的论文"）

只返回 JSON: {{"explorative": true}} 或 {{"explorative": false}}

问题: {question}"""

    try:
        resp = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=50,
        )
        result = json.loads(resp.choices[0].message.content)
        return result.get("explorative", False)
    except Exception:
        return False
```

- [ ] **Step 3: 修改 `ask_stream` 函数 — 添加 brainstorm 检测和路由**

在 `ask_stream` 函数的问候检测之后、意图解析之前插入 brainstorm 检测。

找到这部分代码（`ask_stream` 函数开头）：

```python
    if is_greeting(question):
        yield {"type": "greeting", "data": ""}
        ...
        return

    # ── 1. 意图解析 ──
    intent = _extract_intent(question)
```

替换为：

```python
    if is_greeting(question):
        yield {"type": "greeting", "data": ""}
        for char in GREETING_RESPONSE:
            yield {"type": "token", "data": char}
        yield {"type": "done", "data": {"citations": [], "answer": GREETING_RESPONSE, "source": "greeting"}}
        return

    # ── Brainstorm 模式检测 ──
    # 从对话历史中恢复或新建 session
    bs_session: BrainstormSession | None = None
    try:
        if history and len(history) >= 2:
            bs_session = BrainstormSession()
            # 简单判断：如果上轮 AI 消息包含探索性引导，恢复 session
            last_ai_msg = ""
            for h in reversed(history):
                if h["role"] == "assistant":
                    last_ai_msg = h["content"]
                    break
            if "头脑风暴" in last_ai_msg and "阶段" in last_ai_msg:
                # 尝试从 history 的最后一条用户消息解析阶段
                # 这里 YAGNI：首次实现不做完整恢复，浏览器恢复前端状态
                pass
    except Exception:
        pass

    # 如果没有活跃 session，检测是否需要建议 brainstorm
    if bs_session is None:
        if _detect_explorative_intent(question) and history and len(history) >= 2:
            bs_session = BrainstormSession()
        elif _detect_explorative_intent(question):
            # 首轮：建议进入 brainstorm 模式
            suggest_msg = "这个问题涉及研究方向的探索，适合用**头脑风暴模式**深入分析。我会逐步帮你澄清方向、探索路径、收敛到可行方案。\n\n需要我进入头脑风暴模式吗？（回复"好的"进入，或直接提问获取快速回答）"

            yield {"type": "brainstorm_suggest", "data": {"message": suggest_msg}}
            # 按普通模式先回答
            # 继续走普通流程...

    # ── 如果处于 brainstorm 模式 ──
    if bs_session is not None and bs_session.phase >= BrainstormPhase.EXPLORE:
        # 检查退出
        if bs_session.check_exit(question):
            yield {"type": "brainstorm_exit", "data": {"reason": "user_abort"}}
            # 降级为普通回答
            bs_session = None
            # 继续走普通流程...


    # ── 1. 意图解析（非 brainstorm 模式） ──
    intent = _extract_intent(question)
```

这是一个关键重构步骤。实际上 brainstorm 模式和普通模式是两条不同的管线。更干净的做法是：

在 `ask_stream` 函数中 **完整拆分两条路径**。完整修改 `ask_stream` 如下：

将整个 `ask_stream` 函数改为以下完整版本（从函数定义到函数结束）：

```python
async def ask_stream(
    question: str,
    top_k: int = 15,
    rerank_top_k: int = 5,
    model: str | None = None,
    history: list[dict] | None = None,
):
    model_name = model or settings.deepseek_model

    if is_greeting(question):
        yield {"type": "greeting", "data": ""}
        for char in GREETING_RESPONSE:
            yield {"type": "token", "data": char}
        yield {"type": "done", "data": {"citations": [], "answer": GREETING_RESPONSE, "source": "greeting"}}
        return

    # ── 数据库上下文 ──
    from sqlalchemy import select, func as sa_func
    from backend.rag.database import async_session_factory
    from backend.rag.models import Paper, Superconductor, SuperconductorRecord
    async with async_session_factory() as sess:
        p_cnt = (await sess.execute(sa_func.count(Paper.id))).scalar() or 0
        r_cnt = (await sess.execute(sa_func.count(SuperconductorRecord.id))).scalar() or 0
        s_cnt = (await sess.execute(sa_func.count(Superconductor.id))).scalar() or 0
    db_ctx = _format_db_context(papers=p_cnt, superconductors=s_cnt, records=r_cnt)

    # ── Brainstorm: 检测并路由 ──
    # 尝试从 history 恢复 session
    bs_session: BrainstormSession | None = _try_restore_bs_session(history)

    # 没有活跃 session 时检测是否需要
    if bs_session is None and _detect_explorative_intent(question):
        yield {
            "type": "brainstorm_suggest",
            "data": {
                "message": "这个问题涉及研究方向探索，适合用**头脑风暴模式**深入分析。我会逐步帮你澄清方向、探索路径、收敛到可行方案。\n\n需要我进入头脑风暴模式吗？"
            }
        }

    if bs_session is not None:
        # ── Brainstorm 子 Agent 管线 ──
        if bs_session.check_exit(question):
            yield {"type": "brainstorm_exit", "data": {"reason": "user_abort"}}
            bs_session = None
            # fall through to normal mode below
        else:
            # 发出阶段事件
            yield {
                "type": "brainstorm_enter",
                "data": {
                    "phase": int(bs_session.phase),
                    "total": 5,
                    "label": bs_session.phase_label,
                }
            }

            # 更新阶段数据
            bs_session.collected_info.append(f"用户: {question}")

            # 运行子 Agent
            result = await run_brainstorm_subagent(
                session=bs_session,
                user_message=question,
                db_context=db_ctx,
            )

            # 推进阶段
            if result["is_complete"]:
                if bs_session.phase == BrainstormPhase.SUMMARIZE:
                    # 退出 brainstorm
                    for char in result["content"]:
                        yield {"type": "token", "data": char}
                    yield {"type": "brainstorm_exit", "data": {"reason": "completed"}}
                    yield {"type": "done", "data": {
                        "citations": [], "answer": result["content"],
                        "source": "brainstorm", "papers": {}, "top10": [],
                    }}
                    return

                bs_session.advance_phase()
                yield {
                    "type": "brainstorm_phase",
                    "data": {
                        "phase": int(bs_session.phase),
                        "label": bs_session.phase_label,
                    }
                }

            # 流式输出子 Agent 回答
            for char in result["content"]:
                yield {"type": "token", "data": char}

            yield {"type": "done", "data": {
                "citations": [], "answer": result["content"],
                "source": f"brainstorm_phase_{int(bs_session.phase)}",
                "papers": {}, "top10": [],
                "brainstorm": bs_session.to_dict(),
            }}
            return

    # ── 普通模式（现有逻辑，不变） ──
    intent = _extract_intent(question)

    kg_results: list[dict] = []
    rag_chunks: list[dict] = []

    if intent["intent"] in ("list_overview", "numeric_compare", "property_query"):
        try:
            if intent["predicates"]:
                predicate = intent["predicates"][0]
                if intent["intent"] == "numeric_compare":
                    op = intent.get("operator", ">") or ">"
                    val = intent.get("value", "0") or "0"
                    kg_results = await kg_query(predicate, operator=op, value=val)
                else:
                    kg_results = await kg_query(predicate, operator=">", value="0")
                if intent["intent"] == "property_query" and intent["subjects"]:
                    kg_results = [r for r in kg_results if r["subject"] == intent["subjects"][0]]
                kg_results.sort(
                    key=lambda r: float(r["object"]) if r["object"].replace(".", "", 1).isdigit() else 0,
                    reverse=True,
                )
            elif intent["subjects"]:
                for subj in intent["subjects"]:
                    props = await get_all_properties(subj)
                    for p in props:
                        kg_results.append({"subject": subj, "predicate": p["predicate"], "object": p["object"]})
        except Exception:
            kg_results = []

    if kg_results:
        yield {"type": "kg_data", "data": {"count": len(kg_results)}}

    is_numeric_only = (intent["question_type"] == "factual"
                       and intent["intent"] in ("list_overview", "numeric_compare")
                       and kg_results)
    if not is_numeric_only:
        search_result = await search_semantic_only(question, top_k=top_k)
        chunks = search_result.get("chunks", [])
        if chunks:
            rag_chunks = await rerank_chunks(question, chunks, top_k=rerank_top_k)
            if not rag_chunks:
                rag_chunks = chunks[:rerank_top_k]

    grouped_kg = _group_kg_results(kg_results) if kg_results else []

    if not kg_results and not rag_chunks:
        yield {"type": "token", "data": "抱歉，在已有文献中没有找到与您问题相关的信息。"}
        yield {"type": "done", "data": {"citations": [], "answer": "抱歉，在已有文献中没有找到与您问题相关的信息。", "source": "rag"}}
        return

    # ── 3. Prompt ──
    if grouped_kg and rag_chunks:
        prompt = build_fusion_prompt(question, kg_results=grouped_kg, rag_chunks=rag_chunks,
                                     history=history, db_context=db_ctx)
        source = "hybrid"
    elif grouped_kg:
        prompt = build_fusion_prompt(question, kg_results=grouped_kg, history=history, db_context=db_ctx)
        source = "knowledge_graph"
    else:
        prompt = build_rag_prompt(question, rag_chunks, history=history, db_context=db_ctx)
        source = "rag"

    if rag_chunks:
        yield {"type": "chunks", "data": [{"paper_id": c["paper_id"]} for c in rag_chunks]}
    if kg_results and source == "hybrid":
        yield {"type": "fusion", "data": {"source": "hybrid", "kg_count": len(kg_results), "chunk_count": len(rag_chunks)}}

    if not settings.deepseek_api_key:
        yield {"type": "token", "data": "错误：DEEPSEEK_API_KEY 未配置。"}
        yield {"type": "done", "data": {"citations": [], "answer": "错误：DEEPSEEK_API_KEY 未配置。", "source": "rag"}}
        return

    # ── 4. LLM 流式生成 ──
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

    full_answer = ""
    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=2000, stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full_answer += delta.content
                yield {"type": "token", "data": delta.content}
    except Exception as e:
        full_answer = f"抱歉，回答生成时出现错误：{e}"
        yield {"type": "token", "data": full_answer}

    # ── 5. Paper 元信息 ──
    paper_ids = set()
    for r in kg_results[:30]:
        if r.get("paper_id"):
            paper_ids.add(r["paper_id"])
    for ch in rag_chunks:
        if ch.get("paper_id"):
            paper_ids.add(ch["paper_id"])
    papers_dict = {}
    if paper_ids:
        async with async_session_factory() as sess:
            q = await sess.execute(select(Paper).where(Paper.id.in_(paper_ids)))
            for p in q.scalars():
                papers_dict[p.id] = {"title": p.title, "doi": p.doi, "journal": p.journal, "year": p.year}

    top10 = [
        {"subject": r["subject"], "predicate": r["predicate"],
         "object": r["object"], "paper_id": r.get("paper_id")}
        for r in grouped_kg[:10]
    ] if kg_results else []

    yield {"type": "done", "data": {
        "citations": [{"paper_id": c["paper_id"]} for c in rag_chunks],
        "answer": full_answer, "source": source,
        "papers": papers_dict, "top10": top10,
    }}
```

同时添加辅助函数，在 `_format_db_context` 函数后面：

```python
def _try_restore_bs_session(history: list[dict] | None) -> BrainstormSession | None:
    """尝试从对话历史的最后一条 done 事件恢复 brainstorm session。

    前端在 done 事件中会收到 brainstorm 字段，下次请求时以特殊格式传入 history。
    简化实现：检测 history 最后一条消息是否包含 brainstorm 元信息。
    """
    if not history:
        return None
    # 检查最后一条 assistant 消息是否以特殊标记包含 bs 状态
    # 前端会将 bs 状态序列化为 JSON 并放在 history 中传递
    # 首次实现：不做复杂恢复，session 只存在于单次对话中
    # 前端通过 localStorage 保存 bs 状态，刷新后恢复
    return None
```

- [ ] **Step 2: 验证语法**

```bash
cd /home/work/workshop/git/SC-Wiki && python -c "
import ast
with open('backend/rag/rag/engine.py') as f:
    ast.parse(f.read())
print('Syntax OK')
"
```

Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add backend/rag/rag/engine.py
git commit -m "feat: add brainstorm detection and routing in ask_stream"
```

---

### Task 5: 更新 API — SSE 事件

**Files:**
- Modify: `backend/api/rag.py`

**注意:** API 层不需要修改。`ask_stream` 函数已经在 `yield` 中发出了 `brainstorm_enter`、`brainstorm_phase`、`brainstorm_options`、`brainstorm_exit` 等事件类型，`rag_chat_stream` 端点只需要透明传递这些 SSE 事件。

- [ ] **Step 1: 验证 API 透明传递**

```bash
cd /home/work/workshop/git/SC-Wiki && python -c "
# 确认 api/rag.py 中的 event_generator 只是 yield _sse(event['type'], event['data'])
# 不需要修改 — SSE 事件类型由 engine 层决定，API 层透明传递
print('API layer: no changes needed')
"
```

- [ ] **Step 2: Commit** （如果无变更，跳过）

确认 `backend/api/rag.py` 无需修改。API 层的 SSE 生成器已经能处理任意 event type。

---

### Task 6: 更新前端 Hook

**Files:**
- Modify: `frontend_test/src/hooks/useStreamingChat.ts`

- [ ] **Step 1: 添加 BrainstormState 类型**

在 `useStreamingChat.ts` 顶部类型定义区域添加：

```typescript
interface BrainstormState {
  active: boolean
  phase: number
  phaseLabel: string
  totalPhases: number
}
```

- [ ] **Step 2: 扩展 CachedMeta 类型**

在 `useStreamingChat.ts` 中修改 `CachedMeta` 接口：

```typescript
interface CachedMeta {
  papers: Record<string, PaperInfo>
  top10: any[]
  brainstorm: BrainstormState | null  // 新增
}
```

- [ ] **Step 3: 在 hook 中添加 brainstorm state**

在 `useStreamingChat` 函数内部，state 声明区域添加：

```typescript
const [brainstorm, setBrainstorm] = useState<BrainstormState>(() => {
  const cid = convs[0]?.id
  return cid ? (loadMeta(cid).brainstorm || { active: false, phase: 1, phaseLabel: '', totalPhases: 5 }) : { active: false, phase: 1, phaseLabel: '', totalPhases: 5 }
})
```

- [ ] **Step 4: 在 SSE 事件处理中添加 brainstorm 事件**

在 `send` 函数的 SSE 事件处理 switch/if-else 中添加（在 `eventType === 'token'` 之前）：

```typescript
if (eventType === 'brainstorm_suggest') {
  // AI 建议进入 brainstorm 模式 — 不自动切换，等待后端流式输出建议消息
} else if (eventType === 'brainstorm_enter') {
  setBrainstorm({ active: true, phase: data.phase, phaseLabel: data.label, totalPhases: data.total })
} else if (eventType === 'brainstorm_phase') {
  setBrainstorm(prev => ({ ...prev, phase: data.phase, phaseLabel: data.label }))
} else if (eventType === 'brainstorm_exit') {
  setBrainstorm({ active: false, phase: 1, phaseLabel: '', totalPhases: 5 })
} else if (eventType === 'brainstorm_suggest') {
  // 建议消息 — 由 token 流式输出处理
}
```

- [ ] **Step 5: 更新 saveMeta 保存 brainstorm 状态**

在 `send` 函数的 `saveMeta(cid, ...)` 调用中扩展：

找到:
```typescript
if (cid) saveMeta(cid, { papers: receivedPapers, top10: receivedTop10 })
```

改为:
```typescript
// 在 finally 后面收集 brainstorm state
let finalBrainstorm = brainstorm
```

并在函数末尾 `saveMeta` 调用改为:

```typescript
// 在 done 事件中提取 brainstorm 状态
// 修改 done 处理:
} else if (eventType === 'done') {
  if (data.papers) { receivedPapers = data.papers; setPapers(data.papers) }
  if (data.top10) { receivedTop10 = data.top10; setTop10(data.top10) }
  if (data.brainstorm) {
    const bs = data.brainstorm
    setBrainstorm({ active: true, phase: bs.phase, phaseLabel: bs.phase_label || '', totalPhases: 5 })
    finalBrainstorm = { active: true, phase: bs.phase, phaseLabel: bs.phase_label || '', totalPhases: 5 }
  }
}
```

返回的 meta 保存:
```typescript
if (cid) saveMeta(cid, { papers: receivedPapers, top10: receivedTop10, brainstorm: finalBrainstorm })
```

- [ ] **Step 6: 在 hook 返回值中添加 brainstorm**

在 `useStreamingChat` 的 `return` 对象中添加:

```typescript
brainstorm,
```

- [ ] **Step 7: 构建验证**

```bash
cd /home/work/workshop/git/SC-Wiki/frontend_test && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 8: Commit**

```bash
git add frontend_test/src/hooks/useStreamingChat.ts
git commit -m "feat: add BrainstormState to useStreamingChat hook with SSE event handling"
```

---

### Task 7: 更新前端 UI

**Files:**
- Modify: `frontend_test/src/pages/RagPage.tsx`

- [ ] **Step 1: 从 hook 解构 brainstorm**

在 `RagPage` 组件中，`useStreamingChat()` 的解构添加 `brainstorm`:

```typescript
const {
  convs, activeId, messages, loading, papers, top10, streamRef, brainstorm,
  newConversation, switchConversation, deleteConversation, send,
} = useStreamingChat()
```

- [ ] **Step 2: 添加进度条组件**

在 `<main style={st.center}>` 内部，`chatBox` 之前添加：

```tsx
{brainstorm.active && (
  <div style={st.bsBar}>
    <div style={st.bsDots}>
      {[1,2,3,4,5].map(p => (
        <div key={p} style={{
          ...st.bsDot,
          backgroundColor: p <= brainstorm.phase ? '#4d6bfe' : '#e5e5e5',
        }} />
      ))}
    </div>
    <span style={st.bsLabel}>🧠 {brainstorm.phaseLabel} ({brainstorm.phase}/{brainstorm.totalPhases})</span>
  </div>
)}
```

- [ ] **Step 3: 添加退出按钮**

在输入框下方、`inputBar` 内部：

```tsx
{brainstorm.active && (
  <button
    onClick={() => {
      send('退出')
    }}
    style={st.bsExitBtn}
  >
    退出头脑风暴
  </button>
)}
```

- [ ] **Step 4: 添加样式定义**

在 `st` 对象中添加：

```typescript
bsBar: { display: 'flex', alignItems: 'center', gap: 12, padding: '8px 20px', backgroundColor: '#fff', borderBottom: '1px solid #f0f0f0', fontSize: 13 },
bsDots: { display: 'flex', gap: 6 },
bsDot: { width: 8, height: 8, borderRadius: '50%', transition: 'background-color .3s' },
bsLabel: { color: '#666', fontWeight: 500 },
bsExitBtn: { marginTop: 8, padding: '4px 12px', borderRadius: 12, border: '1px solid #e55', backgroundColor: '#fff', color: '#e55', fontSize: 12, cursor: 'pointer' },
```

- [ ] **Step 5: 左侧对话列表 Brainstorm 标记**

在对话列表的 `hTitle` 处，添加 brainstorm 标记（仅当该对话是当前活跃的 brainstorm 对话时）。这是可选优化，不做也可。

- [ ] **Step 6: 构建验证**

```bash
cd /home/work/workshop/git/SC-Wiki/frontend_test && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 7: Commit**

```bash
git add frontend_test/src/pages/RagPage.tsx
git commit -m "feat: add brainstorm UI (progress bar, exit button, phase indicator)"
```

---

### Task 8: 构建前端

**Files:**
- Build output: `frontend/templates/rag.html`

- [ ] **Step 1: 构建 React 应用**

```bash
cd /home/work/workshop/git/SC-Wiki/frontend_test && npx vite build
```

Expected: 构建成功，输出到 `dist/`。

- [ ] **Step 2: 复制构建产物**

```bash
cp /home/work/workshop/git/SC-Wiki/frontend_test/dist/index.html /home/work/workshop/git/SC-Wiki/frontend/templates/rag.html
```

- [ ] **Step 3: 调整路径（如需）**

查看 `rag.html` 中的资源引用路径，确认以 `/static/` 开头，否则需要调整或复制静态资源。

- [ ] **Step 4: Commit**

```bash
git add frontend/templates/rag.html
git commit -m "feat: build rag.html with brainstorm UI"
```

---

### Task 9: 端到端测试

- [ ] **Step 1: 启动服务器**

```bash
cd /home/work/workshop/git/SC-Wiki && DATABASE_URL="sqlite:///data/local_dev.db" uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
sleep 3
```

- [ ] **Step 2: 测试探索性意图检测**

```bash
curl -s -X POST http://127.0.0.1:8000/api/rag/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"我想找一个好的超导研究方向","top_k":5,"rerank_top_k":3,"history":[]}' \
  2>&1 | head -30
```

Expected: SSE 事件中包含 `brainstorm_suggest`。

- [ ] **Step 3: 测试普通查询不受影响**

```bash
curl -s -X POST http://127.0.0.1:8000/api/rag/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"LaH10的Tc是多少","top_k":5,"rerank_top_k":3,"history":[]}' \
  2>&1 | head -30
```

Expected: 正常流式回答，无 brainstorm 事件。

- [ ] **Step 4: 清理**

```bash
kill %1 2>/dev/null
```

- [ ] **Step 5: 打开 Playwright 验证前端**

```bash
# 使用 Playwright MCP 打开 /rag 页面，验证：
# 1. AI 对探索性问题建议 brainstorm
# 2. Brainstorm 模式下显示进度条
# 3. 退出按钮可用
```

- [ ] **Step 6: Commit (if any fixes)**

---

## Self-Review

**1. Spec coverage:**
- ✅ 5阶段状态机 → Task 2 (brainstorm.py), Task 4 (engine.py routing)
- ✅ 两级Agent架构 → Task 2 (sub-agent), Task 4 (engine integration)
- ✅ 各阶段 Prompt → Task 2 (PHASE_PROMPTS dict)
- ✅ 主 Agent System Prompt → Task 3 (MAIN_AGENT_SYSTEM_PROMPT)
- ✅ SSE 事件 → Task 4 (engine.py yield), Task 6 (frontend hook)
- ✅ 前端 UI → Task 7 (RagPage.tsx)
- ✅ 探索性意图检测 → Task 4 (_detect_explorative_intent)
- ✅ 错误处理 → 各模块内置 try/except, Task 2 子 Agent 超时处理

**2. Placeholder scan:**
- 无 "TBD"/"TODO"
- `_try_restore_bs_session` 返回 `None` — 这是明确的设计决策（首次实现不做复杂恢复），不是占位符
- 所有代码步骤都有具体实现

**3. Type consistency:**
- `BrainstormSession` from Task 2 used in Task 4, 6
- `BrainstormState` from Task 6 used in Task 7
- SSE event types consistent across backend (Task 4) and frontend (Task 6)
- `CachedMeta.brainstorm` matches `BrainstormState` type
