"""
论文信息富化: LLM从摘要+关键词提取7项结构化数据
用法:
  python backend/ingest/enrich_papers.py [--force] [--limit N] [--dry-run]
  python backend/ingest/enrich_papers.py --fix [--limit N] [--dry-run]
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

import requests

from sqlalchemy import create_engine, text as sqla_text

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = Path(__file__).resolve().parents[1] / "data" / "clean_results"
DEV_DB = BASE_DIR / "data" / "dev.db"
from backend.database import DATABASE_URL as MYSQL_URL

PROMPT = """你是超导材料研究专家。请根据以下论文信息完成七项分析。

## 论文信息
标题: {title}
摘要: {summary}
关键词: {keywords}

## 任务1：区分研究材料 vs 引述材料
- research_materials: 论文自身研究的材料(核心发现/实验验证/主要计算目标)
- referenced_materials: 引言中提及、作为对比基准、一笔带过的材料

## 任务2：判定论文类型（可多选）
- "calculate": 纯理论/计算（DFT、Eliashberg、MD等）— 研究具体材料体系
- "method": 方法论（开发新方法/算法/模型/框架）— 改进研究工具
- "experiment": 有实验合成/测量数据
- "review": 综述
示例: 纯计算→["calculate"]; 用新方法研究材料→["calculate","method"]; 实验测量→["experiment"]

## 任务3：标注论文→材料关系
仅对research_materials标注，不要包含referenced_materials：
- discovers: 首次发现/合成
- investigates: 研究/表征已知材料
- predicts: 理论预测(未合成)

## 任务4：关键物性值
对每个research_material，列出论文中报告的关键物性值（含Tc/P/λ）。
is_primary=true为核心结论值。

## 任务5：研究方法
主要方法(1-5个)：DFT, SCDFT, Eliashberg, Allen-Dynes, Wannier, MLIP, USPEX, AIRSS, VASP, Quantum ESPRESSO, path-integral, CMD, MD, XRD, Raman, DAC, SQUID, resistivity, synchrotron, neutron diffraction

## 任务6：前驱工作
核心方法/结论直接依赖的前人工作(0-3个)：
[{{"work": "Allen-Dynes Tc equation", "hint": "Allen, Dynes, 1975"}}]

## 任务7：核心发现
一句话概括物理/化学层面的核心发现，不写材料名。

返回 JSON:
{{
  "research_materials": [],
  "referenced_materials": [],
  "paper_type": ["calculate"],
  "material_relations": [{{"material":"LaH10","relation":"discovers","evidence":"原文证据"}}],
  "key_properties": {{"LaH10":[{{"name":"diffusivity","name_note":"","value":6e-06,"unit":"cm²/s","condition":{{"pressure":{{"value":250,"unit":"GPa"}},"temperature":{{"value":300,"unit":"K"}}}},"condition_note":"","is_primary":true}}]}},
  "methodology": ["DFT"],
  "builds_on": [{{"work":"Allen-Dynes Tc equation","hint":"Allen, Dynes, 1975"}}],
  "key_finding": "核心发现一句话",
  "research_motivation": "作者开展研究的驱动力，按 1. 2. 3. 分条，不超过 500 字"
}}"""

FIX_PROMPT = """你是超导材料研究专家。下面是你之前的分析结果和论文原文。请根据原文修正之前的分析。

## 之前的分析
{previous}

## 论文原文
{body}

## 修正指引
{guidance}

返回完整的JSON（同之前格式，包含 research_materials, referenced_materials, paper_type, material_relations, key_properties, methodology, builds_on, key_finding, research_motivation）"""


# ═══════════════════════════════════════════════
# 公共工具函数
# ═══════════════════════════════════════════════

def load_env():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def _extract_json(content: str) -> str:
    """从混合推理文本中提取JSON（平衡括号匹配）"""
    start = content.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(content)):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    return content[start:i + 1]
    return content


def deepseek_chat(messages: list[dict], log_path: Path | None = None) -> str:
    """一次多轮对话，返回 assistant 回复，可选写日志"""
    load_env()
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("请设置 DEEPSEEK_API_KEY")

    resp = requests.post("https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "deepseek-v4-flash", "messages": messages,
              "temperature": 0.1, "max_tokens": 3000}, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek API {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    assistant_msg = data.get("choices", [{}])[0].get("message", {})
    content = assistant_msg.get("content", "") or assistant_msg.get("reasoning_content", "")

    if log_path:
        all_msgs = messages + [{"role": "assistant", "content": content}]
        log_lines = [f"[{m['role']}]\n{m['content']}\n" for m in all_msgs]
        log_path.write_text("\n---\n".join(log_lines), encoding="utf-8")

    return content or "{}"


def read_body_from_db(paper_id: int) -> str | None:
    """从 dev.db paper_chunks 读取论文正文（前几个 chunk，~4000字）"""
    try:
        dev = sqlite3.connect(str(DEV_DB))
        rows = dev.execute(
            "SELECT content FROM paper_chunks WHERE paper_id = ? ORDER BY chunk_index LIMIT 8",
            (paper_id,)
        ).fetchall()
        dev.close()
        if rows:
            return "\n".join(r[0] for r in rows if r[0])[:4000]
    except Exception:
        pass
    return None


def is_complete(result: dict) -> bool:
    """检查结果是否有效（review/method 允许无 research_materials）"""
    if not result.get("paper_type") or not result.get("key_finding"):
        return False
    pt = result["paper_type"]
    if isinstance(pt, str):
        pt = [pt]
    if bool(set(pt) & {"review", "method"}):
        return True  # 综述/方法论允许无 materials
    return bool(result.get("research_materials") and result.get("material_relations"))


# ═══════════════════════════════════════════════
# enrich 模式：MySQL → LLM 首轮
# ═══════════════════════════════════════════════

def enrich_single(paper_id: int) -> Path | None:
    """对单篇论文运行 LLM 富化，输出到 clean_results/{paper_id}.json"""
    body = read_body_from_db(paper_id)
    if not body or not body.strip():
        return None
    parts = body.split("\n", 2)
    title = parts[0] if len(parts) > 0 else ""
    summary = parts[1] if len(parts) > 1 else ""
    keywords = parts[2] if len(parts) > 2 else ""

    log_path = CLEAN_DIR / f"{paper_id}.log"
    prompt = PROMPT.format(title=title[:200], summary=summary[:500], keywords=keywords[:200])
    resp = deepseek_chat([{"role": "user", "content": prompt}], log_path)

    try:
        result = json.loads(_extract_json(resp))
    except Exception:
        result = {}

    result["paper_id"] = paper_id
    result["paper_title"] = title
    result["paper_doi"] = ""
    out_path = CLEAN_DIR / f"{paper_id}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

    # 同步写入 papers 表
    try:
        from sqlalchemy import create_engine, text as sqla_text
        engine = create_engine(MYSQL_URL)
        with engine.connect() as c:
            c.execute(sqla_text(
                "UPDATE papers SET research_materials = :rm, referenced_materials = :rf, "
                "material_relations = :mr, builds_on = :bo WHERE id = :pid"
            ), {
                "rm": json.dumps(result.get("research_materials")),
                "rf": json.dumps(result.get("referenced_materials")),
                "mr": json.dumps(result.get("material_relations")),
                "bo": json.dumps(result.get("builds_on")),
                "pid": paper_id,
            })
            c.commit()
    except Exception:
        pass

    print(f"  [富化] paper_{paper_id}: materials={result.get('research_materials', [])}")
    return out_path


def enrich_papers(force: bool, dry_run: bool, limit: int | None):
    engine = create_engine(MYSQL_URL)
    with engine.connect() as c:
        rows = c.execute(sqla_text("""
            SELECT id, title, summary, keywords_tags FROM papers
            WHERE summary IS NOT NULL AND summary != ''
        """)).fetchall()

    enriched = 0
    skipped = 0

    for pid, title, summary, keywords in rows:
        if limit and enriched >= limit:
            break

        out_path = CLEAN_DIR / f"{pid}.json"

        # 跳过已完成的
        if out_path.exists() and not force:
            existing = json.loads(out_path.read_text())
            if is_complete(existing):
                skipped += 1
                continue

        title_s = (title or "")[:200]
        summary_s = (summary or "")[:500]
        keywords_s = (keywords or "")[:200]

        if dry_run:
            print(f"[DRY] paper_{pid}: {title_s[:60]}")
            continue

        log_path = CLEAN_DIR / f"{pid}.log"
        prompt = PROMPT.format(title=title_s, summary=summary_s, keywords=keywords_s)
        resp = deepseek_chat([{"role": "user", "content": prompt}], log_path)

        try:
            result = json.loads(_extract_json(resp))
        except Exception:
            print(f"  paper_{pid} JSON解析失败", file=sys.stderr)
            result = {}

        result["paper_id"] = pid
        result["paper_title"] = title
        result["paper_doi"] = ""

        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

        research = result.get("research_materials", [])
        finding = (result.get("key_finding") or "")[:50]
        print(f"  paper_{pid} research={research} type={result.get('paper_type','?')} "
              f"methods={len(result.get('methodology',[]))} "
              f"builds_on={len(result.get('builds_on',[]))} finding=\"{finding}\"")
        enriched += 1

    print(f"\n增强: {enriched}, 跳过(已有): {skipped}")


# ═══════════════════════════════════════════════
# fix 模式：已有 JSON 自检 + 原文兜底
# ═══════════════════════════════════════════════

def fix_papers(dry_run: bool, limit: int | None):
    json_files = sorted(CLEAN_DIR.glob("*.json"))
    checked = 0
    fixed = 0

    for json_path in json_files:
        if limit and checked >= limit:
            break

        pid = int(json_path.stem)
        data = json.loads(json_path.read_text())

        # 跳过已完整的
        if is_complete(data):
            mats = data.get("research_materials", [])
            has_placeholder = any(
                w in str(m).lower()
                for w in ["material_", "未公开", "未知", "某材料", "unnamed"]
                for m in mats
            )
            if not has_placeholder:
                continue

        checked += 1
        if dry_run:
            print(f"[DRY] paper_{pid}: mats={data.get('research_materials',[])}")
            continue

        # ── 自检轮 ──
        prev_keys = [
            "research_materials", "referenced_materials", "paper_type",
            "material_relations", "key_properties", "methodology",
            "builds_on", "key_finding",
        ]
        prev_json = json.dumps(
            {k: data.get(k) for k in prev_keys if k in data},
            ensure_ascii=False,
        )[:1000]

        check_msg = f"""以下是我的分析结果，请检查是否完整准确。
如果材料名是占位符（如"Material_A"、"未公开"、"未知"）或缺少关键字段，或者声称了研究了某个材料，但是缺失性质时，需要从原文补充。


分析结果:
{prev_json}

如果已完整准确，回复 {{{{"complete": true}}}}
如果需要从原文补充，回复 {{{{"complete": false, "need": "需要补充什么(50字)"}}}}"""

        try:
            check_resp = deepseek_chat([{"role": "user", "content": check_msg}])
            check = json.loads(_extract_json(check_resp))
        except Exception:
            check = {"complete": True}

        if check.get("complete", True):
            continue

        # ── 原文兜底 ──
        body = read_body_from_db(pid)
        if not body:
            continue

        guidance = check.get("need", "补充缺失的材料名称和关键信息")
        fix_msg = FIX_PROMPT.format(previous=prev_json, body=body[:3000], guidance=guidance)
        try:
            fix_resp = deepseek_chat([{"role": "user", "content": fix_msg}])
            fix_result = json.loads(_extract_json(fix_resp))
            if is_complete(fix_result):
                fix_result["paper_id"] = data.get("paper_id", pid)
                fix_result["paper_title"] = data.get("paper_title", "")
                fix_result["paper_doi"] = data.get("paper_doi", "")
                json_path.write_text(json.dumps(fix_result, ensure_ascii=False, indent=2))

                log_path = CLEAN_DIR / f"{pid}.log"
                all_msgs = [{"role": "user", "content": fix_msg},
                           {"role": "assistant", "content": fix_resp}]
                log_lines = [f"[{m['role']}]\n{m['content']}\n" for m in all_msgs]
                log_path.write_text("\n---\n".join(log_lines), encoding="utf-8")
                fixed += 1
                print(f"  paper_{pid} 修复 ok materials={fix_result.get('research_materials',[])}")
        except Exception as e:
            print(f"  paper_{pid} 修复失败: {e}")

    print(f"\n自检: {checked}, 修复: {fixed}")


# ═══════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════

def main():
    limit = None
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    if "--fix" in sys.argv:
        fix_papers("--dry-run" in sys.argv, limit)
    else:
        enrich_papers("--force" in sys.argv, "--dry-run" in sys.argv, limit)


if __name__ == "__main__":
    main()
