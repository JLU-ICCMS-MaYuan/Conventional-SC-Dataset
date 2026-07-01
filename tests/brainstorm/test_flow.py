"""
头脑风暴独立测试 —— 纯对话模式。
无阶段概念，用户和 AI 自然交流产生点子。

用法:
    python tests/brainstorm/test_flow.py "笼状氢化物有什么研究方向"
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.rag.rag.brainstorm import (
    BrainstormSession,
    run_brainstorm_turn,
)


async def _fetch_rag_data(question: str) -> str:
    """一次性预取 RAG + KG 数据。"""
    parts = []
    try:
        from backend.rag.knowledge_graph import query as kg_query
        kg = await kg_query("超导温度(AD)", operator=">", value="0")
        if kg:
            top = sorted(kg, key=lambda r: float(r["object"]) if r["object"].replace(".", "", 1).isdigit() else 0, reverse=True)[:15]
            parts.append("【高 Tc 超导体 Top15】")
            for r in top:
                pid = f" [PID_{r['paper_id']}]" if r.get("paper_id") else ""
                parts.append(f"  {r['subject']}: Tc={r['object']}K{pid}")
    except Exception as e:
        parts.append(f"KG 失败: {e}")

    try:
        from backend.rag.search.engine import search_semantic_only
        from backend.rag.rag.reranker import rerank_chunks
        sr = await search_semantic_only(question, top_k=10)
        chunks = sr.get("chunks", [])
        if chunks:
            chunks = await rerank_chunks(question, chunks, top_k=min(5, len(chunks)))
            parts.append("\n【相关文献片段】")
            for c in (chunks or [])[:5]:
                pid = f" [PID_{c['paper_id']}]" if c.get("paper_id") else ""
                parts.append(f"  {c['content'][:300]}{pid}")
    except Exception as e:
        parts.append(f"RAG 失败: {e}")

    return "\n".join(parts) if len(parts) > 2 else "暂无数据"


async def run_full_flow(initial_question: str):
    """纯对话交互测试。输入「退出」结束，输入「总结」生成计划单。"""
    print("🔍 查询数据库...")
    rag_data = await _fetch_rag_data(initial_question)
    print(f"   获取 {len(rag_data)} 字\n")

    first_msg = f"{initial_question}\n\n数据库资料:\n{rag_data}"
    session = BrainstormSession(user_question=initial_question, rag_data=rag_data)
    session.collected_info.append(f"用户: {first_msg}")
    user_msg = first_msg

    print("=" * 60)
    print("🧠 头脑风暴测试（纯对话模式）")
    print("   输入「退出」结束，输入「总结」生成研究计划")
    print("=" * 60)

    while True:
        result = await run_brainstorm_turn(
            session=session,
            user_message=user_msg,
            verbose=True,
        )

        content = result["content"]

        # 打印发送的消息
        if "messages_sent" in result:
            print("\n" + "-" * 30)
            print("📤 发送给 LLM:")
            for i, msg in enumerate(result["messages_sent"]):
                role = msg["role"]
                body = msg["content"]
                if len(body) > 250:
                    body = body[:250] + f"...({len(body)}字)"
                print(f"  [{i}] {role}: {body}")
            print("-" * 30)

        print(f"\n🤖 助手:\n{content}\n")

        session.collected_info.append(f"助手: {content}")

        if session.check_exit(user_msg):
            print("👋 退出")
            break

        print("-" * 40)
        user_msg = input("👤 你: ").strip()
        if not user_msg:
            user_msg = "继续"

        if session.check_exit(user_msg):
            print("👋 退出")
            break

        session.collected_info.append(f"用户: {user_msg}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("研究方向: ").strip() or "笼状氢化物有什么研究方向"

    asyncio.run(run_full_flow(question))
