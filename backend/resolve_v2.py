"""
论文关系匹配 v2 — 用 paper_summaries 向量集合替代 RAG chunk 搜索。
需要先运行 build_summary_index.py 建立 paper_summaries Chroma 集合。
"""
import json
import os
import re
import sqlite3
import sys

DB_PATH = "/home/work/workshop/git/SC-Wiki-modules/dev.db"
COLLECTION_NAME = "paper_summaries"

sys.path.insert(0, "/home/work/workshop/git/SC-Wiki-modules")
from backend.rag.ingest.embedder import embed_texts
from backend.rag.vectordb import _get_collection


def search_paper_by_summary(description: str, top_k: int = 10) -> list[int]:
    """向量搜索 paper_summaries，返回 paper_id 列表。"""
    query_vec = embed_texts([description])[0]
    col = _get_collection(COLLECTION_NAME)
    results = col.query(
        query_embeddings=[query_vec],
        n_results=top_k,
        include=["metadatas", "distances"],
    )
    if not results["ids"] or not results["ids"][0]:
        return []
    return [int(pid) for pid in results["ids"][0]]


def fetch_profiles(paper_ids: list[int]) -> dict[int, dict]:
    """从 dev.db 读取论文 Profile（summary + keywords + title + paper_type）。"""
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" for _ in paper_ids)
    rows = conn.execute(
        f"SELECT id, title, summary, keywords_tags, paper_type FROM papers WHERE id IN ({placeholders})",
        paper_ids,
    ).fetchall()
    conn.close()

    profiles = {}
    for pid, title, summary, keywords, paper_type in rows:
        kw_list = []
        if keywords:
            try:
                kw_list = json.loads(keywords)
            except (json.JSONDecodeError, TypeError):
                pass
        profiles[pid] = {
            "paper_id": pid,
            "title": title or "",
            "summary": summary or "",
            "keywords": kw_list,
            "paper_type": paper_type or "",
        }
    return profiles


PROFILE_MATCH_PROMPT = """你是超导材料专家。下面描述了一篇论文的研究内容，以及几篇候选论文的Profile。
请选出最匹配的候选论文。

## 目标论文描述
{description}

## 候选论文 Profile
{candidates}

返回 JSON: {{"best_match": paper_id (整数, 不是索引), "confidence": 0-10, "reason": "判断依据"}}
如果都不匹配返回 {{"best_match": 0, "confidence": 0, "reason": "无匹配"}}

## 匹配要点
- 优先比对材料体系（候选Profile的summary和keywords中是否包含描述中的材料名/化学式）
- 其次对比研究方法和结论
- 综述(review/综述)应排除
- 描述中的"文献[N]"、"[N]"等引用编号忽略"""


def resolve_one_paper(description: str, top_k: int = 10) -> dict | None:
    """用新方法解析论文身份：向量搜 summary → 读 Profile → LLM 比对。

    Returns:
        {"paper_id": int, "match_method": "summary_verified"} 或 None
    """
    from extract_relations import deepseek  # 复用已有的 LLM 调用

    # 1. 向量搜索
    paper_ids = search_paper_by_summary(description, top_k=top_k)
    if not paper_ids:
        print(f"    [V2] 无候选", file=sys.stderr)
        return None

    # 2. 读取 Profile
    profiles = fetch_profiles(paper_ids)
    if not profiles:
        return None

    # 3. 构建候选文本
    candidate_text = "\n".join(
        f"paper_id={p['paper_id']}\n"
        f"  标题: {p['title'][:150]}\n"
        f"  摘要: {p['summary'][:300]}\n"
        f"  关键词: {', '.join(p['keywords'][:10])}\n"
        for p in profiles.values()
    )

    safe_desc = description.replace("{", "{{").replace("}", "}}")
    safe_cand = candidate_text.replace("{", "{{").replace("}", "}}")
    prompt = PROFILE_MATCH_PROMPT.format(description=safe_desc, candidates=safe_cand)

    try:
        text = deepseek(prompt, max_tokens=500)
        m = re.search(r'"best_match"\s*:\s*(\d+)', text)
        if m:
            pid = int(m.group(1))
            if pid in profiles:
                print(f"    [V2] → paper_{pid} ({profiles[pid]['title'][:50]})", file=sys.stderr)
                return {"paper_id": pid, "match_method": "summary_verified"}
            elif pid == 0:
                print(f"    [V2] 无匹配 (best_match=0)", file=sys.stderr)
        else:
            print(f"    [V2] 解析失败: ...{text[-80:]}", file=sys.stderr)
    except Exception as e:
        print(f"    [V2] LLM异常: {e}", file=sys.stderr)

    return None


def resolve_with_fallback(description: str) -> dict | None:
    """先尝试 V2（summary搜索），失败则回退到 V1（RAG chunk搜索）。"""
    result = resolve_one_paper(description)
    if result:
        return result

    print(f"    [V2] 回退到 V1...", file=sys.stderr)
    from extract_relations import resolve_one_paper as resolve_v1

    return resolve_v1(description, description.split()[:5])  # fallback
