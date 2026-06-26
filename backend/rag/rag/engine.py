"""
engine.py — RAG 问答引擎主模块。

完整流程：
用户问题 → 问候检测 → 意图解析 → 并行 KG + RAG → 融合 Prompt → LLM 生成回答
支持对话历史，支持流式输出。
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.rag.config import settings
from backend.rag.rag.prompts import build_rag_prompt, is_greeting, build_fusion_prompt, MAIN_AGENT_SYSTEM_PROMPT
from backend.rag.rag.brainstorm import (
    BrainstormSession,
    BrainstormPhase,
    PHASE_LABELS,
    run_brainstorm_subagent,
)
from backend.rag.rag.reranker import rerank_chunks
from backend.rag.search.engine import search_semantic_only

GREETING_RESPONSE = "你好！我是氢化物超导文献助手，可以问我关于超导材料的问题，例如「LaH10 的超导温度是多少？」或「哪些氢化物 Tc 超过 200K？」"


def _format_db_context(papers: int, superconductors: int, records: int) -> str:
    return f"当前数据库包含 {papers} 篇论文、{superconductors} 种超导体、{records} 条超导数据记录。"


def _try_restore_bs_session(history: list[dict] | None) -> BrainstormSession | None:
    """尝试从对话历史的最后一条 done 事件恢复 brainstorm session。

    前端在 done 事件中会收到 brainstorm 字段，下次请求时以特殊格式传入 history。
    简化实现：检测 history 最后一条消息是否包含 brainstorm 元信息。
    """
    if not history:
        return None
    # 检查最后一条 assistant 消息是否包含 [BRAINSTORM_SESSION] 开头的元信息
    for h in reversed(history):
        if h["role"] == "assistant":
            content = h.get("content", "")
            if content.startswith("[BRAINSTORM_SESSION]"):
                try:
                    data = json.loads(content[len("[BRAINSTORM_SESSION]"):])
                    return BrainstormSession.from_dict(data)
                except (json.JSONDecodeError, KeyError):
                    return None
            break
    return None


def _group_kg_results(results: list[dict]) -> list[dict]:
    """按化合物分组，每组只保留 Tc 最高的记录，并收集 paper_id 列表。

    Args:
        results: KG 查询原始结果（可能多个相同 formula 不同 tc 的条目）

    Returns:
        每组一条记录，包含 paper_ids 聚合列表，按 tc 降序
    """
    groups: dict[str, dict] = {}
    for r in results:
        formula = r["subject"]
        try:
            tc_val = float(r["object"])
        except (ValueError, TypeError):
            tc_val = 0.0
        pid = r.get("paper_id")

        if formula in groups:
            existing = groups[formula]
            existing_tc = float(existing.get("object", "0"))
            if tc_val > existing_tc:
                existing["object"] = r["object"]
                existing["paper_id"] = pid
            if pid and pid not in existing.get("_paper_ids", []):
                existing.setdefault("_paper_ids", []).append(pid)
        else:
            groups[formula] = {
                "subject": formula,
                "predicate": r["predicate"],
                "object": r["object"],
                "paper_id": pid,
                "_paper_ids": [pid] if pid else [],
            }

    grouped = sorted(
        groups.values(),
        key=lambda x: float(x["object"]) if x["object"].replace(".", "", 1).isdigit() else 0,
        reverse=True,
    )
    return grouped


def _extract_intent(question: str) -> dict:
    """用 LLM 提取用户问题中的关键信息，不决策路径。

    Returns:
        {
            "subjects": ["LaH10"],           # 提及的化合物列表
            "predicates": ["超导温度(AD)"],   # 关注的属性
            "intent": "list_overview",       # list_overview | property_query | numeric_compare | mechanism
            "question_type": "factual"       # factual | mechanism | summary
        }
        解析失败时返回默认值。
    """
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)

    _prompt = """分析问题，只返回 JSON。

字段说明：
- subjects: 提到的化合物名称列表，如 ["LaH10", "CaH6"]
- predicates: 关注的属性列表，映射规则：Tc/温度/超导温度→"超导温度(AD)"，压力→"压力"，lambda/电声耦合→"电声耦合lambda"
- intent: 问题意图
  * list_overview: 综述/列举/排序类（"有哪些"、"什么"、"列举"）
  * property_query: 查某化合物属性（"LaH10的Tc"）
  * numeric_compare: 数值比较（"Tc>200"、"压力超过"），需额外提取 operator 和 value
  * mechanism: 机理/原理/原因（"为什么"、"机理"）
- question_type:
  * factual: 事实性/数据性
  * mechanism: 机理/解释性
  * summary: 综述/总结

numeric_compare 时额外输出 operator（">"|"<"|">="|"<="）和 value（数字字符串）。
其他 intent 不输出 operator 和 value。

示例：
问题: "LaH10的Tc是多少"
{"subjects":["LaH10"],"predicates":["超导温度(AD)"],"intent":"property_query","question_type":"factual"}

问题: "超导温度高的超导体有哪些"
{"subjects":[],"predicates":["超导温度(AD)"],"intent":"list_overview","question_type":"factual"}

问题: "为什么H3S有高温超导"
{"subjects":["H3S"],"predicates":[],"intent":"mechanism","question_type":"mechanism"}

问题: "Tc超过200K的超导体"
{"subjects":[],"predicates":["超导温度(AD)"],"intent":"numeric_compare","question_type":"factual","operator":">","value":"200"}

问题: """ + question

    try:
        resp = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "user", "content": _prompt}],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=200,
        )
        result = json.loads(resp.choices[0].message.content)
        return {
            "subjects": result.get("subjects", []),
            "predicates": result.get("predicates", []),
            "intent": result.get("intent", "list_overview"),
            "question_type": result.get("question_type", "factual"),
            "operator": result.get("operator"),
            "value": result.get("value"),
        }
    except Exception:
        return {
            "subjects": [],
            "predicates": [],
            "intent": "list_overview",
            "question_type": "factual",
            "operator": None,
            "value": None,
        }


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


async def ask(
    question: str,
    top_k: int = 15,
    rerank_top_k: int = 5,
    model: str | None = None,
    verbose: bool = False,
    history: list[dict] | None = None,
) -> dict[str, Any]:
    import time as _t
    _t0 = _t.time()

    if is_greeting(question):
        return {"answer": GREETING_RESPONSE, "chunks_used": 0, "chunks": [], "citations": [],
                "model": model or settings.deepseek_model, "source": "greeting"}

    # ── 1. 意图解析 ──
    intent = _extract_intent(question)
    _t1 = _t.time()
    if verbose:
        print(f"[阶段1] 意图解析 ({_t1 - _t0:.1f}s) → intent={intent['intent']} subjects={intent['subjects']}")

    # ── 2. 并行执行 KG + RAG ──
    from backend.rag.knowledge_graph import query as kg_query, get_all_properties

    kg_results: list[dict] = []
    rag_chunks: list[dict] = []

    # KG 查询
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
                        kg_results.append({
                            "subject": subj,
                            "predicate": p["predicate"],
                            "object": p["object"],
                        })
        except Exception as e:
            if verbose:
                print(f"    [KG] 查询异常: {e}")
            kg_results = []

    # RAG 检索（除非意图明确是纯数值查询且 KG 已有结果）
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

    _t2 = _t.time()
    if verbose:
        print(f"[阶段2] KG={len(kg_results)}条 RAG={len(rag_chunks)}块 ({_t2 - _t1:.1f}s)")

    # 按化合物分组 KG 结果（相同 formula 只保留最高 Tc）
    grouped_kg = _group_kg_results(kg_results) if kg_results else []
    if verbose:
        print(f"  [分组] 原始 {len(kg_results)} 条 → 分组后 {len(grouped_kg)} 个化合物")

    # ── 降级判断 ──
    if not kg_results and not rag_chunks:
        return {"answer": "抱歉，在已有文献中没有找到与您问题相关的信息。",
                "chunks_used": 0, "chunks": [], "citations": [],
                "model": model or settings.deepseek_model, "source": "rag"}

    # ── 3. 构造 Prompt ──
    from sqlalchemy import select, func as sa_func
    from backend.rag.database import async_session_factory
    from backend.rag.models import Paper, Superconductor, SuperconductorRecord
    async with async_session_factory() as sess:
        p_cnt = (await sess.execute(sa_func.count(Paper.id))).scalar() or 0
        r_cnt = (await sess.execute(sa_func.count(SuperconductorRecord.id))).scalar() or 0
        s_cnt = (await sess.execute(sa_func.count(Superconductor.id))).scalar() or 0
    db_context = _format_db_context(papers=p_cnt, superconductors=s_cnt, records=r_cnt)

    if grouped_kg and rag_chunks:
        prompt = build_fusion_prompt(question, kg_results=grouped_kg, rag_chunks=rag_chunks,
                                     history=history, db_context=db_context)
        source = "hybrid"
    elif grouped_kg:
        prompt = build_fusion_prompt(question, kg_results=grouped_kg, history=history,
                                     db_context=db_context)
        source = "knowledge_graph"
    else:
        prompt = build_rag_prompt(question, rag_chunks, history=history, db_context=db_context)
        source = "rag"

    if not settings.deepseek_api_key:
        return {"answer": "错误：DEEPSEEK_API_KEY 未配置。", "chunks_used": len(rag_chunks),
                "chunks": rag_chunks, "citations": [], "source": "rag"}

    # ── 4. LLM 生成 ──
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    resp = client.chat.completions.create(
        model=model or settings.deepseek_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=2000,
    )

    _t3 = _t.time()
    if verbose:
        tk = resp.usage
        print(f"[阶段3] LLM 生成 ({_t3 - _t2:.1f}s) → prompt={tk.prompt_tokens}tk output={tk.completion_tokens}tk")

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
                papers_dict[p.id] = {
                    "title": p.title,
                    "doi": p.doi,
                    "journal": p.journal,
                    "year": p.year,
                }

    top10 = [
        {"subject": r["subject"], "predicate": r["predicate"],
         "object": r["object"], "paper_id": r.get("paper_id")}
        for r in grouped_kg[:10]
    ] if kg_results else []

    return {"answer": resp.choices[0].message.content, "chunks_used": len(rag_chunks),
            "chunks": rag_chunks, "citations": [{"paper_id": ch.get("paper_id")} for ch in rag_chunks],
            "model": model or settings.deepseek_model, "source": source,
            "papers": papers_dict, "top10": top10}


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

    # ── Brainstorm: 数据库上下文（提前获取，brainstorm 管线也需要） ──
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
            # Fall through to normal mode
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

            # 流式输出子 Agent 回答
            for char in result["content"]:
                yield {"type": "token", "data": char}

            # 推进阶段
            if result["is_complete"]:
                if bs_session.phase == BrainstormPhase.SUMMARIZE:
                    yield {"type": "brainstorm_exit", "data": {"reason": "completed"}}
                    # 在 done 事件中包含 brainstorm session 用于前端恢复
                    done_data = {
                        "citations": [], "answer": result["content"],
                        "source": "brainstorm", "papers": {}, "top10": [],
                        "brainstorm": bs_session.to_dict(),
                    }
                    # 在 answer 前加上 session 元信息供下次恢复
                    done_data["answer"] = f"[BRAINSTORM_SESSION]{json.dumps(bs_session.to_dict(), ensure_ascii=False)}\n\n{result['content']}"
                    yield {"type": "done", "data": done_data}
                    return

                bs_session.advance_phase()
                yield {
                    "type": "brainstorm_phase",
                    "data": {
                        "phase": int(bs_session.phase),
                        "label": bs_session.phase_label,
                    }
                }

            # done 事件包含 brainstorm session
            done_data = {
                "citations": [], "answer": result["content"],
                "source": f"brainstorm_phase_{int(bs_session.phase)}",
                "papers": {}, "top10": [],
                "brainstorm": bs_session.to_dict(),
            }
            done_data["answer"] = f"[BRAINSTORM_SESSION]{json.dumps(bs_session.to_dict(), ensure_ascii=False)}\n\n{result['content']}"
            yield {"type": "done", "data": done_data}
            return

    # ── 普通模式（以下为现有逻辑，不变） ──
    # ── 1. 意图解析 ──
    intent = _extract_intent(question)

    # ── 2. 并行 KG + RAG ──
    from backend.rag.knowledge_graph import query as kg_query, get_all_properties

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

    # 按化合物分组 KG 结果
    grouped_kg = _group_kg_results(kg_results) if kg_results else []

    if not kg_results and not rag_chunks:
        yield {"type": "token", "data": "抱歉，在已有文献中没有找到与您问题相关的信息。"}
        yield {"type": "done", "data": {"citations": [], "answer": "抱歉，在已有文献中没有找到与您问题相关的信息。", "source": "rag"}}
        return

    # ── 3. Prompt（db_ctx 已在 brainstorm 检测阶段获取） ──

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
