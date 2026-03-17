"""
将 HydrideLiteratureData 输出的 superconductor_data_reviewed.xlsx 导入数据库。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import zipfile
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend import crud, models


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS = {"a": MAIN_NS}

META_HEADERS = [
    "filename",
    "doi",
    "title",
    "author",
    "abstract",
    "year",
    "article_type",
    "superconductor_type",
    "chemical_formula_total",
    "crystal_structure",
]
POINT_FIELDS = ["chemical_formula", "pressure", "tc", "lambda", "omega_log", "n_ef"]

ARTICLE_TYPE_MAP = {
    "t": "theoretical",
    "theoretical": "theoretical",
    "e": "experimental",
    "experimental": "experimental",
}

SC_TYPE_MAP = {
    "c": "cuprate",
    "cuprate": "cuprate",
    "i": "iron_based",
    "iron_based": "iron_based",
    "n": "nickel_based",
    "nickel_based": "nickel_based",
    "h": "hydride",
    "hydride": "hydride",
    "cb": "carbon",
    "carbon": "carbon",
    "or": "organic",
    "organic": "organic",
    "ot": "others",
    "others": "others",
}


def col_to_index(ref: str) -> int:
    match = re.match(r"([A-Z]+)", ref)
    if not match:
        raise ValueError(f"无法解析单元格坐标: {ref}")
    value = 0
    for ch in match.group(1):
        value = value * 26 + ord(ch) - 64
    return value - 1


def read_cell(cell: ET.Element) -> str | None:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        node = cell.find("a:is", NS)
        if node is None:
            return None
        return "".join(item.text or "" for item in node.iterfind(".//a:t", NS))

    value = cell.find("a:v", NS)
    return None if value is None else value.text


def read_xlsx_rows(path: Path) -> tuple[list[str], list[list[str | None]]]:
    with zipfile.ZipFile(path) as zf:
        worksheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        sheet_data = worksheet.find("a:sheetData", NS)
        if sheet_data is None:
            raise ValueError("sheet1.xml 缺少 sheetData")

        sparse_rows: list[dict[int, str | None]] = []
        max_col = 0
        for row in sheet_data.findall("a:row", NS):
            values: dict[int, str | None] = {}
            for cell in row.findall("a:c", NS):
                idx = col_to_index(cell.attrib["r"])
                max_col = max(max_col, idx + 1)
                values[idx] = read_cell(cell)
            sparse_rows.append(values)

    headers = [sparse_rows[0].get(i) or "" for i in range(max_col)]
    rows = [[sparse.get(i) for i in range(max_col)] for sparse in sparse_rows[1:]]
    return headers, rows


def parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    if math.isnan(result):
        return None
    return result


def parse_int(value: str | None) -> int | None:
    number = parse_float(value)
    return None if number is None else int(number)


def normalize_article_type(value: str | None) -> str:
    key = (value or "").strip().lower()
    return ARTICLE_TYPE_MAP.get(key, "theoretical")


def normalize_superconductor_type(value: str | None) -> str:
    key = (value or "").strip().lower()
    return SC_TYPE_MAP.get(key, "others")


def extract_elements(*formulas: str | None) -> list[str]:
    symbols: set[str] = set()
    for formula in formulas:
        if not formula:
            continue
        for symbol in re.findall(r"[A-Z][a-z]?", str(formula)):
            symbols.add(symbol)
    return sorted(symbols)


def normalize_authors(value: str | None) -> str:
    if not value:
        return "[]"
    text = str(value).strip()
    if not text:
        return "[]"
    if text.startswith("["):
        return text

    if ";" in text:
        parts = [item.strip() for item in text.split(";") if item.strip()]
    else:
        parts = [text]
    return json.dumps(parts, ensure_ascii=False)


def iter_points(row: list[str | None], max_points: int) -> Iterable[dict[str, object | None]]:
    for point_index in range(1, max_points + 1):
        start = len(META_HEADERS) + (point_index - 1) * len(POINT_FIELDS)
        formula = row[start] if start < len(row) else None
        tc = parse_float(row[start + 2]) if start + 2 < len(row) else None
        if formula in (None, "") or tc is None:
            continue
        yield {
            "chemical_formula": formula,
            "pressure": parse_float(row[start + 1]) if start + 1 < len(row) else None,
            "tc": tc,
            "lambda_val": parse_float(row[start + 3]) if start + 3 < len(row) else None,
            "omega_log": parse_float(row[start + 4]) if start + 4 < len(row) else None,
            "n_ef": parse_float(row[start + 5]) if start + 5 < len(row) else None,
        }


def build_surrogate_doi(row: list[str | None]) -> str:
    basis = "|".join(
        [
            str(row[0] or ""),
            str(row[2] or ""),
            str(row[8] or ""),
            str(row[5] or ""),
        ]
    )
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]
    return f"10.99999/xlsx-import-{digest}"


def build_notes(row: list[str | None], source_path: Path, doi_was_generated: bool) -> str:
    parts = [f"Imported from reviewed xlsx: {source_path.name}"]
    filename = row[0]
    if filename:
        parts.append(f"source_file={filename}")
    if doi_was_generated:
        parts.append("doi_generated_from_row_content=true")
    return " | ".join(parts)


def import_reviewed_xlsx(xlsx_path: str) -> None:
    source_path = Path(xlsx_path).resolve()
    if not source_path.exists():
        raise SystemExit(f"文件不存在: {source_path}")

    headers, rows = read_xlsx_rows(source_path)
    max_points = max(0, (len(headers) - len(META_HEADERS)) // len(POINT_FIELDS))

    db: Session = SessionLocal()
    stats = {
        "rows_total": 0,
        "rows_skipped_no_points": 0,
        "rows_skipped_no_elements": 0,
        "papers_inserted": 0,
        "papers_skipped_existing": 0,
        "paper_data_inserted": 0,
        "generated_doi": 0,
    }

    try:
        for row in rows:
            stats["rows_total"] += 1

            points = list(iter_points(row, max_points))
            if not points:
                stats["rows_skipped_no_points"] += 1
                continue

            total_formula = row[8]
            point_formulas = [str(point["chemical_formula"]) for point in points]
            elements = extract_elements(total_formula, *point_formulas)
            compound = crud.get_or_create_compound(db, elements)
            if compound is None:
                stats["rows_skipped_no_elements"] += 1
                continue

            raw_doi = (row[1] or "").strip()
            doi_was_generated = raw_doi == ""
            doi = raw_doi or build_surrogate_doi(row)
            if doi_was_generated:
                stats["generated_doi"] += 1

            existing = (
                db.query(models.Paper)
                .filter(models.Paper.compound_id == compound.id, models.Paper.doi == doi)
                .first()
            )
            if existing:
                stats["papers_skipped_existing"] += 1
                continue

            paper = models.Paper(
                compound_id=compound.id,
                doi=doi,
                title=(row[2] or row[0] or f"Imported from {source_path.name}"),
                article_type=normalize_article_type(row[6]),
                superconductor_type=normalize_superconductor_type(row[7]),
                authors=normalize_authors(row[3]),
                journal="",
                volume="",
                pages="",
                year=parse_int(row[5]),
                abstract=row[4] or "",
                citation_aps="",
                citation_bibtex="",
                chemical_formula=total_formula or point_formulas[0],
                crystal_structure=row[9] or "",
                contributor_name="HydrideLiteratureData Import",
                contributor_affiliation="System",
                notes=build_notes(row, source_path, doi_was_generated),
            )
            db.add(paper)
            db.flush()

            for point in points:
                db.add(
                    models.PaperData(
                        paper_id=paper.id,
                        pressure=point["pressure"],
                        tc=point["tc"],
                        lambda_val=point["lambda_val"],
                        omega_log=point["omega_log"],
                        n_ef=point["n_ef"],
                        s_factor=crud.compute_s_factor(point["pressure"], point["tc"]),
                    )
                )
                stats["paper_data_inserted"] += 1

            stats["papers_inserted"] += 1

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"源文件: {source_path}")
    print(f"总行数: {stats['rows_total']}")
    print(f"插入 papers: {stats['papers_inserted']}")
    print(f"跳过已存在 papers: {stats['papers_skipped_existing']}")
    print(f"插入 paper_data: {stats['paper_data_inserted']}")
    print(f"生成占位 DOI: {stats['generated_doi']}")
    print(f"跳过无数据点行: {stats['rows_skipped_no_points']}")
    print(f"跳过无有效元素行: {stats['rows_skipped_no_elements']}")


if __name__ == "__main__":
    import sys

    input_file = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "/home/guoqiang/workspace/HydrideLiteratureData/Results/superconductor_data_reviewed.xlsx"
    )
    import_reviewed_xlsx(input_file)
