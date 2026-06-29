"""
brainstorm.py — DEPRECATED: 已被 inspiration/ 模块替代。

此模块不再被 engine.py 调用，保留仅用于 git 历史追溯。
新功能请使用 backend.rag.rag.inspiration.* 。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from openai import OpenAI

from backend.rag.config import settings


class BrainstormPhase(IntEnum):
    EXPLORE = 1     # 了解兴趣方向
    CLARIFY = 2     # 追问缩小范围
    PROPOSE = 3     # 提出 2-3 条路径
    PLAN = 4        # 生成研究计划单
    REVIEW = 5      # 自审修正


PHASE_LABELS: dict[int, str] = {
    1: "了解方向",
    2: "追问澄清",
    3: "提出路径",
    4: "生成计划",
    5: "审核定稿",
}

# ── 统一人设（始终不变）────────────────────────────────────────────

PERSONA = """你是氢化物超导领域的学术头脑风暴伙伴。

## 你的能力
你熟悉超导材料数据库中的论文和实验数据。你会在对话中自然地引用数据库中的信息来支撑你的观点，使用 [PID_xxx] 格式标注文献来源。

## 你的风格
- 像一位有经验的导师一样和研究者对话
- 先理解对方的兴趣，再逐步深入
- 当你觉得信息足够时，主动帮对方梳理出可行的研究方向
- 引用数据时自然融入对话，不要像在读表格

## 引用格式
文献引用必须使用 [PID_xxx] 格式。例如："LaH₁₀ 在 250 GPa 下 Tc 达到 286 K [PID_74]。"

## 对话中的数据库资料
用户的第一条消息中包含了数据库检索结果，请充分利用这些资料。"""

# ── 阶段引导（引擎注入用户消息末尾，LLM 看不到标记）─────────────

PHASE_HINTS: dict[BrainstormPhase, str] = {
    BrainstormPhase.EXPLORE:
        "\n\n[系统提示：请先复述你对用户研究方向的理解，然后提一个选择题帮用户缩小范围。]",

    BrainstormPhase.CLARIFY:
        "\n\n[系统提示：用户已回答了上一轮的问题。如果信息还不够具体（方向+约束+指标不足3类），请继续提一个追问。如果信息已经足够，请回复「信息收集完成，我来为你梳理方向。」]",

    BrainstormPhase.PROPOSE:
        "\n\n[系统提示：基于前面的对话和数据库资料，请提出2-3个具体的研究方向。每条包含：方向名称、可行性（高/中/低）、关键文献支撑、推荐理由。最后推荐其中一条并请用户选择。]",

    BrainstormPhase.PLAN:
        "\n\n[系统提示：用户已选定方向。请生成一份结构化研究计划单，包含四个部分：做什么（核心问题）、为什么（背景和价值）、如何做（方法和风险）、分步行动计划（具体可执行步骤）。]",

    BrainstormPhase.REVIEW:
        "\n\n[系统提示：请审核你刚生成的计划单。检查完整性、一致性、可执行性、引用准确性。如有问题请直接修正后输出完整计划单。如无问题请在末尾追加「✅ 自审通过」。]",
}

# ── 引擎判断：阶段是否该推进 ─────────────────────────────────────

def _should_advance(session: BrainstormSession, user_msg: str) -> bool:
    """引擎判断当前阶段是否应该推进到下一阶段。

    不依赖 LLM 输出的标记，而是根据对话状态判断。
    """
    if session.phase == BrainstormPhase.EXPLORE:
        # 用户回答了选择题就推进
        return True

    if session.phase == BrainstormPhase.CLARIFY:
        # 用户说"够了我来梳理"类似的确认 → 推进
        confirm = {"够了", "可以", "梳理", "提出", "来吧", "好的", "差不多了", "OK", "ok", "行"}
        if any(kw in user_msg for kw in confirm):
            return True
        # 达到最大轮数 → 推进
        if session.clarify_rounds >= session.max_clarify_rounds:
            return True
        return False

    if session.phase == BrainstormPhase.PROPOSE:
        # 用户选了路径 → 推进
        return session.selected_path_index is not None

    if session.phase == BrainstormPhase.PLAN:
        # 计划生成后自动推进到审核
        return True

    if session.phase == BrainstormPhase.REVIEW:
        # 审核完成后结束
        return True

    return False


def _detect_path_selection(session: BrainstormSession, user_msg: str):
    """从用户消息检测路径选择。"""
    for i, path in enumerate(session.paths):
        title = path.get("title", "")
        if title and title in user_msg:
            session.selected_path_index = i
            session.selected_path_label = title
            return
    # 数字匹配
    for i in range(1, len(session.paths) + 1):
        if str(i) in user_msg:
            session.selected_path_index = i - 1
            session.selected_path_label = session.paths[i - 1].get("title", f"路径{i}")
            return


# ── 会话状态 ──────────────────────────────────────────────────────

@dataclass
class BrainstormSession:
    """头脑风暴会话状态。"""

    phase: BrainstormPhase = BrainstormPhase.EXPLORE
    user_question: str = ""
    collected_info: list[str] = field(default_factory=list)
    paths: list[dict] = field(default_factory=list)
    selected_path_index: int | None = None
    selected_path_label: str = ""
    clarify_rounds: int = 0
    plan_sheet: str = ""
    rag_data: str = ""

    @property
    def total_phases(self) -> int:
        return 5

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
            "selected_path_index": self.selected_path_index,
            "selected_path_label": self.selected_path_label,
            "clarify_rounds": self.clarify_rounds,
            "plan_sheet": self.plan_sheet,
            "rag_data": self.rag_data,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BrainstormSession":
        session = cls(
            phase=BrainstormPhase(d.get("phase", 1)),
            user_question=d.get("user_question", ""),
            collected_info=d.get("collected_info", []),
            paths=d.get("paths", []),
            selected_path_index=d.get("selected_path_index"),
            selected_path_label=d.get("selected_path_label", ""),
            clarify_rounds=d.get("clarify_rounds", 0),
            plan_sheet=d.get("plan_sheet", ""),
            rag_data=d.get("rag_data", ""),
        )
        if session.selected_path_index is not None and session.paths:
            try:
                session.selected_path_label = session.paths[session.selected_path_index].get("title", "")
            except IndexError:
                session.selected_path_label = ""
        return session

    def check_exit(self, user_response: str) -> bool:
        exit_keywords = {"退出", "不用brainstorm", "不用头脑风暴", "取消", "算了"}
        return any(kw in user_response for kw in exit_keywords)

    def advance_phase(self):
        self.phase = BrainstormPhase(self.phase + 1)


# ── 历史消息构建 ──────────────────────────────────────────────────

def _build_history_messages(collected_info: list[str]) -> list[dict]:
    """将 collected_info 解析为对话历史。"""
    history: list[dict] = []
    for item in collected_info:
        if item.startswith("用户"):
            content = item.split(":", 1)[-1].strip() if ":" in item else item
            history.append({"role": "user", "content": content})
        elif item.startswith("助手"):
            content = item.split(":", 1)[-1].strip() if ":" in item else item
            history.append({"role": "assistant", "content": content})
    return history


# ── 阶段执行 ──────────────────────────────────────────────────────

async def run_brainstorm_turn(
    session: BrainstormSession,
    user_message: str,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """执行一轮头脑风暴对话。

    引擎决定当前阶段，注入对应引导语到用户消息末尾。
    LLM 只需自然对话，不需要输出控制标记。

    Returns:
        {"content": str, "should_advance": bool, "messages_sent": [...]}
    """
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

    # ── 构建 messages ──
    messages: list[dict] = [
        {"role": "system", "content": PERSONA},
    ]

    # 历史对话
    history_msgs = _build_history_messages(session.collected_info)
    messages.extend(history_msgs)

    # 当前用户消息 + 阶段引导（引擎注入，LLM 自然遵循）
    hint = PHASE_HINTS.get(session.phase, "")
    augmented_msg = user_message + hint

    # 去重
    last_is_same = (
        messages
        and messages[-1]["role"] == "user"
        and messages[-1]["content"] == augmented_msg
    )
    if not last_is_same:
        messages.append({"role": "user", "content": augmented_msg})

    messages_sent = [dict(m) for m in messages] if verbose else []

    # ── LLM 调用 ──
    response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        temperature=0.7,  # 稍高温度让对话更自然
        max_tokens=2000,
    )
    content = response.choices[0].message.content or ""

    if session.phase == BrainstormPhase.PLAN:
        session.plan_sheet = content
    elif session.phase == BrainstormPhase.REVIEW:
        session.plan_sheet = content

    result: dict[str, Any] = {
        "content": content,
        "should_advance": _should_advance(session, user_message),
    }
    if verbose:
        result["messages_sent"] = messages_sent
    return result
