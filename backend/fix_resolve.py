"""
重新解析 paper_id（V2 summary搜索优先 + V1 RAG fallback）+ 多引用拆分
用法: python backend/fix_resolve.py
"""
import copy, json, os, glob, re, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from extract_relations import search_paper, fetch_abstracts, llm_match, llm_match_with_chunks

# V2 匹配
try:
    sys.path.insert(0, "/home/work/workshop/git/SC-Wiki-modules")
    from resolve_v2 import resolve_one_paper as resolve_v2
except ImportError:
    resolve_v2 = None

REVIEWS_DIR = "/home/work/workshop/bak/reviews"
LOG_FILE = os.path.join(REVIEWS_DIR, "fix_resolve.log")


class Tee:
    """同时输出到 stderr 和日志文件。"""
    def __init__(self, path):
        self.file = open(path, "a")
        self.stderr = sys.stderr

    def write(self, s):
        self.stderr.write(s)
        self.file.write(s)

    def flush(self):
        self.stderr.flush()
        self.file.flush()


def extract_multi_refs(author_info: str) -> list[str]:
    """检测 author_info 中的多引用模式 [14,22] 或 文献[14,22]，拆分为独立条目"""
    # 匹配 [...] 中包含逗号分隔数字的模式
    m = re.search(r'\[(\d+(?:\s*,\s*\d+)+)\]', author_info)
    if not m:
        return [author_info]

    nums = [n.strip() for n in m.group(1).split(',')]
    if len(nums) <= 1:
        return [author_info]

    prefix = author_info[:m.start()]
    suffix = author_info[m.end():]

    results = []
    for n in nums:
        single_ref = f"[{n}]"
        new_info = prefix + single_ref + suffix
        results.append(new_info)
    return results


def split_multi_refs(relations: list[dict]) -> list[dict]:
    """拆分含多引用的关系，返回展开后的关系列表"""
    result = []
    split_count = 0
    for r in relations:
        src = r.get("source", {}) if isinstance(r.get("source"), dict) else {}
        tgt = r.get("target", {}) if isinstance(r.get("target"), dict) else {}

        src_refs = extract_multi_refs(src.get("author_info", ""))
        tgt_refs = extract_multi_refs(tgt.get("author_info", ""))

        if len(src_refs) == 1 and len(tgt_refs) == 1:
            result.append(r)
            continue

        # 生成笛卡尔积
        for s_ref in src_refs:
            for t_ref in tgt_refs:
                new_r = copy.deepcopy(r)
                if len(src_refs) > 1:
                    new_r["source"]["author_info"] = s_ref
                if len(tgt_refs) > 1:
                    new_r["target"]["author_info"] = t_ref
                result.append(new_r)
                split_count += 1

    if split_count > 0:
        print(f"    多引用拆分: {split_count - len(relations)} → {split_count} 条", file=sys.stderr)
    return result


def resolve_one(author_info: str, queries: list[str]):
    """V2优先: summary向量搜索 → 失败回退 V1 RAG。"""
    if not queries:
        queries = [author_info] if author_info else []
    if not queries:
        return None

    # ── 优先 V2 ──
    if resolve_v2:
        print(f"    [V2] {author_info[:60]}...", end=" ", flush=True)
        try:
            result = resolve_v2(author_info)
            if result:
                print(f"→ paper_{result['paper_id']} (summary_verified)", flush=True)
                return result
            print("无匹配, 回退V1", flush=True)
        except Exception as e:
            print(f"✗ {e}, 回退V1", flush=True)

    # ── V1 fallback ──
    # 1. RAG 搜索
    print(f"    RAG搜索: {queries[0][:60]}...", end=" ", flush=True)
    try:
        top_ids, chunks_by_paper = search_paper(queries)
        print(f"→ {len(top_ids)} candidates", flush=True)
    except Exception as e:
        print(f"✗ {e}", flush=True)
        return None

    if not top_ids:
        return None

    # 2. MySQL 查摘要
    print(f"    查摘要: {top_ids[:3]}...", end=" ", flush=True)
    try:
        abstracts = fetch_abstracts(top_ids)
        print(f"→ {len(abstracts)} have data", flush=True)
    except Exception as e:
        print(f"✗ {e}", flush=True)
        abstracts = {}

    if not abstracts:
        # 所有候选都是综述/博士论文 → 用 RAG 第一名（有 chunks 数据支撑）
        return {"paper_id": top_ids[0], "match_method": "rag_only", "note": "all_candidates_excluded"}

    # 3. LLM 验证（摘要 → 失败则用RAG原文chunks再试）
    try:
        matched = llm_match(author_info, abstracts, queries)
        if not matched:
            print("      [摘要] 无匹配, chunks再试", file=sys.stderr)
            matched = llm_match_with_chunks(author_info, chunks_by_paper, queries)
            if not matched:
                print("      [内容] 无匹配, fallback rag_first", file=sys.stderr)

        if matched:
            return {
                "paper_id": matched,
                "abstract": abstracts.get(matched, "")[:500],
                "match_method": "llm_verified",
                "candidates": top_ids,
            }
    except Exception as e:
        print(f"✗ {e}", flush=True)

    return {"paper_id": top_ids[0], "match_method": "rag_first", "candidates": top_ids}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", help="指定单个 JSON 文件")
    args = parser.parse_args()

    sys.stderr = Tee(LOG_FILE)
    if args.file:
        files = [args.file]
    else:
        files = sorted(glob.glob(os.path.join(REVIEWS_DIR, "*.json")))
    start = time.time()

    for fi, f in enumerate(files):
        with open(f) as fp:
            d = json.load(fp)
        rels = d.get("relations", [])

        # ── 阶段0: 多引用拆分 ──
        old_count = len(rels)
        rels = split_multi_refs(rels)
        if len(rels) != old_count:
            print(f"  多引用拆分: {old_count} → {len(rels)}")
            d["relations"] = rels

        missing = sum(1 for r in rels if not r.get("source", {}).get("paper_id") or not r.get("target", {}).get("paper_id"))
        if missing == 0:
            continue

        name = os.path.basename(f)
        elapsed = int(time.time() - start)
        print(f"\n[{fi+1}/{len(files)}] {name} ({missing}/{len(rels)} need fix) [{elapsed}s]", flush=True)
        fixed = 0
        for ri, r in enumerate(rels):
            for prefix in ("source", "target"):
                info = r.get(prefix, {})
                if isinstance(info, str):
                    info = {"author_info": info, "search_queries": [info]}
                if info.get("paper_id"):
                    continue
                author_info = info.get("author_info", "")
                queries = info.get("search_queries", [])
                print(f"  [{ri+1}.{prefix}]", end=" ", flush=True)
                result = resolve_one(author_info, queries)
                if result and result.get("paper_id"):
                    r[prefix] = {**info, **result}
                    fixed += 1
                time.sleep(0.2)

        with open(f, "w") as fp:
            json.dump(d, fp, ensure_ascii=False, indent=2)
        print(f"  ✓ 修复 {fixed}", flush=True)

    print(f"\n完成! 总耗时 {int(time.time()-start)}s")


if __name__ == "__main__":
    main()
