"""
论文关系提取 v2 — 自然语言描述 + RAG多路搜索 + MySQL摘要 + LLM二次验证
用法: python backend/extract_relations.py [paper.md | 综述目录]
输出: /home/work/workshop/bak/knowledge_graph.json
"""
import json, os, re, sys, time
from collections import Counter

import requests

# V2 匹配：用 paper_summaries 向量搜索替代 RAG chunk 搜索
try:
    from resolve_v2 import resolve_one_paper as _resolve_v2
except ImportError:
    _resolve_v2 = None

OUTPUT_FILE = "/home/work/workshop/bak/knowledge_graph.json"
API = "http://localhost:8000"
MINERU_REVIEW_DIR = "/home/work/workshop/bak/HydrideLiteratureData/mineru/综述"

RELATION_WEIGHTS = {
    "first_discovery": 0.9, "experimental_validation": 0.9,
    "theoretical_basis": 0.8, "correction_or_dispute": 0.7,
    "development_extension": 0.6, "material_system_extension": 0.6,
    "same_research_direction": 0.5, "supporting_evidence": 0.4,
}

MATCH_PROMPT = """下面是一篇目标论文的研究内容描述，以及从数据库搜到的几篇候选论文。
请判断哪篇候选论文最可能是描述所指的论文。

## 重要提示
- 描述中的"文献[N]"、"Ref. [N]"等编号请忽略，那是原文的引用编号，无法用于匹配
- 请根据描述中的**研究内容**（材料体系、方法、发现、结论）与候选摘要进行匹配
- 如果描述涉及具体的材料（如 YC2、LaH10）、方法（如比热容测量）、结论（如 Tc=250K），优先匹配包含相同信息的候选
- **材料体系必须匹配**：描述说研究YC2的比热容，候选也必须涉及YC2或同类碳化物超导体，不能匹配到研究氢化物或MgB2等不同体系的论文
- 即使不能完全确定，只要有明显的内容重叠，就应该给出最佳匹配
- 综述(Review)、博士/硕士论文(Thesis/Dissertation)应排除

## 目标论文描述
{description}

## 候选论文
{candidates}

返回 JSON: {{"best_match": 1-based-index, "confidence": 0-10, "reason": "判断依据"}}
如果所有候选材料体系或研究内容都不匹配，返回 {{"best_match": 0, "confidence": 0, "reason": "无匹配"}}"""


# ════════════════════════════════════════════

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def deepseek(prompt: str, max_tokens: int = 4096) -> str:
    load_env()
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("请设置 DEEPSEEK_API_KEY")
    resp = requests.post("https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.1, "max_tokens": max_tokens}, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek API {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    msg = data.get("choices", [{}])[0].get("message", {})
    content = msg.get("content", "") or msg.get("reasoning_content", "")
    if not content:
        raise RuntimeError(f"DeepSeek 返回空内容: {json.dumps(data, ensure_ascii=False)[:300]}")
    return content


# ════════════════════════════════════════════
# 1. LLM 提取关系（自然语言描述版）
# ════════════════════════════════════════════

SECTION_PROMPT = """你是超导领域文献分析专家。下面是一篇论文的「{section_name}」章节。
提取该章节中描述的论文间关系。如果本段没有描述任何论文间关系，返回空数组 []。

## 要求
- 本文自身不作为 source 或 target
- source 和 target 都必须包含 author_info 和 search_queries
- search_queries 搜索的是论文自身的学术内容（材料体系、发现结论、研究方法），不是别人对它的描述
  错误示例: "Peng predicted LaH10" （这是引用者视角）
  正确示例: "LaH10 fcc superconductor electron-phonon coupling 275 K 210 GPa" （这是论文自身内容）
- author_info 延续自然语言描述
- 每个关系必须有 evidence（原文中直接描述该关系的句子）
- confidence 是对该关系确信程度的 0-10 分

## 输出格式（严格JSON）
[
  {{
    "source": {{"author_info": "作者, 年份, 研究了什么", "search_queries": ["关键词1", "关键词2", "关键词3"]}},
    "target": {{"author_info": "作者, 年份, 研究了什么", "search_queries": ["关键词1", "关键词2", "关键词3"]}},
    "relation_type": "experimental_validation",
    "relation_label": "实验验证",
    "evidence": "从正文中摘录的描述该关系的原句",
    "confidence": 8
  }}
]

## 关系类型
{relation_types}

## {section_name} 章节文本
{section_text}"""


def extract_relations(body_text: str) -> list[dict]:
    """按章节分段提取，合并去重"""
    # 按 ## 标题分割
    sections = re.split(r"\n(?=## )", body_text)
    all_relations = []

    for section in sections:
        section = section.strip()
        if len(section) < 200:
            continue
        # 取章节名
        heading_match = re.match(r"## (.+)", section)
        section_name = heading_match.group(1).strip() if heading_match else "正文"
        if section_name.lower() in ("references", "acknowledgments", "author information", "funding"):
            continue

        print(f"    分析 [{section_name}] ({len(section)}字符)...", file=sys.stderr)
        safe = section.replace("{", "{{").replace("}", "}}")
        prompt = SECTION_PROMPT.format(
            section_name=section_name,
            relation_types="\n".join(f"- {k}: {v}" for k, v in RELATION_WEIGHTS.items()),
            section_text=safe[:4000],
        )
        try:
            text = deepseek(prompt, max_tokens=2048)
            for pattern in [r"\[[\s\S]*\]", r"```json\s*([\s\S]*?)```", r"```\s*([\s\S]*?)```"]:
                m = re.search(pattern, text)
                if m:
                    rels = json.loads(m.group(1) if m.lastindex else m.group(0))
                    all_relations.extend(rels)
                    print(f"      → {len(rels)} 条", file=sys.stderr)
                    break
            else:
                clean = re.sub(r"```\w*\s*", "", text).strip()
                rels = json.loads(clean)
                all_relations.extend(rels)
        except Exception as e:
            print(f"      ✗ {e}", file=sys.stderr)
            continue

    # 补全缺失字段
    RELATION_LABELS = {
        "first_discovery": "首次发现", "experimental_validation": "实验验证",
        "theoretical_basis": "理论基础", "correction_or_dispute": "修正或争议",
        "development_extension": "发展延续", "material_system_extension": "材料体系扩展",
        "same_research_direction": "同方向里程碑", "supporting_evidence": "支撑证据",
    }
    for r in all_relations:
        if not r.get("relation_label"):
            r["relation_label"] = RELATION_LABELS.get(r.get("relation_type", ""), r.get("relation_type", "未知"))
        if not r.get("confidence"):
            r["confidence"] = 5

    # 去重：基于 source + target 作者信息 + 关系类型
    seen = set()
    unique = []
    for r in all_relations:
        src_info = (r.get("source", {}) if isinstance(r.get("source"), dict) else {}).get("author_info", "")
        tgt_info = (r.get("target", {}) if isinstance(r.get("target"), dict) else {}).get("author_info", "")
        # 取前 60 字符做 key，忽略细微差异
        key = (src_info[:60], tgt_info[:60], r.get("relation_type", ""))
        if key not in seen:
            seen.add(key)
            unique.append(r)
        else:
            # 保留 confidence 更高的那条
            existing = next(u for u in unique if (u["source"]["author_info"][:60], u["target"]["author_info"][:60], u.get("relation_type","")) == key)
            if r.get("confidence", 0) > existing.get("confidence", 0):
                idx = unique.index(existing)
                unique[idx] = r
    print(f"    合并: {len(all_relations)} → {len(unique)} (去重)", file=sys.stderr)
    return unique


# ════════════════════════════════════════════
# 2. 多路 RAG 搜索 + 投票
# ════════════════════════════════════════════
# 搜索范围：paper_chunks(全量) + 专题collections，Chroma层过滤综述
SEARCH_COLLECTIONS = [
    "paper_chunks",  # 全量论文，搜得最全
    "theoretical_chunks", "experimental_chunks",
    "mechanism_chunks", "solid_hydrogen_chunks",
    "anharmonic_chunks",
]


def _get_review_paper_ids() -> set[int]:
    """从 Chroma review_chunks 获取综述论文 paper_id（缓存）"""
    if hasattr(_get_review_paper_ids, "_cache"):
        return _get_review_paper_ids._cache
    try:
        from backend.rag.vectordb import _get_collection, REVIEW_COLLECTION_NAME
        col = _get_collection(REVIEW_COLLECTION_NAME)
        result = col.get(include=['metadatas'])
        ids = {int(m['paper_id']) for m in result['metadatas']}
    except Exception:
        ids = set()
    _get_review_paper_ids._cache = ids
    return ids


def search_paper(queries: list[str]) -> tuple[list[int], dict[int, list[str]]]:
    """多 query 多 collection 语义搜索，embedding 一次、搜全部 collection。
    返回 (排序后的 paper_id 列表, {paper_id: [原文chunk内容, ...]})"""
    # 确保项目根目录在 sys.path（rag 模块内部用 from backend.rag... 导入）
    _proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _proj_root not in sys.path:
        sys.path.insert(0, _proj_root)
    from backend.rag.ingest.embedder import embed_texts
    from backend.rag.vectordb import _get_collection

    review_ids = _get_review_paper_ids()
    paper_scores: Counter = Counter()
    chunks_by_paper: dict[int, list[str]] = {}
    errors = 0

    for q in queries[:5]:
        # 1. embedding（所有 collection 共用）
        try:
            query_vec = embed_texts([q])[0]
        except Exception as e:
            errors += 1
            print(f"    Embedding失败: {e}", file=sys.stderr)
            continue

        # 2. 搜索所有 collection
        for col_name in SEARCH_COLLECTIONS:
            try:
                col = _get_collection(col_name)
                if col.count() == 0:
                    continue
                results = col.query(
                    query_embeddings=[query_vec],
                    n_results=5,
                    include=["documents", "metadatas", "distances"],
                )
                if not results["ids"] or not results["ids"][0]:
                    continue
                for i in range(len(results["ids"][0])):
                    pid_str = results["metadatas"][0][i].get("paper_id", "")
                    if not pid_str:
                        continue
                    pid = int(pid_str)
                    if pid in review_ids:
                        continue  # 排除综述
                    paper_scores[pid] += 1
                    content = (results["documents"][0][i] or "")[:500].strip()
                    if pid not in chunks_by_paper:
                        chunks_by_paper[pid] = []
                    if content and content not in chunks_by_paper[pid]:
                        chunks_by_paper[pid].append(content)
            except Exception:
                continue

    if errors >= len(queries[:5]):
        print(f"    ⚠ 所有 embedding 请求均失败", file=sys.stderr)

    sorted_ids = [pid for pid, _ in paper_scores.most_common(5)]
    return sorted_ids, chunks_by_paper


# ════════════════════════════════════════════
# 3. MySQL 查摘要 + LLM 二次验证
# ════════════════════════════════════════════

def fetch_abstracts(paper_ids: list[int]) -> dict[int, str]:
    """查数据库获取论文信息：优先摘要，没有则用标题+期刊+年份"""
    results = {}
    for pid in paper_ids[:5]:
        try:
            resp = requests.get(f"{API}/api/papers/{pid}", timeout=15)
            if resp.ok:
                data = resp.json()
                abst = data.get("abstract", "") or ""
                if len(abst) > 50:
                    results[pid] = abst
                else:
                    # 用标题+期刊+年份拼一个描述
                    title = data.get("title", "") or ""
                    journal = data.get("journal", "") or ""
                    year = data.get("year", "") or ""
                    parts = [p for p in [title, journal, str(year)] if p]
                    results[pid] = " | ".join(parts)
        except Exception:
            continue
    return results


def fetch_meta(paper_ids: list[int]) -> dict[int, dict]:
    """批量获取论文元信息 {pid: {title, year}}"""
    results = {}
    for pid in paper_ids[:10]:
        try:
            resp = requests.get(f"{API}/api/papers/{pid}", timeout=10)
            if resp.ok:
                d = resp.json()
                results[pid] = {"title": d.get("title", "") or "", "year": d.get("year")}
        except Exception:
            continue
    return results


def _extract_year(text: str) -> int | None:
    """从描述文本中提取年份"""
    import re as _re
    # "2014年" / "2014," / "in 2014" / "(2014)" / "Drozdov, 2015,"
    m = _re.search(r'(?:^|\s|[,.(])(\d{4})(?:$|\s|[,.)]|年)', text)
    if m:
        y = int(m.group(1))
        if 1900 <= y <= 2030:
            return y
    # 纯数字 "2014"
    m = _re.search(r'\b(19\d{2}|20\d{2})\b', text)
    if m:
        return int(m.group(1))
    return None


def fetch_titles(paper_ids: list[int]) -> dict[int, str]:
    """批量获取论文标题（兼容旧接口）"""
    meta = fetch_meta(paper_ids)
    return {pid: m["title"] for pid, m in meta.items() if m["title"]}


TITLE_MATCH_PROMPT = """你是超导材料专家。下面描述了一篇论文的研究内容，以及几篇候选论文的标题。
请选出**所有标题与研究内容中提到的化合物/材料体系相关的候选**（可多选）。

## 目标论文描述
{description}

## 候选论文标题
{candidates}

返回 JSON: {{"matches": [1-based-index, ...], "reason": "判断依据"}}
如果所有标题都与描述中的化合物/材料无关，返回 {{"matches": [], "reason": "无匹配"}}"""


ABSTRACT_MATCH_PROMPT = """下面是一篇目标论文的研究内容描述，以及几篇通过标题初筛的候选论文摘要。
请判断哪篇候选论文最可能是描述所指的论文。

## 重要提示
- 描述中的"文献[N]"、"Ref. [N]"等编号请忽略
- 根据研究内容（材料体系、方法、发现、结论）与摘要匹配
- 材料体系必须匹配：描述说研究YC2比热容，候选也必须涉及YC2或同类碳化物
- 综述(Review)、博士/硕士论文应排除

## 目标论文描述
{description}

## 候选论文
{candidates}

返回 JSON: {{"best_match": 1-based-index, "confidence": 0-10, "reason": "判断依据"}}
如果都不匹配返回 {{"best_match": 0, "confidence": 0, "reason": "无匹配"}}"""


def llm_match(description: str, candidates: dict[int, str], queries: list[str] | None = None,
              skip_titles: bool = False) -> int | None:
    """两阶段匹配：标题筛 → 摘要定。
    skip_titles=True 时跳过标题筛选直接做内容匹配（chunks fallback用）"""
    if not candidates:
        return None

    enriched = description
    if queries:
        enriched = f"{description}\n研究关键词: {', '.join(queries[:3])}"

    titles = {}
    if not skip_titles:
        # ── 阶段0: 年份筛选 ──
        n_before = len(candidates)
        target_year = _extract_year(enriched)
        if target_year:
            meta = fetch_meta(list(candidates.keys()))
            year_filtered = {}
            for pid, m in meta.items():
                paper_year = m.get("year")
                if paper_year and abs(paper_year - target_year) <= 2:
                    year_filtered[pid] = m["title"]
            if year_filtered:
                before = len(candidates)
                candidates = {pid: candidates[pid] for pid in year_filtered if pid in candidates}
                titles = {pid: year_filtered[pid] for pid in candidates if pid in year_filtered}
                if len(candidates) < before:
                    print(f"      [年份] {target_year}±2 ({before}→{len(candidates)})", file=sys.stderr)
            else:
                print(f"      [年份] {target_year}±2 → 0, 跳过过滤", file=sys.stderr)

        if not titles:
            titles = fetch_titles(list(candidates.keys()))

        # ── 阶段1: 标题筛选 ──
        if titles:
            title_text = "\n".join(
                f"[{i+1}] paper_id={pid}\n{titles[pid][:200]}\n"
                for i, (pid, _) in enumerate(candidates.items()) if pid in titles
            )
            if title_text:
                safe_desc = enriched.replace("{", "{{").replace("}", "}}")
                safe_titles = title_text.replace("{", "{{").replace("}", "}}")
                prompt = TITLE_MATCH_PROMPT.format(description=safe_desc, candidates=safe_titles)
                try:
                    text = deepseek(prompt, max_tokens=1024)
                    m = re.search(r'"matches"\s*:\s*\[([^\]]*)\]', text)
                    if m:
                        indices = [int(x.strip()) for x in m.group(1).split(",") if x.strip().isdigit()]
                        matching_ids = [list(candidates.keys())[i-1] for i in indices if 1 <= i <= len(candidates)]
                        if matching_ids:
                            names = ", ".join(
                                f"paper_{pid}({titles.get(pid, '?')[:50]})"
                                for pid in matching_ids
                            )
                            print(f"      [标题] {names} ({n_before}→{len(matching_ids)})", file=sys.stderr)
                            candidates = {pid: candidates[pid] for pid in matching_ids if pid in candidates}
                        else:
                            print(f"      [标题] 0/{n_before}", file=sys.stderr)
                            return None
                    else:
                        print(f"      [标题] 解析失败, 原文末100字: ...{text[-100:]}", file=sys.stderr)
                except Exception as e:
                    print(f"      [标题] 异常: {e}", file=sys.stderr)

    if not candidates:
        return None

    stage_label = "[内容]" if skip_titles else "[摘要]"
    candidate_text = "\n".join(
        f"[{i+1}] paper_id={pid}\n{abst[:600]}\n"
        for i, (pid, abst) in enumerate(candidates.items())
    )

    safe_desc = enriched.replace("{", "{{").replace("}", "}}")
    safe_cand = candidate_text.replace("{", "{{").replace("}", "}}")
    prompt = ABSTRACT_MATCH_PROMPT.format(description=safe_desc, candidates=safe_cand)
    try:
        text = deepseek(prompt, max_tokens=1024)
        m = re.search(r'"best_match"\s*:\s*(\d+)', text)
        if m:
            idx = int(m.group(1))
            if idx > 0 and idx <= len(candidates):
                pid = list(candidates.keys())[idx - 1]
                title_hint = titles.get(pid, "")[:50] if titles else ""
                print(f"      {stage_label} → paper_{pid}({title_hint})", file=sys.stderr)
                return pid
            else:
                print(f"      {stage_label} best_match=0", file=sys.stderr)
        else:
            print(f"      {stage_label} 解析失败, 原文末: ...{text[-80:]}", file=sys.stderr)
    except Exception as e:
        print(f"      {stage_label} 异常: {e}", file=sys.stderr)
    return None


def llm_match_with_chunks(description: str, chunks_by_paper: dict[int, list[str]], queries: list[str] | None = None) -> int | None:
    """用 RAG 返回的原文 chunks 作为候选文本进行 LLM 匹配（摘要匹配失败时的 fallback）"""
    if not chunks_by_paper:
        return None
    candidates = {}
    for pid, contents in chunks_by_paper.items():
        candidates[pid] = "\n---\n".join(contents[:3])
    return llm_match(description, candidates, queries, skip_titles=True)


def resolve_one_paper(author_info: str, search_queries: list[str]) -> dict | None:
    """MySQL + LLM 确定一篇论文的身份"""
    # B: 多路搜索 + 投票
    top_ids, chunks_by_paper = search_paper(search_queries)
    if not top_ids:
        return None

    # MySQL: 查摘要
    abstracts = fetch_abstracts(top_ids)
    if not abstracts:
        # 没摘要或所有候选都是综述/博士论文
        return {"paper_id": top_ids[0], "match_method": "rag_only"}

    # LLM: 二次验证（摘要）
    matched = llm_match(author_info, abstracts, search_queries)
    if not matched:
        print(f"      [摘要] 无匹配, chunks再试", file=sys.stderr)
        matched = llm_match_with_chunks(author_info, chunks_by_paper, search_queries)
        if not matched:
            print("      [内容] 无匹配, fallback rag_first", file=sys.stderr)

    if matched:
        return {
            "paper_id": matched,
            "abstract": abstracts.get(matched, "")[:500],
            "match_method": "llm_verified",
            "candidates": top_ids,
        }

    # 没有 LLM 匹配，返回第一候选
    return {
        "paper_id": top_ids[0],
        "match_method": "rag_first",
        "candidates": top_ids,
    }


# ════════════════════════════════════════════
# 4. 重要性评分
# ════════════════════════════════════════════

def calc_importance(relations: list[dict], body_text: str) -> list[dict]:
    body_lower = body_text.lower()
    total = len(body_lower)
    front, back = body_lower[:int(total * 0.2)], body_lower[int(total * 0.8):]

    for rel in relations:
        evidence = rel.get("evidence", "")
        count = body_text.count(evidence[:50]) if evidence else 1
        freq = min(count / 5 + (0.2 if evidence and evidence[:50] in front else 0)
                   + (0.2 if evidence and evidence[:50] in back else 0), 1.0)
        weight = RELATION_WEIGHTS.get(rel.get("relation_type", ""), 0.3)
        matched = bool(rel.get("source", {}).get("paper_id")) and bool(rel.get("target", {}).get("paper_id"))
        quality = ((rel.get("confidence", 5) or 0) / 10) * (1.0 if matched else 0.3)
        rel["importance"] = round(freq * 0.3 + weight * 0.4 + quality * 0.3, 3)

    relations.sort(key=lambda r: r.get("importance", 0), reverse=True)
    return relations


# ════════════════════════════════════════════
# 5. 主流程
# ════════════════════════════════════════════

def process_paper(md_path: str) -> dict:
    with open(md_path) as f:
        content = f.read()
    parts = content.split("\n## References", 1)
    body = parts[0]
    title = os.path.basename(md_path).replace(".md", "")

    print(f"  提取: {title} ({len(body)}字符)", file=sys.stderr)
    try:
        relations = extract_relations(body)
    except Exception as e:
        print(f"    提取失败: {e}", file=sys.stderr)
        return {"review_paper": {"file": md_path, "title": title}, "relations": [], "total": 0, "error": str(e)}
    print(f"    → {len(relations)} 条候选关系", file=sys.stderr)

    for i, rel in enumerate(relations):
        print(f"    [{i+1}/{len(relations)}] 解析论文身份...", file=sys.stderr)
        for prefix in ("source", "target"):
            info = rel.get(prefix, {})
            if isinstance(info, str):
                info = {"author_info": info, "search_queries": [info]}
            author_info = info.get("author_info", "")
            queries = info.get("search_queries", [])
            if not queries and author_info:
                queries = [author_info]

            result = None
            # 优先 V2（summary向量搜索），失败回退 V1
            if _resolve_v2:
                result = _resolve_v2(author_info)
            if not result:
                result = resolve_one_paper(author_info, queries)
            rel[prefix] = {**info, **(result or {})}

    # 过滤掉综述自身参与的 relation（作者名或文件标题匹配）
    review_names = set(re.findall(r"[A-Z][a-z]{2,}", title))
    review_names.update(re.findall(r"[A-Z][a-z]{2,}", body[:300]))  # paper header
    relations = [
        r for r in relations
        if not (
            any(n in (r.get("source", {}).get("author_info", "")) for n in review_names if len(n) > 3)
            or any(n in (r.get("target", {}).get("author_info", "")) for n in review_names if len(n) > 3)
        )
    ]

    relations = calc_importance(relations, body)

    matched_src = sum(1 for r in relations if r.get("source", {}).get("paper_id"))
    matched_tgt = sum(1 for r in relations if r.get("target", {}).get("paper_id"))
    print(f"    匹配: source {matched_src}/{len(relations)}  target {matched_tgt}/{len(relations)}", file=sys.stderr)

    return {
        "review_paper": {"file": md_path, "title": title, "body_length": len(body)},
        "relations": relations,
        "total": len(relations),
        "source_matched": matched_src,
        "target_matched": matched_tgt,
    }


def main():
    load_env()
    arg = sys.argv[1] if len(sys.argv) > 1 else MINERU_REVIEW_DIR
    out_dir = os.path.join(os.path.dirname(OUTPUT_FILE), "reviews")
    os.makedirs(out_dir, exist_ok=True)

    review_files = []
    if os.path.isfile(arg):
        review_files = [arg]
    elif os.path.isdir(arg):
        for root, _, files in os.walk(arg):
            for f in files:
                if f.endswith(".md"):
                    review_files.append(os.path.join(root, f))

    print(f"找到 {len(review_files)} 篇综述, 输出目录: {out_dir}", file=sys.stderr)

    all_results = []
    for i, f in enumerate(review_files):
        name = os.path.basename(f).replace(".md", ".json")
        out_path = os.path.join(out_dir, name)

        # 跳过已生成的文件
        if os.path.exists(out_path):
            print(f"\n[{i+1}/{len(review_files)}] 跳过 (已存在): {out_path}", file=sys.stderr)
            try:
                with open(out_path) as fp:
                    all_results.append(json.load(fp))
            except Exception:
                pass
            continue

        print(f"\n[{i+1}/{len(review_files)}]", file=sys.stderr)
        try:
            result = process_paper(f)
            with open(out_path, "w") as fp:
                json.dump(result, fp, ensure_ascii=False, indent=2)
            print(f"   → {out_path}", file=sys.stderr)
        except Exception as e:
            print(f"  失败: {e}", file=sys.stderr)
            result = {"review_paper": {"file": f}, "relations": [], "total": 0, "error": str(e)}
        all_results.append(result)
        time.sleep(0.5)

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "review_count": len(review_files),
        "total_relations": sum(r.get("total", 0) for r in all_results),
        "output_dir": out_dir,
        "results": [r["review_paper"] for r in all_results],
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n完成 → {OUTPUT_FILE} (汇总), {out_dir}/ (单篇)", file=sys.stderr)


if __name__ == "__main__":
    main()
