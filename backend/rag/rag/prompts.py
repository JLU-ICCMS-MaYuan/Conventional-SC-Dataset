"""
prompts.py — RAG 系统的 Prompt 模板。
"""

import re

RAG_SYSTEM_PROMPT = """你是一个材料科学专家，专注于超导材料研究。

## 领域背景（你已有的知识）
你是该领域的专家，对氢化物超导有深入的背景理解。例如：
- 氢化物超导体按成分可分为二元（H₃S、LaH₁₀、CaH₆、YH₆）、三元（LaBeH₈、MgIrH₆）、四元（La-Y-Ce-H）等
- 按结构可分为笼形（clathrate，如 LaH₁₀ 的 H₃₂ 笼、CaH₆ 的 H₂₄ 笼）和非笼型
- 按研究手段可分为理论预测（第一性原理 DFT、Eliashberg 方程）和实验验证（金刚石对顶砧 DAC、原位输运测量）
- Tc 计算方法包括 McMillan 公式、Allen-Dynes 修正、各向同性/各向异性 Eliashberg 方程

## 你的任务
根据下面提供的**文献片段**和你的专业知识，用中文回答用户的问题。回答要求：

1. **优先使用文献片段中的具体数据**（Tc、压力、λ 等数值必须使用片段头部的 paper_id 构成 [PID_数字] 引用）
2. **对于分类、概述等背景知识问题**，可以结合你的专业知识回答，但不要编造具体数值
3. 如果提供的片段与问题无关，但仍属于你的专业领域知识，可以基于你的知识回答
4. **每个从片段中引用的数据点必须标注来源**，使用片段头部的 paper_id 构成 [PID_数字] 格式
   （例如，片段头部为 "[来源1] paper_id=74" 时，引用应写 [PID_74]）
   **绝对不要**使用 [来源X] 格式！
5. Tc、压力、λ 等数值必须附带单位
6. **注意对话历史**：如果用户说"具体一点"、"还有呢"、"继续"这类话，
   结合历史理解意图，不要当新问题处理

## 引用格式示例

正确：LaH10 在 200 GPa 下 Fm-3m 结构的 Tc 为 250 K [PID_74]。
正确：目前已知的氢化物超导体有 H₃S、LaH₁₀、CaH₆ 等，其中 LaH₁₀ 的 Tc 约 250 K [PID_74]。
错误：LaH10 的 Tc 为 250 K [来源1]。 ← 严格禁止！

## 以下为文献片段"""


# ── RCS 重排序 ────────────────────────────────────────────────────────────

RERANK_SYSTEM_PROMPT = """你是一个材料科学专家。你的任务是对检索到的文献片段进行相关性评分。

## 评分标准

评分 0-5：
- 5: 直接回答了用户问题，包含明确的数值（Tc、压力、λ 等）
- 4: 与问题高度相关，包含用户问的化合物或现象
- 3: 与问题相关，但信息不够具体
- 2: 部分相关，主要是背景信息
- 1: 微弱相关，只提到化合物名称
- 0: 完全不相关

## 输出格式

返回 JSON 数组，每个元素包含 index（片段编号）和 score（0-5）。
{
  "scores": [{"index": 0, "score": 5, "reason": "直接给出了 LaH10 在 200 GPa 的 Tc 值"}, ...],
  "answerable": true,
  "brief_reason": "片段 0 和 2 直接回答了问题"
}"""


def is_greeting(text: str) -> bool:
    """检测是否为问候语，不触发文献搜索。"""
    text = text.strip().lower()
    greetings = {
        "你好", "您好", "你好吗", "您好吗", "嗨", "hi", "hello",
        "hey", "早上好", "下午好", "晚上好", "大家好",
        "在吗", "在不在", "谢谢", "感谢", "thanks", "thank you",
    }
    return text in greetings


def format_history(history: list[dict]) -> str:
    """将对话历史格式化为文本。"""
    if not history:
        return ""
    parts = []
    for h in history[-4:]:  # 保留最近 4 轮
        role = "用户" if h["role"] == "user" else "你"
        parts.append(f"{role}: {h['content']}")
    return "\n".join(parts)


def build_rag_prompt(
    query: str,
    chunks: list[dict],
    history: list[dict] | None = None,
    db_context: str | None = None,
) -> str:
    """将用户问题 + 对话历史 + 检索结果拼成最终 Prompt。

    Args:
        query: 用户问题
        chunks: 检索到的文本片段列表
        history: 对话历史
        db_context: 数据库概况文字（论文总数、超导体数等）
    """
    context_parts = []
    for i, chunk in enumerate(chunks):
        content = chunk.get("content", "")
        section = chunk.get("section_name", "")
        paper_id = chunk.get("paper_id", "?")
        source_tag = f"[来源{i + 1}]"

        header = f"--- {source_tag} paper_id={paper_id}"
        if section:
            header += f" 章节: {section}"
        header += " ---"

        context_parts.append(f"{header}\n{content}")

    context = "\n\n".join(context_parts)
    history_text = format_history(history) if history else ""

    # 数据库上下文前置
    db_header = f"\n[数据库概况]\n{db_context}\n" if db_context else ""

    if history_text:
        prompt = f"""{RAG_SYSTEM_PROMPT}{db_header}

{context}

---
对话历史:
{history_text}

---
当前用户问题: {query}

请结合对话历史和以上文献片段回答用户问题。"""
    else:
        prompt = f"""{RAG_SYSTEM_PROMPT}{db_header}

{context}

---
用户问题: {query}

请根据以上文献片段回答用户问题。"""

    return prompt


# ── 融合管线 Prompt ─────────────────────────────────────────────────────

FUSION_SYSTEM_PROMPT = """根据下面提供的结构化超导数据和文献片段，用中文回答用户的问题。

## ⚠️ 引用格式（极其重要，必须严格遵守）
**所有引用统一使用 [PID_数字] 格式，禁止使用 [来源X] 或其他格式！**
- 引用结构化数据表格中的数据 → 直接使用表格中已有的 [PID_xxx]（如 [PID_74]）
- 引用文献片段中的内容 → 查看片段头部的 paper_id，使用 [PID_数字] 格式（如 [PID_637]）
- **绝对不要**写成 [来源1]（paper_id=74）或 [来源3] 或 （paper_id=637）这类格式
- **绝对不要**在 [PID_xxx] 后面加括号补充说明

正确示例：
  正确：LaH₁₀ 在 250 GPa 下 Tc 可达 473 K [PID_74]。
  正确：Bowen Jiang 等人的工作表明该方法有效 [PID_637]。
  错误：文献[来源1]（paper_id=74）指出...  ← 严格禁止！
  错误：LaH₁₀ 的 Tc 为 250 K [来源1]。 ← 严格禁止！

## 回答要求
1. 数值直接引用下方表格中的数据，用 [PID_123] 格式标注论文来源
2. 文本解释引用文献片段中的内容，同样用 [PID_数字] 格式标注（查看片段头部的 paper_id）
3. 每个数值必须附带单位（Tc 的单位为 K，压力的单位为 GPa）
4. 注意对话历史：如果用户说"具体一点"、"还有呢"、"继续"，
   结合历史理解意图，不要当新问题处理"""


def build_fusion_prompt(
    query: str,
    kg_results: list[dict] | None = None,
    rag_chunks: list[dict] | None = None,
    history: list[dict] | None = None,
    db_context: str | None = None,
) -> str:
    """构建融合 Prompt：结构化数据 + 文献片段 + 对话历史。

    Args:
        query: 用户问题
        kg_results: KG 查询结果列表，每项含 formula/tc/pressure/paper_id/source_type
        rag_chunks: RAG 检索到的文献片段
        history: 对话历史
        db_context: 数据库概况文字

    Returns:
        完整 Prompt 字符串
    """
    parts = [FUSION_SYSTEM_PROMPT]

    # 数据库概况
    if db_context:
        parts.append(f"\n[数据库概况]\n{db_context}")

    # 结构化数据表格
    if kg_results:
        # 根据 predicate 动态决定列名
        first_pred = kg_results[0].get("predicate", "")
        if "压力" in first_pred:
            col_name = "压力(GPa)"
        elif "lambda" in first_pred or "电声" in first_pred:
            col_name = "λ"
        elif "Tc" in first_pred or "温度" in first_pred or "超导" in first_pred:
            col_name = "Tc(K)"
        else:
            col_name = "数值"
        table_lines = ["\n=== 结构化数据（来自数据库） ==="]
        table_lines.append(f"| 化合物 | {col_name} | 论文ID |")
        table_lines.append("|--------|" + "-" * len(col_name) + "|--------|")
        for r in kg_results:
            formula = r.get("formula", r.get("subject", "?"))
            tc = r.get("tc", r.get("object", ""))
            paper_id = r.get("paper_id")
            pid_str = f"[PID_{paper_id}]" if paper_id else "—"
            table_lines.append(
                f"| {formula} | {tc} | {pid_str} |"
            )
        parts.append("\n".join(table_lines))

    # 文献片段
    if rag_chunks:
        context_parts = ["\n=== 文献片段（来自论文全文） ==="]
        for i, chunk in enumerate(rag_chunks):
            content = chunk.get("content", "")
            section = chunk.get("section_name", "")
            paper_id = chunk.get("paper_id", "?")
            tag = f"[来源{i + 1}]"
            header = f"--- {tag} paper_id={paper_id}"
            if section:
                header += f" 章节: {section}"
            header += " ---"
            context_parts.append(f"{header}\n{content}")
        parts.append("\n".join(context_parts))

    # 对话历史
    if history:
        history_lines = ["\n---", "对话历史:"]
        for h in history[-4:]:
            role = "用户" if h["role"] == "user" else "你"
            history_lines.append(f"{role}: {h['content']}")
        parts.append("\n".join(history_lines))

    parts.append(f"\n---\n当前用户问题: {query}\n")
    parts.append("请结合以上结构化数据和文献片段回答用户问题。")
    return "\n\n".join(parts)


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
