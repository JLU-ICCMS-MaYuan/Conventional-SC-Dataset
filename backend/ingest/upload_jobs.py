"""RQ jobs for the staged paper upload workflow."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import and_, func

from backend.database import SessionLocal
from backend.db_helpers import normalize_formula
from backend.ingest.chunker import Chunk, chunk_paper
from backend.ingest.extractor import _parse_result
from backend.ingest.pdf_extractor import extract_text_from_pdf
from backend.ingest.upload_tasks import (
    artifact_directory,
    artifact_path,
    data_path,
    get_state,
    markdown_path,
    save_draft,
    schedule_cleanup,
    update_state,
)
from backend.ingest.upload_contracts import (
    UPLOAD_STATE_SCHEMA_VERSION,
    compare_file_identities,
    structure_format_for_filename,
)
from backend.ingest.structure_extractor import extract_structure_candidates
from backend.models import Paper, PaperFile
from backend.rag.llm import complete_json
from backend.services.structure_candidates import (
    StructureCandidateError,
    build_structure_candidate,
)


CHUNK_SYSTEM_PROMPT = """你是超导论文证据提取助手。只根据给出的一个论文分段提取候选事实，返回 JSON。
每个事实都要保留可逐字核对的原文 quote 和最近的 <!-- page: N --> 页码；没有信息时返回空数组或 null，不要猜测。
论文整体类型和材料类型此时只给候选证据，不做最终决定。
每条论文类型证据和材料类型候选必须标记 scope：current_paper 表示本文作者实际完成的工作，
referenced_work 表示前人研究、引用论文或领域背景。同一分段同时含两类陈述时分别输出。
前人实验、理论预测或综述叙述不能作为本文自身类型证据。材料类型 value 允许自由文本，但必须描述
材料家族或体系，不能用临界温度高低、配对机制或计算方法代替材料类型。
referenced_materials 仅作为后台排除误判的临时候选，不进入用户界面、最终草稿或正式论文数据。
每个压力条件单独建立 material_state；压力同时保留换算后的 GPa 数值和论文原始文本/单位。
空间群必须拆为 Hermann–Mauguin 符号与国际群号。λ 写入 lambda_ep，ωlog 写入 omega_log_k（K）；
原文未报告的字段必须为 null。Tc 写入 tc_results，不得混入普通 properties。
通讯作者只能根据星号说明、通讯邮箱或 correspondence 声明识别；共同第一作者只能根据
equal contribution、contributed equally 等明确声明识别。证据不足时返回空数组，不得按作者顺序猜测。

返回结构：
{
  "metadata": {"title": null, "doi": null, "authors": [], "corresponding_authors": [], "co_first_authors": [], "journal": null, "year": null, "abstract": null},
  "paper_type_evidence": [{"candidate": "theoretical|experimental|review|unknown", "scope": "current_paper|referenced_work", "page": 1, "quote": "原文"}],
  "research_materials": [],
  "referenced_materials": [],
  "material_relations": [{"material": "", "relation": "discovers|investigates|predicts", "page": 1, "quote": ""}],
  "material_states": [{
    "material": "",
    "scope": "current_paper|referenced_work",
    "material_family": {"name": "自由材料家族名称", "scope": "current_paper|referenced_work", "page": 1, "quote": ""},
    "structure_families": [{"name": "结构家族名称", "is_primary": true, "scope": "current_paper|referenced_work", "page": 1, "quote": ""}],
    "material_dimensionality": "zero_dimensional|one_dimensional|two_dimensional|three_dimensional|quasi_one_dimensional|quasi_two_dimensional|unknown",
    "pressure_value_gpa": null, "pressure_min_gpa": null, "pressure_max_gpa": null,
    "pressure_raw": null, "pressure_unit_raw": null,
    "state_kind": "theoretical|experimental|mixed|unknown",
    "reported_space_group_symbol": null, "reported_space_group_number": null,
    "calculation_context": {"lambda_ep": null, "omega_log_k": null, "mu_star": null},
    "tc_results": [], "properties": [],
    "evidence": {"page": 1, "quote": "原文"}
  }],
  "methodology": [],
  "key_findings": []
}"""

CHUNK_RESULT_SCHEMA_VERSION = 5

PUBLIC_CHUNK_RESULT_FIELDS = {
    "metadata", "paper_type_evidence", "research_materials",
    "material_relations", "material_states", "methodology", "key_findings", "_source",
}

FORM_PREVIEW_GROUPS = (
    ("bibliography", "基本信息", (
        ("paper.title", "标题"), ("paper.doi", "DOI"), ("paper.authors", "作者"),
        ("paper.journal", "期刊"), ("paper.volume", "卷"), ("paper.pages", "页码"),
        ("paper.year", "年份"), ("paper.abstract", "摘要"),
    )),
    ("classification", "分类判断", (
        ("paper.paper_type", "论文类型"), ("paper.theoretical_subtype", "理论二级类型"),
        ("classification_reason", "分类理由"),
    )),
    ("content", "研究内容", (
        ("paper.summary", "全文摘要"), ("paper.keywords_tags", "关键词"),
        ("paper.methodology", "研究方法"), ("paper.key_finding", "主要结论"),
        ("paper.rationale", "判断依据"), ("paper.research_materials", "研究材料"),
        ("paper.material_relations", "材料关系"),
        ("paper.builds_on", "工作脉络"),
    )),
    ("properties", "关键物性", (("material_states", "材料状态与物性数据"),)),
)

FORM_PREVIEW_MULTI_FIELDS = {
    "paper.authors", "paper.keywords_tags", "paper.methodology", "paper.key_finding",
    "paper.research_materials", "paper.material_relations",
    "paper.builds_on", "material_states",
}

FORM_PREVIEW_CLASSIFICATION_FIELDS = {
    path
    for group_id, _, fields in FORM_PREVIEW_GROUPS
    if group_id == "classification"
    for path, _ in fields
}


SUMMARY_SYSTEM_PROMPT = """你是超导材料论文分类与结构化提取专家。汇总整篇论文各分段候选事实，去重并返回 JSON 草稿。

论文整体分类按核心贡献判断：
- 理论提出主要结论、实验只验证理论，归 theoretical。
- 实验发现主要现象、理论用于解释实验，归 experimental。
- 理论和实验同等重要、无法分主次，也归 experimental。
- 以整理评价已有工作为主，归 review。
理论二级类型只允许 calculation、method、theory。新算法、新模型、新研究工具归 method；使用已有计算方法研究具体问题归 calculation；解析推导、理论模型或机制研究归 theory。
材料超导类型必须综合全文判断，可以使用已有类型，也可以提出自由文本新类型，不能只凭化学式猜测。
分段证据中的 scope 表示证据主体；只有 scope=current_paper 的候选可以决定本文 paper_type 和材料状态分类，
scope=referenced_work 或缺少 scope 的候选只能作为背景，不能参与本文分类。
referenced_materials 仅用于帮助区分本文对象与背景对象，最终草稿不要返回该字段。
论文整体 paper_type 与每条物性的 article_type 必须分别判断，article_type 只允许 e 或 t。
每个关键分类和物性保留 section/page/quote 证据；无法确定就返回 unknown 或空值，不要编造。
通讯作者和共同第一作者必须来自 authors；仅在分段候选包含明确声明时保留，不能根据作者顺序猜测。
按材料、压力、state_kind 和报告空间群区分 material_states。空间群符号与群号必须分开；λ、ωlog 只写入
calculation_context，Tc 只写入 tc_results。压力优先换算为 GPa，同时保留 pressure_raw 和
pressure_unit_raw；无法可靠换算或原文没有报告时保留原文并将规范数值设为 null。

返回结构：
{
  "paper": {
    "title": "", "doi": null, "authors": [], "corresponding_authors": [], "co_first_authors": [],
    "journal": null, "volume": null, "pages": null,
    "year": null, "abstract": null, "summary": "", "paper_type": "theoretical|experimental|review|unknown",
    "theoretical_subtype": null, "keywords_tags": [], "methodology": [], "key_finding": "",
    "rationale": "", "research_materials": [], "material_relations": [], "builds_on": []
  },
  "material_states": [{
    "material": "",
    "material_family": {"id": null, "name": "自由材料家族名称", "status": "pending", "evidence": {"section": "", "page": null, "quote": ""}},
    "structure_families": [{"id": null, "name": "结构家族名称", "is_primary": true, "status": "pending", "evidence": {"section": "", "page": null, "quote": ""}}],
    "element_count": null,
    "material_dimensionality": "zero_dimensional|one_dimensional|two_dimensional|three_dimensional|quasi_one_dimensional|quasi_two_dimensional|unknown",
    "pressure_value_gpa": null, "pressure_min_gpa": null, "pressure_max_gpa": null,
    "pressure_raw": null, "pressure_unit_raw": null,
    "state_kind": "theoretical|experimental|mixed|unknown",
    "reported_space_group_symbol": null, "reported_space_group_number": null,
    "space_group_evidence": {"section": "", "page": null, "quote": ""},
    "structure": null,
    "calculation_context": {
      "phonon_nuclear_treatment": "unknown", "lambda_ep": null,
      "omega_log_k": null, "mu_star": null,
      "evidence": {"section": "", "page": null, "quote": ""}
    },
    "experimental_context": null,
    "tc_results": [{
      "result_kind": "theoretical|experimental", "tc_method": "unknown|experimental|allen_dynes|mcmillan|isotropic_eliashberg|anisotropic_eliashberg",
      "tc_value_k": null, "tc_min_k": null, "tc_max_k": null,
      "value_raw": "", "unit_raw": "K", "evidence": {"section": "", "page": null, "quote": ""}
    }],
    "properties": []
  }],
  "classification_reason": "",
  "classification_evidence": [{"section": "", "page": null, "quote": ""}]
}"""


class UploadCancelled(RuntimeError):
    """任务已请求取消，Worker 应停止且不得写回成功状态。"""


def _schedule_terminal_cleanup(task_id: str) -> None:
    """清理调度失败不能覆盖已完成或已记录的处理结果。"""
    try:
        schedule_cleanup(task_id)
    except Exception as exc:
        print(f"  [上传] task_id={task_id} 无法安排终态清理: {exc}")


def _ensure_not_cancelled(task_id: str) -> dict[str, Any]:
    state = get_state(task_id)
    if not state:
        raise UploadCancelled("上传任务已被清理")
    if state.get("status") in {"cancelling", "cancelled"}:
        if state.get("status") == "cancelling":
            cancelled = update_state(
                task_id, status="cancelled", processing_status="cancelled",
                processing_error=None,
            )
            _schedule_terminal_cleanup(task_id)
            return cancelled
        raise UploadCancelled("上传任务已取消")
    return state


def _original_path(state: dict[str, Any]) -> Path:
    value = state.get("file_path")
    if not value:
        main = next(
            (item for item in state.get("files") or [] if item.get("role") == "main"),
            None,
        )
        value = main.get("stored_path") if main else None
    if not value:
        raise RuntimeError("上传文件路径缺失")
    path = Path(str(value))
    if not path.is_file():
        raise RuntimeError("上传文件不存在或已清理")
    return path


def _extract_markdown(state: dict[str, Any], source: Path) -> str:
    if state.get("file_kind") == "pdf":
        text = extract_text_from_pdf(source)
        if len(text.strip()) < 50:
            raise ValueError("PDF 文本提取失败，可能为扫描件，请上传可搜索文本的 PDF")
        return text
    for encoding in ("utf-8", "gbk"):
        try:
            return source.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法解码文件内容，请使用 UTF-8 编码")


def _structure_format_for_file(file_item: dict[str, Any], source: Path) -> str | None:
    filename = str(file_item.get("original_filename") or source.name)
    return structure_format_for_filename(filename)


def _lightweight_identity(file_item: dict[str, Any], markdown: str) -> dict[str, Any]:
    head = markdown[:12000]
    doi_match = re.search(r"10\.\d{4,9}/[^\s<>\"]+", head, re.IGNORECASE)
    lines = [
        re.sub(r"^#+\s*", "", line).strip()
        for line in head.splitlines()
        if line.strip() and not line.lstrip().startswith("<!--")
    ]
    return {
        "file_id": file_item.get("file_id"),
        "role": file_item.get("role"),
        "title": lines[0] if lines else None,
        "doi": doi_match.group(0).rstrip(".,;)") if doi_match else None,
        "authors": None,
    }


def _chunks_with_preamble(markdown: str) -> list[Chunk]:
    chunks = chunk_paper(markdown, paper_id=0)
    if not chunks:
        return []
    sample = chunks[0].content[:120]
    offset = markdown.find(sample) if sample else -1
    preamble = markdown[:offset].strip() if offset > 0 else ""
    if len(preamble) >= 10:
        chunks.insert(0, Chunk(0, 0, "论文首页与摘要", None, preamble, max(1, len(preamble) // 4)))
    cursor = 0
    for index, chunk in enumerate(chunks):
        chunk.chunk_index = index
        sample = chunk.content[:120]
        offset = markdown.find(sample, cursor) if sample else -1
        if offset < 0 and sample:
            offset = markdown.find(sample)
        if offset >= 0:
            cursor = offset + len(sample)
            local_marker = re.search(r"<!--\s*page:\s*(\d+)\s*-->", chunk.content)
            if local_marker:
                chunk.source_page = int(local_marker.group(1))
            else:
                markers = list(re.finditer(r"<!--\s*page:\s*(\d+)\s*-->", markdown[:offset]))
                chunk.source_page = int(markers[-1].group(1)) if markers else None
        else:
            chunk.source_page = None
    return chunks


def _chunk_result_path(
    task_id: str, chunk_index: int, file_id: str | None = None, *, create: bool = True,
) -> Path:
    directory = (
        artifact_directory(task_id) if create
        else data_path("review_artifacts") / task_id
    ) / "chunks"
    if file_id:
        directory = directory / file_id
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{chunk_index:05d}.json"


def _atomic_write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _read_chunk(
    task_id: str,
    chunk: Chunk,
    file_id: str | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result_path = _chunk_result_path(task_id, chunk.chunk_index, file_id)
    if result_path.exists():
        cached = json.loads(result_path.read_text(encoding="utf-8"))
        if cached.get("_schema_version") == CHUNK_RESULT_SCHEMA_VERSION:
            return cached
    prompt = (
        f"章节：{chunk.section_name or '正文'}\n页码：{getattr(chunk, 'source_page', None) or '未知'}\n"
        f"分段编号：{chunk.chunk_index}\n\n{chunk.content}"
    )
    result = complete_json(CHUNK_SYSTEM_PROMPT, prompt)
    result["_schema_version"] = CHUNK_RESULT_SCHEMA_VERSION
    result["_source"] = {
        "file_id": file_id,
        "filename": (source or {}).get("original_filename"),
        "file_role": (source or {}).get("role"),
        "chunk_index": chunk.chunk_index,
        "section": chunk.section_name or "正文",
        "page_start": getattr(chunk, "source_page", None),
        "page_end": getattr(chunk, "source_page", None),
    }
    _atomic_write_json(result_path, result)
    return result


def _chunk_manifest_path(task_id: str, *, create: bool = True) -> Path:
    root = artifact_directory(task_id) if create else data_path("review_artifacts") / task_id
    path = root / "chunks" / "manifest.json"
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _save_chunk_manifest(task_id: str, items: list[dict[str, Any]]) -> None:
    _atomic_write_json(_chunk_manifest_path(task_id), {"items": items})


def _preview_source(chunk: dict[str, Any], evidence: Any = None) -> dict[str, Any]:
    source = {
        key: chunk.get(key) for key in (
            "file_id", "filename", "file_role", "section", "page_start", "page_end",
        )
    }
    if isinstance(evidence, dict):
        page = evidence.get("page")
        if page not in (None, ""):
            source["page_start"] = page
            source["page_end"] = page
        quote = str(evidence.get("quote") or "").strip()
        if quote:
            source["quote"] = quote
    return source


def _preview_item_value(item: Any, *keys: str) -> Any:
    if not isinstance(item, dict):
        return item
    for key in keys:
        if item.get(key) not in (None, ""):
            return item[key]
    return None


def _is_current_paper_evidence(item: Any) -> bool:
    return isinstance(item, dict) and item.get("scope") == "current_paper"


def _is_effective_paper_type_evidence(item: Any) -> bool:
    return (
        _is_current_paper_evidence(item)
        and _preview_item_value(item, "candidate", "value") != "unknown"
    )


def _current_paper_material_state(item: Any) -> dict[str, Any] | None:
    if not _is_current_paper_evidence(item):
        return None
    state = json.loads(json.dumps(item, ensure_ascii=False))
    family = state.get("material_family")
    if isinstance(family, dict) and family.get("scope") != "current_paper":
        state["material_family"] = None
    state["structure_families"] = [
        selection
        for selection in state.get("structure_families") or []
        if _is_current_paper_evidence(selection)
    ]
    return state


def _classification_scope_evidence(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten raw scoped candidates for the administrator-only review artifact."""
    evidence: list[dict[str, Any]] = []

    def add(dimension: str, raw_name: Any, item: Any, source: Any) -> None:
        if not isinstance(item, dict) or item.get("scope") not in {"current_paper", "referenced_work"}:
            return
        entry = {
            "dimension": dimension,
            "raw_name": str(raw_name or "").strip(),
            "scope": item["scope"],
            **_preview_source(source if isinstance(source, dict) else {}, item),
        }
        evidence.append(entry)

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for item in candidate.get("paper_type_evidence") or []:
            add("paper_type", _preview_item_value(item, "candidate", "value"), item, candidate.get("_source"))
        for item in candidate.get("sc_type_candidates") or []:
            add("material_family", _preview_item_value(item, "value", "name"), item, candidate.get("_source"))
        for state in candidate.get("material_states") or []:
            if not isinstance(state, dict):
                continue
            add("material_state", state.get("material"), state, candidate.get("_source"))
            family = state.get("material_family")
            if isinstance(family, dict):
                add("material_family", family.get("name") or family.get("value"), family, candidate.get("_source"))
            for structure in state.get("structure_families") or []:
                if isinstance(structure, dict):
                    add("structure_family", structure.get("name") or structure.get("value"), structure, candidate.get("_source"))
    return evidence


def _summary_classification_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared = json.loads(json.dumps(candidates, ensure_ascii=False))
    for result in prepared:
        if "paper_type_evidence" in result:
            result["paper_type_evidence"] = [
                item for item in result.get("paper_type_evidence") or []
                if _is_effective_paper_type_evidence(item)
            ]
        if "sc_type_candidates" in result:
            result["sc_type_candidates"] = [
                item for item in result.get("sc_type_candidates") or []
                if _is_current_paper_evidence(item)
            ]
        if "material_states" in result:
            result["material_states"] = [
                material_state for item in result.get("material_states") or []
                if (material_state := _current_paper_material_state(item)) is not None
            ]
    return prepared


def _build_form_preview(chunks: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    buckets: dict[str, dict[str, dict[str, Any]]] = {
        path: {} for _, _, fields in FORM_PREVIEW_GROUPS for path, _ in fields
    }

    def add(path: str, value: Any, chunk: dict[str, Any], evidence: Any = None) -> None:
        if value in (None, "", [], {}):
            return
        if path == "material_states" and isinstance(value, dict):
            value = {
                key: item for key, item in value.items()
                if key not in {"page", "quote", "evidence", "_source"}
            }
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        candidate = buckets[path].setdefault(key, {"value": value, "sources": []})
        source = _preview_source(chunk, evidence)
        source_key = json.dumps(source, ensure_ascii=False, sort_keys=True)
        if all(json.dumps(item, ensure_ascii=False, sort_keys=True) != source_key for item in candidate["sources"]):
            candidate["sources"].append(source)

    for chunk in chunks:
        result = chunk.get("result")
        if not isinstance(result, dict):
            continue
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        for key in ("title", "doi", "journal", "year", "abstract"):
            add(f"paper.{key}", metadata.get(key), chunk)
        for author in metadata.get("authors") or []:
            add("paper.authors", author, chunk)
        for item in result.get("paper_type_evidence") or []:
            if _is_effective_paper_type_evidence(item):
                add("paper.paper_type", _preview_item_value(item, "candidate", "value"), chunk, item)
        for result_key, path, keys in (
            ("research_materials", "paper.research_materials", ("value", "material", "name")),
            ("methodology", "paper.methodology", ("value", "method", "name")),
            ("key_findings", "paper.key_finding", ("value", "finding", "text")),
            ("material_relations", "paper.material_relations", ()),
        ):
            for item in result.get(result_key) or []:
                add(path, _preview_item_value(item, *keys) if keys else item, chunk, item)
        for item in result.get("material_states") or []:
            if _is_current_paper_evidence(item):
                add("material_states", item, chunk, item)

    task_status = state.get("status")
    classification_pending = task_status in {"reading", "summarizing"}
    groups: list[dict[str, Any]] = []
    for group_id, label, field_specs in FORM_PREVIEW_GROUPS:
        fields: list[dict[str, Any]] = []
        for path, field_label in field_specs:
            candidates = list(buckets[path].values())
            conflict = path not in FORM_PREVIEW_MULTI_FIELDS and len(candidates) > 1
            field_state = (
                "pending_summary"
                if classification_pending and path in FORM_PREVIEW_CLASSIFICATION_FIELDS
                else "conflict" if conflict
                else "filled" if candidates
                else "waiting"
            )
            fields.append({
                "path": path,
                "label": field_label,
                "state": field_state,
                "candidates": candidates,
            })
        groups.append({"id": group_id, "label": label, "fields": fields})

    preview_status = (
        "ready" if task_status == "ready"
        else "summarizing" if task_status == "summarizing"
        else "updating" if any(buckets[path] for path in buckets)
        else "waiting"
    )
    return {
        "status": preview_status,
        "read_only": task_status != "ready",
        "groups": groups,
    }


def public_parsing_detail(task_id: str) -> dict[str, Any]:
    """返回安全的文件/分段/汇总快照。"""
    state = get_state(task_id)
    if not state:
        raise KeyError("上传任务不存在或已过期")
    manifest_path = _chunk_manifest_path(task_id, create=False)
    try:
        items = json.loads(manifest_path.read_text(encoding="utf-8")).get("items", [])
    except (OSError, json.JSONDecodeError):
        items = []
    chunks: list[dict[str, Any]] = []
    for item in items:
        public = {
            key: item.get(key) for key in (
                "chunk_id", "file_id", "filename", "file_role", "index", "section",
                "page_start", "page_end", "status", "error",
            )
        }
        if item.get("status") == "completed":
            path = _chunk_result_path(
                task_id, int(item["index"]), item.get("cache_file_id"), create=False,
            )
            try:
                result = json.loads(path.read_text(encoding="utf-8"))
                public_result = {
                    key: result[key] for key in PUBLIC_CHUNK_RESULT_FIELDS if key in result
                }
                if "material_states" in public_result:
                    public_result["material_states"] = [
                        material_state for item in public_result["material_states"]
                        if (material_state := _current_paper_material_state(item)) is not None
                    ]
                public["result"] = public_result
            except (OSError, json.JSONDecodeError):
                public["status"] = "failed"
                public["error"] = "分段结果不可读取"
        chunks.append(public)
    stable = state.get("status") in {"ready", "failed", "duplicate", "cancelled", "submitted"}
    return {
        "task_id": task_id,
        "status": state.get("status"),
        "stage": state.get("stage"),
        "files": [
            {key: file.get(key) for key in (
                "file_id", "role", "original_filename", "upload_status", "extraction_status", "error",
            )}
            for file in state.get("files") or []
        ],
        "chunks": chunks,
        "form_preview": _build_form_preview(chunks, state),
        "summary": {
            "status": "completed" if state.get("status") == "ready" else state.get("stage"),
            "completed": state.get("completed_chunks", 0),
            "total": state.get("total_chunks", 0),
        },
        "next_poll_ms": None if stable else 2000,
        "revision": state.get("revision", 0),
    }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _normalize_text_items(value: Any, *keys: str) -> tuple[list[str], list[dict[str, Any]]]:
    texts: list[str] = []
    evidence: list[dict[str, Any]] = []
    for item in _as_list(value):
        raw = item
        if isinstance(item, dict):
            raw = next((item.get(key) for key in keys if item.get(key) not in (None, "")), "")
            item_evidence = item.get("evidence")
            if isinstance(item_evidence, dict):
                evidence.append(item_evidence)
        text = str(raw or "").strip()
        if text and text not in texts:
            texts.append(text)
    return texts, evidence


def _normalize_authors(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(";") if item.strip()]
    return []


def _normalize_author_roles(value: Any, authors: list[str]) -> list[str]:
    selected = {name.casefold() for name in _normalize_authors(value)}
    return [author for author in authors if author.casefold() in selected]


def _flatten_properties(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    rows: list[dict[str, Any]] = []
    for material, properties in value.items():
        for item in _as_list(properties):
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("material", str(material))
                rows.append(row)
    return rows


SPACE_GROUP_NUMBERS = {
    "Fd-3m": 227,
    "P-3m1": 164,
}


def _formula_from_material(value: Any) -> str:
    text = str(value or "").strip()
    try:
        normalize_formula(text)
        return text
    except ValueError:
        pass
    candidates = [
        token
        for token in re.split(r"[^A-Za-z0-9.]+", text)
        if re.fullmatch(r"(?:[A-Z][a-z]?(?:\d+(?:\.\d+)?)?)+", token or "")
    ]
    for candidate in sorted(candidates, key=len, reverse=True):
        try:
            normalize_formula(candidate)
            return candidate
        except ValueError:
            continue
    return text


def _condition_pressure(item: dict[str, Any]) -> tuple[float | None, float | None, float | None, str | None, str | None]:
    condition = item.get("condition") if isinstance(item.get("condition"), dict) else {}
    raw = item.get("pressure_gpa")
    unit = "GPa" if raw not in (None, "") else None
    if raw in (None, ""):
        raw = condition.get("pressure")
        unit = condition.get("pressure_unit")
    if isinstance(raw, dict):
        unit = raw.get("unit") or unit
        raw = raw.get("value")
    if raw in (None, ""):
        return None, None, None, None, unit
    raw_text = str(raw).strip()
    numbers = [
        float(match)
        for match in re.findall(r"[-+]?\d+(?:\.\d+)?", raw_text)
    ]
    if not numbers:
        return None, None, None, raw_text, unit
    if unit and str(unit).strip().lower() != "gpa":
        return None, None, None, raw_text, str(unit)
    if len(numbers) >= 2 and re.search(r"[-–—~～]|\bto\b", raw_text, re.IGNORECASE):
        return None, min(numbers[0], numbers[1]), max(numbers[0], numbers[1]), raw_text, unit or "GPa"
    value = numbers[0]
    return value, None, None, raw_text, unit or "GPa"


def _numeric_value(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else None


def _numeric_range(value: Any) -> tuple[float | None, float | None, float | None]:
    text = str(value or "").strip()
    numbers = [float(item) for item in re.findall(r"[-+]?\d+(?:\.\d+)?", text)]
    if len(numbers) >= 2 and re.search(r"[-–—~～]|\bto\b", text, re.IGNORECASE):
        return None, min(numbers[0], numbers[1]), max(numbers[0], numbers[1])
    return (numbers[0], None, None) if numbers else (None, None, None)


def _legacy_properties_to_material_states(properties: list[dict[str, Any]]) -> list[dict[str, Any]]:
    states: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in properties:
        material = _formula_from_material(item.get("material"))
        pressure_value, pressure_min, pressure_max, pressure_raw, pressure_unit = _condition_pressure(item)
        article_type = item.get("article_type")
        state_kind = "theoretical" if article_type == "t" else "experimental" if article_type == "e" else "unknown"
        key = (material, pressure_value, pressure_min, pressure_max, state_kind)
        state = states.setdefault(key, {
            "material": material,
            "pressure_value_gpa": pressure_value,
            "pressure_min_gpa": pressure_min,
            "pressure_max_gpa": pressure_max,
            "pressure_raw": pressure_raw,
            "pressure_unit_raw": pressure_unit,
            "state_kind": state_kind,
            "reported_space_group_symbol": None,
            "reported_space_group_number": None,
            "structure": None,
            "calculation_context": {
                "phonon_nuclear_treatment": "unknown",
                "lambda_ep": None,
                "omega_log_k": None,
                "mu_star": None,
            } if state_kind == "theoretical" else None,
            "experimental_context": {
                "tc_criterion": "unknown",
            } if state_kind == "experimental" else None,
            "tc_results": [],
            "properties": [],
        })

        raw_name = str(item.get("name_raw") or item.get("name") or "").strip()
        name = str(item.get("name") or raw_name).strip()
        lowered = f"{name} {raw_name}".lower()
        value = item.get("value_raw") if item.get("value_raw") not in (None, "") else item.get("value")
        evidence = item.get("evidence")

        if "space group" in lowered or name.lower() == "crystal structure":
            symbol = str(value or "").strip()
            if symbol:
                state["reported_space_group_symbol"] = symbol
                state["reported_space_group_number"] = SPACE_GROUP_NUMBERS.get(symbol)
                state["space_group_evidence"] = evidence
            continue
        if "electron-phonon coupling" in lowered or raw_name == "λ" or name == "electron_phonon_coupling":
            if state["calculation_context"] is None:
                state["calculation_context"] = {
                    "phonon_nuclear_treatment": "unknown",
                    "lambda_ep": None,
                    "omega_log_k": None,
                    "mu_star": None,
                }
            state["calculation_context"]["lambda_ep"] = _numeric_value(value)
            state["calculation_context"]["evidence"] = evidence
            continue
        if "omega_log" in lowered or "ω_log" in lowered or "ωlog" in lowered:
            if state["calculation_context"] is None:
                state["calculation_context"] = {
                    "phonon_nuclear_treatment": "unknown",
                    "lambda_ep": None,
                    "omega_log_k": None,
                    "mu_star": None,
                }
            state["calculation_context"]["omega_log_k"] = _numeric_value(value)
            state["calculation_context"]["evidence"] = evidence
            continue
        if (
            "critical temperature" in lowered
            or "transition temperature" in lowered
            or name.lower() == "critical_temperature"
            or raw_name.lower() == "tc"
        ):
            tc_value, tc_min, tc_max = _numeric_range(value)
            state["tc_results"].append({
                "result_kind": state_kind if state_kind in {"theoretical", "experimental"} else "theoretical",
                "tc_method": "experimental" if state_kind == "experimental" else "unknown",
                "tc_value_k": tc_value,
                "tc_min_k": tc_min,
                "tc_max_k": tc_max,
                "value_raw": str(value or ""),
                "unit_raw": str(item.get("unit") or "K"),
                "is_representative": bool(item.get("is_primary")),
                "evidence": evidence,
            })
            continue

        property_item = dict(item)
        property_item["material"] = material
        property_item.setdefault("value_raw", str(value or ""))
        state["properties"].append(property_item)
    return list(states.values())


def _normalize_material_states(value: Any) -> list[dict[str, Any]]:
    states = []
    for raw in _as_list(value):
        if not isinstance(raw, dict):
            continue
        if raw.get("scope") == "referenced_work":
            continue
        state = dict(raw)
        state.pop("scope", None)
        state["material"] = _formula_from_material(state.get("material"))
        try:
            _normalized_formula, elements, _composition, _ratios = normalize_formula(state["material"])
            state["element_count"] = len(elements) or None
        except ValueError:
            state["element_count"] = None
        state.pop("phase_label", None)
        family = state.get("material_family")
        if isinstance(family, dict) and family.get("scope") == "referenced_work":
            family = None
        if isinstance(family, str):
            family = {"id": None, "name": family.strip(), "status": "pending"}
        elif isinstance(family, dict):
            family = {
                "id": family.get("id"),
                "name": str(family.get("name") or family.get("value") or "").strip(),
                "status": "confirmed" if family.get("id") not in (None, "") else "pending",
                **({"evidence": family["evidence"]} if isinstance(family.get("evidence"), dict) else {}),
            }
        state["material_family"] = family if isinstance(family, dict) and family.get("name") else None
        structure_families = []
        for structure_family in _as_list(state.get("structure_families")):
            if isinstance(structure_family, str):
                structure_family = {"id": None, "name": structure_family.strip(), "status": "pending"}
            if not isinstance(structure_family, dict):
                continue
            if structure_family.get("scope") == "referenced_work":
                continue
            name = str(structure_family.get("name") or structure_family.get("value") or "").strip()
            if not name:
                continue
            structure_families.append({
                "id": structure_family.get("id"),
                "name": name,
                "status": "confirmed" if structure_family.get("id") not in (None, "") else "pending",
                "is_primary": bool(structure_family.get("is_primary")),
                **({"evidence": structure_family["evidence"]} if isinstance(structure_family.get("evidence"), dict) else {}),
            })
        state["structure_families"] = structure_families
        dimensionality = str(state.get("material_dimensionality") or "unknown")
        if dimensionality not in {
            "zero_dimensional", "one_dimensional", "two_dimensional", "three_dimensional",
            "quasi_one_dimensional", "quasi_two_dimensional", "unknown",
        }:
            dimensionality = "unknown"
        state["material_dimensionality"] = dimensionality
        pressure_value, pressure_min, pressure_max, pressure_raw, pressure_unit = _condition_pressure(state)
        state["pressure_value_gpa"] = _numeric_value(state.get("pressure_value_gpa")) if state.get("pressure_value_gpa") not in (None, "") else pressure_value
        state["pressure_min_gpa"] = _numeric_value(state.get("pressure_min_gpa")) if state.get("pressure_min_gpa") not in (None, "") else pressure_min
        state["pressure_max_gpa"] = _numeric_value(state.get("pressure_max_gpa")) if state.get("pressure_max_gpa") not in (None, "") else pressure_max
        state["pressure_raw"] = state.get("pressure_raw") or pressure_raw
        state["pressure_unit_raw"] = state.get("pressure_unit_raw") or pressure_unit
        if state["pressure_raw"] in (None, "") and state["pressure_value_gpa"] is not None:
            state["pressure_raw"] = str(state["pressure_value_gpa"])
            state["pressure_unit_raw"] = state["pressure_unit_raw"] or "GPa"
        state.setdefault("state_kind", "unknown")
        state.setdefault("reported_space_group_symbol", None)
        if state.get("reported_space_group_number") in (None, ""):
            state["reported_space_group_number"] = SPACE_GROUP_NUMBERS.get(
                str(state.get("reported_space_group_symbol") or "")
            )
        else:
            state["reported_space_group_number"] = int(state["reported_space_group_number"])
        state.setdefault("structure", None)
        calculation = state.get("calculation_context")
        if isinstance(calculation, dict):
            calculation = dict(calculation)
            calculation.setdefault("phonon_nuclear_treatment", "unknown")
            calculation["lambda_ep"] = _numeric_value(
                calculation.get("lambda_ep", calculation.get("lambda"))
            )
            calculation["omega_log_k"] = _numeric_value(
                calculation.get("omega_log_k", calculation.get("wlog"))
            )
            calculation["mu_star"] = _numeric_value(calculation.get("mu_star"))
            state["calculation_context"] = calculation
        else:
            state["calculation_context"] = None
        state.setdefault("experimental_context", None)
        tc_results = []
        for item in _as_list(state.get("tc_results")):
            if not isinstance(item, dict):
                continue
            result = dict(item)
            raw_value = result.get("value_raw") or result.get("value") or result.get("tc_value_k")
            parsed_value, parsed_min, parsed_max = _numeric_range(raw_value)
            result["tc_value_k"] = _numeric_value(result.get("tc_value_k")) if result.get("tc_value_k") not in (None, "") else parsed_value
            result["tc_min_k"] = _numeric_value(result.get("tc_min_k")) if result.get("tc_min_k") not in (None, "") else parsed_min
            result["tc_max_k"] = _numeric_value(result.get("tc_max_k")) if result.get("tc_max_k") not in (None, "") else parsed_max
            result["value_raw"] = str(raw_value or "")
            result.setdefault("unit_raw", result.get("unit") or "K")
            result.setdefault("result_kind", "theoretical" if state["state_kind"] == "theoretical" else "experimental" if state["state_kind"] == "experimental" else "theoretical")
            result.setdefault("tc_method", "experimental" if result["result_kind"] == "experimental" else "unknown")
            result.setdefault("is_representative", False)
            tc_results.append(result)
        state["tc_results"] = tc_results
        state["properties"] = [
            dict(item) for item in _as_list(state.get("properties")) if isinstance(item, dict)
        ]
        states.append(state)
    return states


def _normalize_draft(raw: dict[str, Any]) -> dict[str, Any]:
    parsed = _parse_result(raw)
    raw_paper = raw.get("paper") if isinstance(raw.get("paper"), dict) else raw
    paper_type = str(raw_paper.get("paper_type") or parsed.paper_type or "unknown").strip().lower()
    if paper_type not in {"theoretical", "experimental", "review", "unknown"}:
        paper_type = "unknown"
    subtype = raw_paper.get("theoretical_subtype") if paper_type == "theoretical" else None
    if subtype not in {"calculation", "method", "theory"}:
        subtype = None

    keywords, keywords_evidence = _normalize_text_items(raw_paper.get("keywords_tags"), "keyword", "value", "name")
    methodology, methodology_evidence = _normalize_text_items(raw_paper.get("methodology"), "method", "value", "name")
    research_materials, research_evidence = _normalize_text_items(
        raw_paper.get("research_materials"), "material", "value", "name",
    )
    authors = _normalize_authors(raw_paper.get("authors") or parsed.paper.get("authors"))
    paper = {
        "title": raw_paper.get("title") or parsed.paper.get("title") or "",
        "doi": raw_paper.get("doi") or parsed.paper.get("doi"),
        "authors": authors,
        "corresponding_authors": _normalize_author_roles(raw_paper.get("corresponding_authors"), authors),
        "co_first_authors": _normalize_author_roles(raw_paper.get("co_first_authors"), authors),
        "journal": raw_paper.get("journal") or parsed.paper.get("journal"),
        "volume": raw_paper.get("volume"),
        "pages": raw_paper.get("pages"),
        "year": raw_paper.get("year") or parsed.paper.get("year"),
        "abstract": raw_paper.get("abstract") or parsed.paper.get("abstract"),
        "summary": raw_paper.get("summary") or parsed.summary or "",
        "paper_type": paper_type,
        "theoretical_subtype": subtype,
        "keywords_tags": keywords or _normalize_text_items(parsed.keywords_tags, "keyword", "value", "name")[0],
        "methodology": methodology,
        "key_finding": raw_paper.get("key_finding") or "",
        "rationale": raw_paper.get("rationale") or raw.get("classification_reason") or "",
        "research_materials": research_materials,
        "material_relations": _as_list(raw_paper.get("material_relations")),
        "builds_on": _as_list(raw_paper.get("builds_on")),
    }
    properties = _flatten_properties(raw.get("key_properties"))
    for item in properties:
        item.setdefault("name_raw", item.get("name") or "")
        if item.get("value_raw") in (None, "") and item.get("value") not in (None, ""):
            item["value_raw"] = str(item["value"])
        item.setdefault("condition", {})
        item.setdefault("is_primary", False)
        if item.get("article_type") not in {"e", "t"}:
            item["article_type"] = None
        evidence = item.get("evidence")
        item["evidence"] = evidence if isinstance(evidence, dict) else {
            "section": "",
            "page": None,
            "quote": str(item.pop("quote", "") or ""),
        }
    existing_field_evidence = raw.get("field_evidence")
    field_evidence = dict(existing_field_evidence) if isinstance(existing_field_evidence, dict) else {}
    field_evidence.pop("referenced_materials", None)
    for field, values in {
        "keywords_tags": keywords_evidence,
        "methodology": methodology_evidence,
        "research_materials": research_evidence,
    }.items():
        if values:
            field_evidence[field] = values

    material_states = _normalize_material_states(raw.get("material_states"))
    if not material_states and properties:
        material_states = _legacy_properties_to_material_states(properties)

    return {
        "paper": paper,
        "material_states": material_states,
        "structure_candidates": [
            item for item in _as_list(raw.get("structure_candidates"))
            if isinstance(item, dict)
        ],
        "classification_reason": raw.get("classification_reason") or paper["rationale"],
        "classification_evidence": _as_list(raw.get("classification_evidence")),
        "field_evidence": field_evidence,
    }


def empty_draft() -> dict[str, Any]:
    return _normalize_draft({"paper": {"paper_type": "unknown"}, "material_states": []})


def normalize_doi(value: Any) -> str | None:
    doi = str(value or "").strip()
    if not doi:
        return None
    lowered = doi.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if lowered.startswith(prefix):
            doi = doi[len(prefix):].strip()
            break
    return doi or None


def _existing_paper_query(db):
    return db.query(
        Paper.id,
        Paper.doi,
        Paper.review_status,
        Paper.uploaded_by_user_id,
        PaperFile.stored_path.label("main_stored_path"),
        PaperFile.sha256.label("main_sha256"),
    ).outerjoin(
        PaperFile,
        and_(PaperFile.paper_id == Paper.id, PaperFile.role == "main"),
    )


def _find_existing_paper(doi: str | None) -> Any | None:
    normalized = normalize_doi(doi)
    if not normalized:
        return None
    db = SessionLocal()
    try:
        candidates = _existing_paper_query(db).filter(
            func.lower(Paper.doi).contains(normalized.lower())
        ).all()
        return next(
            (paper for paper in candidates if (normalize_doi(paper.doi) or "").lower() == normalized.lower()),
            None,
        )
    finally:
        db.close()


def _find_existing_by_hash(state: dict[str, Any]) -> Any | None:
    expected = str(state.get("file_sha256") or "")
    if not expected:
        return None
    db = SessionLocal()
    try:
        return _existing_paper_query(db).filter(
            func.lower(PaperFile.sha256) == expected.lower()
        ).first()
    finally:
        db.close()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _handle_duplicate(task_id: str, state: dict[str, Any], existing: Any) -> dict[str, Any]:
    source = _original_path(state)
    source_sha256 = str(state.get("file_sha256") or "") or sha256_file(source)
    existing_sha256 = str(getattr(existing, "main_sha256", None) or "")
    same_file = bool(existing_sha256 and source_sha256.lower() == existing_sha256.lower())
    shutil.rmtree(artifact_directory(task_id), ignore_errors=True)
    markdown_path(task_id).unlink(missing_ok=True)

    candidate_path: Path | None = None
    if same_file:
        source.unlink(missing_ok=True)
        action = "duplicate_deleted"
    else:
        candidate_dir = data_path("upload_PDFs") / "candidates" / str(existing.id)
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = candidate_dir / f"{task_id}{source.suffix.lower()}"
        shutil.move(str(source), str(candidate_path))
        candidate_path.with_suffix(".json").write_text(
            json.dumps(
                {
                    "existing_paper_id": existing.id,
                    "doi": existing.doi,
                    "task_id": task_id,
                    "user_id": state.get("user_id"),
                    "filename": state.get("filename"),
                    "file_sha256": state.get("file_sha256") or sha256_file(candidate_path),
                    "created_at": state.get("created_at"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        action = "candidate_saved"

    can_view = existing.review_status in {"approved", "pending"} or (
        existing.review_status == "rejected"
        and int(existing.uploaded_by_user_id or 0) == int(state.get("user_id") or 0)
    )
    allowed_actions = ["view"] if can_view else []
    if can_view and int(existing.uploaded_by_user_id or 0) == int(state.get("user_id") or 0):
        allowed_actions.append("edit")
    duplicate = update_state(
        task_id,
        status="duplicate",
        stage="ready",
        stage_index=5,
        processing_status="succeeded",
        processing_error=None,
        duplicate=True,
        existing_paper_id=existing.id,
        existing_paper_status=existing.review_status,
        allowed_actions=allowed_actions,
        duplicate_reason=("数据库中已有该论文" if can_view else "数据库中已有该论文，但当前账号无权查看"),
        duplicate_file_action=action,
        candidate_attachment=str(candidate_path) if candidate_path else None,
        state_schema_version=UPLOAD_STATE_SCHEMA_VERSION,
    )
    _schedule_terminal_cleanup(task_id)
    return duplicate


def process_upload_task(task_id: str) -> dict[str, Any]:
    """Extract, read every chunk, and build an editable draft."""
    state = get_state(task_id)
    if not state:
        raise RuntimeError("上传任务不存在或已过期")
    try:
        _ensure_not_cancelled(task_id)
        source = _original_path(state)
        existing_by_hash = _find_existing_by_hash(state)
        if existing_by_hash:
            return _handle_duplicate(task_id, state, existing_by_hash)
        md_path = markdown_path(task_id)
        update_state(
            task_id, status="extracting", stage="extracting", stage_index=2, processing_status="processing",
            processing_error=None, error_code=None,
        )
        multi_file = bool(state.get("files"))
        sources = state.get("files") or [{
            "file_id": "main", "role": "main", "original_filename": state.get("filename"),
            "kind": state.get("file_kind"), "stored_path": str(source),
        }]
        extracted_root = data_path("parsed_markdown") / task_id
        extracted_root.mkdir(parents=True, exist_ok=True)
        all_chunks: list[tuple[dict[str, Any], Chunk]] = []
        combined_markdown: list[str] = []
        identities: list[dict[str, Any]] = []
        structure_candidates: list[dict[str, Any]] = []
        for file_item in sources:
            _ensure_not_cancelled(task_id)
            file_source = Path(str(file_item.get("stored_path") or source))
            file_state = {**state, "file_kind": file_item.get("kind") or file_source.suffix.lstrip(".")}
            file_md = extracted_root / f"{file_item['file_id']}.md"
            structure_format = _structure_format_for_file(file_item, file_source)
            if multi_file:
                file_item["extraction_status"] = "processing"
                update_state(task_id, files=sources)
            try:
                if structure_format:
                    structure_ok = False
                    source_info = {
                        "file_id": file_item.get("file_id"),
                        "filename": file_item.get("original_filename") or file_source.name,
                        "role": file_item.get("role"),
                        "page": None,
                        "quote": None,
                    }
                    try:
                        structure_text = file_source.read_text(encoding="utf-8")
                        structure_candidates.append(build_structure_candidate(
                            structure_format=structure_format,
                            structure_text=structure_text,
                            material_state_ref=f"unassigned:{file_item['file_id']}",
                            source=source_info,
                        ))
                        structure_ok = True
                    except (OSError, UnicodeDecodeError, StructureCandidateError) as structure_exc:
                        structure_candidates.append({
                            "candidate_id": f"blocked:{file_item['file_id']}",
                            "material_state_ref": f"unassigned:{file_item['file_id']}",
                            "source_kind": "attachment",
                            "status": "blocked",
                            "confirmation": "unreviewed",
                            "original_format": structure_format,
                            "original_text": None,
                            "validation": {
                                "ase_valid": False,
                                "code": getattr(structure_exc, "code", "structure_read_failed"),
                                "message": str(structure_exc),
                            },
                            "derivation": None,
                            "representations": {},
                            "sources": [source_info],
                            "conflicts": [],
                            "user_note": None,
                        })
                    markdown = (
                        f"<!-- 结构附件 {file_item.get('original_filename') or file_source.name} 已通过 ASE 校验 -->"
                        if structure_ok else
                        f"<!-- 结构附件 {file_item.get('original_filename') or file_source.name} 校验失败，等待人工处理 -->"
                    )
                elif not multi_file and md_path.exists():
                    markdown = md_path.read_text(encoding="utf-8")
                elif file_md.exists():
                    markdown = file_md.read_text(encoding="utf-8")
                else:
                    markdown = _extract_markdown(file_state, file_source)
                    file_md.write_text(markdown, encoding="utf-8")
                if not structure_format and str(file_item.get("kind") or file_state.get("file_kind") or "").lower() == "pdf":
                    structure_candidates.extend(extract_structure_candidates(
                        markdown,
                        source={
                            "file_id": file_item.get("file_id"),
                            "filename": file_item.get("original_filename") or file_source.name,
                            "role": file_item.get("role"),
                        },
                    ))
            except Exception as extraction_exc:
                if multi_file:
                    file_item["extraction_status"] = "failed"
                    file_item["error"] = str(extraction_exc)
                    update_state(task_id, files=sources)
                raise
            if multi_file:
                file_item["extraction_status"] = "completed"
                file_item["error"] = None
                update_state(task_id, files=sources)
            combined_markdown.append(
                f"\n\n# 来源文件：{file_item.get('original_filename') or file_source.name}\n\n{markdown}"
            )
            identities.append(_lightweight_identity(file_item, markdown))
            if not structure_format:
                for chunk in _chunks_with_preamble(markdown):
                    all_chunks.append((file_item, chunk))
        md_path.write_text("".join(combined_markdown), encoding="utf-8")
        update_state(task_id, consistency=compare_file_identities(identities))
        if not all_chunks:
            raise ValueError("论文正文为空，无法生成可校对草稿")
        manifest = [
            {
                "chunk_id": f"{item['file_id']}:{chunk.chunk_index}",
                "file_id": item["file_id"],
                "filename": item.get("original_filename"),
                "file_role": item.get("role"),
                "index": chunk.chunk_index,
                "section": chunk.section_name or "正文",
                "page_start": getattr(chunk, "source_page", None),
                "page_end": getattr(chunk, "source_page", None),
                "status": "waiting",
                "error": None,
                "cache_file_id": item["file_id"] if multi_file else None,
            }
            for item, chunk in all_chunks
        ]
        _save_chunk_manifest(task_id, manifest)
        update_state(
            task_id, status="reading", stage="reading", stage_index=3,
            completed_chunks=0, total_chunks=len(all_chunks),
        )
        candidates: list[dict[str, Any]] = []
        for completed, (file_item, chunk) in enumerate(all_chunks, start=1):
            _ensure_not_cancelled(task_id)
            manifest[completed - 1]["status"] = "processing"
            _save_chunk_manifest(task_id, manifest)
            try:
                if multi_file:
                    candidates.append(_read_chunk(task_id, chunk, file_item["file_id"], file_item))
                else:
                    candidates.append(_read_chunk(task_id, chunk))
                manifest[completed - 1]["status"] = "completed"
            except Exception as chunk_exc:
                manifest[completed - 1]["status"] = "failed"
                manifest[completed - 1]["error"] = str(chunk_exc)
                _save_chunk_manifest(task_id, manifest)
                raise
            _save_chunk_manifest(task_id, manifest)
            update_state(task_id, completed_chunks=completed, total_chunks=len(all_chunks))

        _ensure_not_cancelled(task_id)
        update_state(task_id, status="summarizing", stage="summarizing", stage_index=4)
        summary_candidates = _summary_classification_candidates(candidates)
        raw_draft = complete_json(
            SUMMARY_SYSTEM_PROMPT,
            json.dumps(summary_candidates, ensure_ascii=False),
        )
        draft = _normalize_draft(raw_draft)
        draft["structure_candidates"] = structure_candidates
        current_state = get_state(task_id) or state
        existing = _find_existing_paper(draft["paper"].get("doi")) or _find_existing_by_hash(current_state)
        if existing:
            return _handle_duplicate(task_id, current_state, existing)

        ai_values = json.loads(json.dumps(draft, ensure_ascii=False))
        draft["ai_original"] = ai_values
        artifact_path(task_id).write_text(
            json.dumps(
                {
                    "task_id": task_id,
                    "paper_id": None,
                    "ai_values": ai_values,
                    "user_values": None,
                    "evidence": {
                        "classification": draft.get("classification_evidence", []),
                        "classification_scope": _classification_scope_evidence(candidates),
                        "material_states": [
                            {
                                "space_group": item.get("space_group_evidence"),
                                "calculation_context": (
                                    item.get("calculation_context") or {}
                                ).get("evidence"),
                                "tc_results": [
                                    result.get("evidence")
                                    for result in item.get("tc_results") or []
                                    if isinstance(result, dict)
                                ],
                            }
                            for item in draft["material_states"]
                        ],
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        save_draft(task_id, draft)
        ready = update_state(
            task_id, status="ready", stage="ready", stage_index=5, processing_status="succeeded",
            processing_error=None, completed_chunks=len(all_chunks), total_chunks=len(all_chunks), duplicate=False,
        )
        _schedule_terminal_cleanup(task_id)
        return ready
    except UploadCancelled:
        current = get_state(task_id)
        if current and current.get("status") == "cancelling":
            cancelled = update_state(
                task_id, status="cancelled", processing_status="cancelled", processing_error=None,
            )
            _schedule_terminal_cleanup(task_id)
            return cancelled
        return current or {"task_id": task_id, "status": "cancelled"}
    except Exception as exc:
        current = get_state(task_id) or state
        update_state(
            task_id, status="failed", processing_status="failed", processing_error=str(exc),
            error_code="paper_processing_failed", failed_stage=current.get("stage"),
        )
        _schedule_terminal_cleanup(task_id)
        raise
