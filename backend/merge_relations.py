"""
合并 reviews/ 下所有 JSON → 去重 → 输出 graph.json
节点用 paper_id 或 author_info hash 做 ID，有 paper_id 时查标题
"""
import json, os, glob, hashlib
from collections import Counter

import requests

REVIEWS_DIR = "/home/work/workshop/bak/reviews"
OUTPUT = "/home/work/workshop/bak/graph.json"
API = "http://localhost:8000"

_title_cache: dict[int, str] = {}


def fetch_title(paper_id: int) -> str:
    if paper_id in _title_cache:
        return _title_cache[paper_id]
    try:
        resp = requests.get(f"{API}/api/papers/{paper_id}", timeout=5)
        if resp.ok:
            title = resp.json().get("title", "") or ""
            _title_cache[paper_id] = title
            return title
    except Exception:
        pass
    return ""


def node_id(rec: dict) -> str:
    """优先 paper_id，否则用 author_info hash"""
    pid = rec.get("paper_id")
    if pid:
        return f"paper_{pid}"
    info = (rec.get("author_info") or "").strip().lower()[:80]
    h = hashlib.md5(info.encode()).hexdigest()[:8]
    return f"node_{h}"


def node_label(rec: dict) -> str:
    """节点显示名：有 paper_id 查标题，否则用 author_info"""
    pid = rec.get("paper_id")
    if pid:
        title = fetch_title(pid)
        if title:
            return title[:120]
    return (rec.get("author_info") or rec.get("title") or "")[:80]


def main():
    files = sorted(glob.glob(os.path.join(REVIEWS_DIR, "*.json")))
    print(f"读取 {len(files)} 个文件...")

    edges = []
    nodes = {}
    seen = set()
    self_loop = 0
    match_methods = Counter()
    paper_id_count = 0
    total_pairs = 0

    for f in files:
        try:
            with open(f) as fp:
                d = json.load(fp)
        except Exception:
            continue
        for r in d.get("relations", []):
            src = r.get("source", {}) or {}
            tgt = r.get("target", {}) or {}
            if isinstance(src, str):
                src = {"author_info": src}
            if isinstance(tgt, str):
                tgt = {"author_info": tgt}

            sid = node_id(src)
            tid = node_id(tgt)
            if sid == tid:
                self_loop += 1
                continue

            total_pairs += 2
            for info in (src, tgt):
                if info.get("paper_id"):
                    paper_id_count += 1
                    match_methods[info.get("match_method", "unknown")] += 1

            rel_type = r.get("relation_type", "unknown")
            importance = r.get("importance", 0)

            key = (sid, tid, rel_type)
            if key in seen:
                continue
            seen.add(key)

            for nid, info in [(sid, src), (tid, tgt)]:
                if nid not in nodes:
                    nodes[nid] = {
                        "id": nid,
                        "label": node_label(info),
                        "paper_id": info.get("paper_id"),
                        "match_method": info.get("match_method", ""),
                    }

            edges.append({
                "source": sid, "target": tid,
                "type": rel_type,
                "label": r.get("relation_label", ""),
                "importance": importance,
                "evidence": (r.get("evidence") or "")[:200],
            })

    print(f"关系: {len(files)}文件 → {len(edges)+self_loop}条边(排除{self_loop}自环) → {len(edges)}去重")
    print(f"节点: {len(nodes)}个 (有paper_id: {paper_id_count}/{total_pairs})")
    print(f"匹配方式: {dict(match_methods)}")

    # 只保留 importance > 0.25 的边
    before = len(edges)
    edges = [e for e in edges if e["importance"] > 0.25]
    print(f"importance>0.25: {before} → {len(edges)}")

    used = set()
    for e in edges:
        used.add(e["source"]); used.add(e["target"])
    nodes_list = [nodes[nid] for nid in used if nid in nodes]

    print(f"最终: {len(edges)} edges, {len(nodes_list)} nodes")

    with open(OUTPUT, "w") as f:
        json.dump({"nodes": nodes_list, "edges": edges}, f, ensure_ascii=False)
    print(f"输出: {OUTPUT}")


if __name__ == "__main__":
    main()
