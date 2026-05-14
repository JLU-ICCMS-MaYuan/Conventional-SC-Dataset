#!/usr/bin/env python3
"""Import MinerU markdown/images into SQLite with staged extraction."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
MIN_IMAGE_BYTES = 10 * 1024
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
FIG_RE = re.compile(r"(?i)^(fig\.?|figure\.?|图\s*\d+)")

PERIODIC_SYMBOLS = [
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
    "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
    "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
]
ELEMENT_ID_MAP = {sym: i + 1 for i, sym in enumerate(PERIODIC_SYMBOLS)}
ELEMENTS_SEED_ROWS = [
    (1, "H", "Hydrogen", "氢", 1),
    (2, "He", "Helium", "氦", 2),
    (3, "Li", "Lithium", "锂", 3),
    (4, "Be", "Beryllium", "铍", 4),
    (5, "B", "Boron", "硼", 5),
    (6, "C", "Carbon", "碳", 6),
    (7, "N", "Nitrogen", "氮", 7),
    (8, "O", "Oxygen", "氧", 8),
    (9, "F", "Fluorine", "氟", 9),
    (10, "Ne", "Neon", "氖", 10),
    (11, "Na", "Sodium", "钠", 11),
    (12, "Mg", "Magnesium", "镁", 12),
    (13, "Al", "Aluminum", "铝", 13),
    (14, "Si", "Silicon", "硅", 14),
    (15, "P", "Phosphorus", "磷", 15),
    (16, "S", "Sulfur", "硫", 16),
    (17, "Cl", "Chlorine", "氯", 17),
    (18, "Ar", "Argon", "氩", 18),
    (19, "K", "Potassium", "钾", 19),
    (20, "Ca", "Calcium", "钙", 20),
    (21, "Sc", "Scandium", "钪", 21),
    (22, "Ti", "Titanium", "钛", 22),
    (23, "V", "Vanadium", "钒", 23),
    (24, "Cr", "Chromium", "铬", 24),
    (25, "Mn", "Manganese", "锰", 25),
    (26, "Fe", "Iron", "铁", 26),
    (27, "Co", "Cobalt", "钴", 27),
    (28, "Ni", "Nickel", "镍", 28),
    (29, "Cu", "Copper", "铜", 29),
    (30, "Zn", "Zinc", "锌", 30),
    (31, "Ga", "Gallium", "镓", 31),
    (32, "Ge", "Germanium", "锗", 32),
    (33, "As", "Arsenic", "砷", 33),
    (34, "Se", "Selenium", "硒", 34),
    (35, "Br", "Bromine", "溴", 35),
    (36, "Kr", "Krypton", "氪", 36),
    (37, "Rb", "Rubidium", "铷", 37),
    (38, "Sr", "Strontium", "锶", 38),
    (39, "Y", "Yttrium", "钇", 39),
    (40, "Zr", "Zirconium", "锆", 40),
    (41, "Nb", "Niobium", "铌", 41),
    (42, "Mo", "Molybdenum", "钼", 42),
    (43, "Tc", "Technetium", "锝", 43),
    (44, "Ru", "Ruthenium", "钌", 44),
    (45, "Rh", "Rhodium", "铑", 45),
    (46, "Pd", "Palladium", "钯", 46),
    (47, "Ag", "Silver", "银", 47),
    (48, "Cd", "Cadmium", "镉", 48),
    (49, "In", "Indium", "铟", 49),
    (50, "Sn", "Tin", "锡", 50),
    (51, "Sb", "Antimony", "锑", 51),
    (52, "Te", "Tellurium", "碲", 52),
    (53, "I", "Iodine", "碘", 53),
    (54, "Xe", "Xenon", "氙", 54),
    (55, "Cs", "Cesium", "铯", 55),
    (56, "Ba", "Barium", "钡", 56),
    (57, "La", "Lanthanum", "镧", 57),
    (58, "Ce", "Cerium", "铈", 58),
    (59, "Pr", "Praseodymium", "镨", 59),
    (60, "Nd", "Neodymium", "钕", 60),
    (61, "Pm", "Promethium", "钷", 61),
    (62, "Sm", "Samarium", "钐", 62),
    (63, "Eu", "Europium", "铕", 63),
    (64, "Gd", "Gadolinium", "钆", 64),
    (65, "Tb", "Terbium", "铽", 65),
    (66, "Dy", "Dysprosium", "镝", 66),
    (67, "Ho", "Holmium", "钬", 67),
    (68, "Er", "Erbium", "铒", 68),
    (69, "Tm", "Thulium", "铥", 69),
    (70, "Yb", "Ytterbium", "镱", 70),
    (71, "Lu", "Lutetium", "镥", 71),
    (72, "Hf", "Hafnium", "铪", 72),
    (73, "Ta", "Tantalum", "钽", 73),
    (74, "W", "Tungsten", "钨", 74),
    (75, "Re", "Rhenium", "铼", 75),
    (76, "Os", "Osmium", "锇", 76),
    (77, "Ir", "Iridium", "铱", 77),
    (78, "Pt", "Platinum", "铂", 78),
    (79, "Au", "Gold", "金", 79),
    (80, "Hg", "Mercury", "汞", 80),
    (81, "Tl", "Thallium", "铊", 81),
    (82, "Pb", "Lead", "铅", 82),
    (83, "Bi", "Bismuth", "铋", 83),
    (84, "Po", "Polonium", "钋", 84),
    (85, "At", "Astatine", "砹", 85),
    (86, "Rn", "Radon", "氡", 86),
    (87, "Fr", "Francium", "钫", 87),
    (88, "Ra", "Radium", "镭", 88),
    (89, "Ac", "Actinium", "锕", 89),
    (90, "Th", "Thorium", "钍", 90),
    (91, "Pa", "Protactinium", "镤", 91),
    (92, "U", "Uranium", "铀", 92),
    (93, "Np", "Neptunium", "镎", 93),
    (94, "Pu", "Plutonium", "钚", 94),
    (95, "Am", "Americium", "镅", 95),
    (96, "Cm", "Curium", "锔", 96),
    (97, "Bk", "Berkelium", "锫", 97),
    (98, "Cf", "Californium", "锎", 98),
    (99, "Es", "Einsteinium", "锿", 99),
    (100, "Fm", "Fermium", "镄", 100),
    (101, "Md", "Mendelevium", "钔", 101),
    (102, "No", "Nobelium", "锘", 102),
    (103, "Lr", "Lawrencium", "铹", 103),
    (104, "Rf", "Rutherfordium", "鈩", 104),
    (105, "Db", "Dubnium", "𨧀", 105),
    (106, "Sg", "Seaborgium", "𨭎", 106),
    (107, "Bh", "Bohrium", "𨨏", 107),
    (108, "Hs", "Hassium", "𨭆", 108),
    (109, "Mt", "Meitnerium", "鿏", 109),
    (110, "Ds", "Darmstadtium", "𫟼", 110),
    (111, "Rg", "Roentgenium", "𬬻", 111),
    (112, "Cn", "Copernicium", "鿔", 112),
    (113, "Nh", "Nihonium", "鿭", 113),
    (114, "Fl", "Flerovium", "𫓧", 114),
    (115, "Mc", "Moscovium", "镆", 115),
    (116, "Lv", "Livermorium", "𫟷", 116),
    (117, "Ts", "Tennessine", "石田", 117),
    (118, "Og", "Oganesson", "气奥", 118),
]

PAPER_KEYS = ("doi", "title", "authors", "journal", "volume", "pages", "year", "abstract")
DATA_POINT_KEYS = (
    "article_type",
    "superconductor_type",
    "chemical_formula",
    "crystal_structure",
    "tc",
    "tc_press",
    "lambda_val",
    "omega_log",
    "n_ef",
    "sample_name",
    "data_source_note",
)

SYSTEM_PROMPT = """You are a materials science expert specializing in superconductors. Extract structured data from the given literature text with high precision.

Return a JSON object with these exact fields:
{
  "paper": {
    "doi": string|null,
    "title": string|null,
    "authors": string|null,
    "journal": string|null,
    "volume": string|null,
    "pages": string|null,
    "year": integer|null,
    "abstract": string|null
  },
  "data_points": [
    {
      "article_type": string|null,
      "superconductor_type": string|null,
      "chemical_formula": string|null,
      "crystal_structure": string|null,
      "tc": [number|null] | [number|null, number|null] | null,
      "tc_press": [number|null] | [number|null, number|null] | null,
      "lambda_val": number|null,
      "omega_log": number|null,
      "n_ef": number|null,
      "sample_name": string|null,
      "data_source_note": string|null
    }
  ]
}

Field constraints:
- article_type: ONE OF "e" (experimental) OR "t" (theoretical), or null if unknown
- superconductor_type: ONE OF "c" (cuprate), "i" (iron-based), "n" (nickel-based), "h" (hydride), "cb" (carbon-based), "or" (organic), "ot" (others), or null if unknown
- crystal_structure priority:
  1) International space group symbol (e.g., "Im-3m", "Fm-3m", "P6/mmm")
  2) Structure description (e.g., "tetragonal", "cubic", "layered")
  3) null
- Each item in data_points must represent ONE independent measurement/condition:
  * Different conditions for the MAIN research object -> separate item
  * Different Tc/pressure conditions for same composition -> separate item
  * Different reported datasets -> separate item
  * ONLY include data for the paper's primary studied material/system.
  * The primary studied object may include MULTIPLE compounds when they are part of
    the same core research series in this paper (e.g., "XH3, X = Al, Ba, Li").
    In such cases, include all those primary-series compounds.
  * EXCLUDE comparison materials, cited prior-work materials, benchmark examples,
    hypothetical side examples, or any non-primary object mentioned in passing.
  * If multiple compounds are mentioned, keep only the one(s) that the paper directly
    claims to synthesize/measure/calculate as its core result.
  * For non-superconducting papers (only synthesis/structure), still output data_points with
    chemical_formula and/or crystal_structure when available.

Numeric extraction rules:
- tc format: [tc] for a single value, or [tc_min, tc_max] for a range
  * tc in K
  * range like "10-15 K" -> tc uses [10, 15]
  * "above X K" / "below X K" -> tc extracts [X]
- tc_press format: [pressure] for a single value, or [pressure_min, pressure_max] for a range
  * pressure in GPa
  * do NOT use synthesis pressure as superconducting pressure
  * use 0 only if ambient-pressure superconducting Tc is explicitly reported
- lambda_val corresponds to λ (electron-phonon coupling)
- omega_log is logarithmic average phonon frequency
- n_ef is DOS at Fermi level

Physical plausibility checks:
- tc (if present) must be > 0 K (otherwise null)
- pressure (if present) must be >= 0 GPa (otherwise null)
- lambda_val usually in 0-3; if clearly abnormal and uncertain, prefer null

Ambiguity handling:
- Multiple values for same condition: choose the primary/concluded value
- Conflicting values: prioritize Abstract > Conclusion > Results > Tables
- Incomplete or unclear statements: only extract explicit values

Missing data policy:
- Use null, NEVER use empty string or "N/A"
- Do not invent or extrapolate
- For synthesis-only/structure-only entries, it is valid that tc/lambda_val/omega_log/n_ef
  are null while chemical_formula/crystal_structure are present.

Output validation:
- Ensure valid JSON syntax
- All fields must be present
- data_points must be an array (use [] if none)

Important Notice:
If the text consists of garbled characters, such as:
"qrsIJ tu7v, wxyz{|}sIJt
u~s E~s   @9{ ^ ,     sIJ
   G
       v  #      8¡    ¢h
1 23"
then return:
{
  "paper": {
    "doi": null,
    "title": "Contains garbled characters",
    "authors": null,
    "journal": null,
    "volume": null,
    "pages": null,
    "year": null,
    "abstract": null
  },
  "data_points": []
}

Return ONLY the JSON object, no additional text, explanations, or markdown formatting."""

FIG_TRANSLATE_PROMPT = """Translate figure captions from English to Simplified Chinese.
Return JSON object only:
{
  "captions_cn": ["...", "..."]
}
Rules:
- Keep scientific symbols/formulas/units unchanged (e.g., Tc, λ, ωlog, GPa, K, H3S, Im-3m).
- Keep numbering labels like (a), (b), Fig. 1.
- Keep array length exactly equal to input captions.
- If a caption is already Chinese, keep it as is.
- No extra commentary."""


@dataclass
class ParsedDoc:
    paper: dict[str, Any]
    data_points: list[dict[str, Any]]


def normalize_formula(formula: str | None) -> str | None:
    if not formula:
        return None
    cleaned = re.sub(r"\s+", "", formula)
    cleaned = re.sub(r"[^A-Za-z0-9\(\)\[\]\+\-\.,]", "", cleaned)
    return cleaned or None


def clean_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    s = doi.strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
    return s.strip() or None


def to_text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    m = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_numeric_range(value: Any) -> list[float | None] | None:
    if not isinstance(value, list) or not value or len(value) > 2:
        return None
    normalized = [to_float(item) for item in value]
    cleaned = [item for item in normalized if item is not None]
    if not cleaned:
        return None
    if len(cleaned) == 2 and cleaned[0] > cleaned[1]:
        cleaned.sort()
    return cleaned


def calc_s_factor(tc_range: list[float | None] | None, pressure_range: list[float | None] | None) -> float | None:
    if not tc_range or not pressure_range:
        return None
    tc_values = [v for v in tc_range if v is not None]
    pressure_values = [v for v in pressure_range if v is not None]
    if not tc_values or not pressure_values:
        return None
    tc = sum(tc_values[:2]) / min(len(tc_values), 2)
    pressure = sum(pressure_values[:2]) / min(len(pressure_values), 2)
    return tc / ((1521 + pressure * pressure) ** 0.5)


def parse_formula_counts(formula: str | None) -> dict[str, int]:
    if not formula:
        return {}
    out: dict[str, int] = {}
    for sym, num in re.findall(r"([A-Z][a-z]?)(\d*)", formula):
        n = int(num) if num else 1
        out[sym] = out.get(sym, 0) + n
    return out


def gcd_int(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def reduce_counts(counts: dict[str, int]) -> dict[str, int]:
    vals = [v for v in counts.values() if v > 0]
    if not vals:
        return {}
    g = vals[0]
    for v in vals[1:]:
        g = gcd_int(g, v)
    if g <= 1:
        return dict(counts)
    return {k: v // g for k, v in counts.items()}


def parse_title(md_text: str) -> str | None:
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip() or None
    return None


def normalize_paper_title_for_merge(title: str | None) -> str | None:
    if not title:
        return None
    t = re.sub(r"\s+", " ", title).strip()
    # Remove common SI/supporting markers.
    t = re.sub(
        r"(?i)\b(supporting information|supporting info|supplementary information|supplementary material[s]?|supplemental material[s]?|appendix|supporting data|supplementary data)\b",
        "",
        t,
    )
    t = re.sub(r"(补充材料|支撑材料|附录)", "", t)
    # Remove trailing short suffix forms like -SI, -Supp, -Suppl, (SI), _SI.
    t = re.sub(r"(?i)[\(\[\{]\s*(si|supp|suppl|sm)\s*[\)\]\}]\s*$", "", t)
    t = re.sub(r"(?i)[\s\-_:/]*(si|supp|suppl|sm)\s*$", "", t)
    t = re.sub(r"\s+", " ", t).strip(" -_:/;,.")
    return t.casefold() if t else None


def parse_doi(md_text: str) -> str | None:
    m = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", md_text, flags=re.IGNORECASE)
    return m.group(0) if m else None


def parse_year(md_text: str, path: Path) -> int | None:
    m = re.search(r"\b(19\d{2}|20\d{2})\b", path.as_posix())
    if m:
        return int(m.group(1))
    m = re.search(r"\b(19\d{2}|20\d{2})\b", md_text[:4000])
    return int(m.group(1)) if m else None


def heuristic_parse(md_text: str, md_path: Path) -> ParsedDoc:
    return ParsedDoc(
        paper={
            "doi": parse_doi(md_text),
            "title": parse_title(md_text),
            "authors": None,
            "journal": None,
            "volume": None,
            "pages": None,
            "year": parse_year(md_text, md_path),
            "abstract": None,
        },
        data_points=[],
    )


def llm_parse(md_text: str, model: str) -> ParsedDoc:
    from openai import OpenAI

    client = OpenAI(api_key=__import__("os").environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": md_text[:18000]},
        ],
        response_format={"type": "json_object"},
    )
    usage = resp.usage
    if usage is not None:
        print(
            f"  Tokens — prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens}, "
            f"cache hit: {usage.prompt_cache_hit_tokens}, cache miss: {usage.prompt_cache_miss_tokens}"
        )
    payload = json.loads(resp.choices[0].message.content)
    return ParsedDoc(paper=payload.get("paper", {}) or {}, data_points=payload.get("data_points", []) or [])


def llm_translate_captions(captions: list[str], model: str) -> list[str]:
    if not captions:
        return []

    from openai import OpenAI

    client = OpenAI(api_key=__import__("os").environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": FIG_TRANSLATE_PROMPT},
            {"role": "user", "content": json.dumps({"captions": captions}, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
    )
    payload = json.loads(resp.choices[0].message.content)
    out = payload.get("captions_cn")
    if isinstance(out, list) and len(out) == len(captions):
        return [str(x) if x is not None else "" for x in out]
    return list(captions)


def normalize_parsed_doc(parsed: ParsedDoc, md_text: str, md_path: Path) -> ParsedDoc:
    paper_in = parsed.paper if isinstance(parsed.paper, dict) else {}
    paper = {k: None for k in PAPER_KEYS}
    for k in PAPER_KEYS:
        paper[k] = paper_in.get(k)

    paper["doi"] = clean_doi(to_text(paper.get("doi")) or parse_doi(md_text))
    paper["title"] = to_text(paper.get("title")) or parse_title(md_text)
    paper["authors"] = to_text(paper.get("authors"))
    paper["journal"] = to_text(paper.get("journal"))
    paper["volume"] = to_text(paper.get("volume"))
    paper["pages"] = to_text(paper.get("pages"))
    paper["year"] = to_int(paper.get("year")) or parse_year(md_text, md_path)
    paper["abstract"] = to_text(paper.get("abstract"))

    points_out: list[dict[str, Any]] = []
    points_in = parsed.data_points if isinstance(parsed.data_points, list) else []
    for raw in points_in:
        if not isinstance(raw, dict):
            continue
        p = {k: None for k in DATA_POINT_KEYS}
        for k in DATA_POINT_KEYS:
            p[k] = raw.get(k)

        p["article_type"] = to_text(p["article_type"])
        p["superconductor_type"] = to_text(p["superconductor_type"])
        p["chemical_formula"] = to_text(p["chemical_formula"])
        p["crystal_structure"] = to_text(p["crystal_structure"])
        p["tc"] = parse_numeric_range(p["tc"])
        p["tc_press"] = parse_numeric_range(p["tc_press"])
        p["lambda_val"] = to_float(p["lambda_val"])
        p["omega_log"] = to_float(p["omega_log"])
        p["n_ef"] = to_float(p["n_ef"])
        p["sample_name"] = to_text(p["sample_name"])
        p["data_source_note"] = to_text(p["data_source_note"])

        has_payload = any(
            p.get(k) is not None
            for k in (
                "chemical_formula",
                "crystal_structure",
                "tc",
                "tc_press",
                "lambda_val",
                "omega_log",
                "n_ef",
            )
        )
        if has_payload:
            points_out.append(p)

    return ParsedDoc(paper=paper, data_points=points_out)


def fetch_crossref(doi: str, timeout: int = 20) -> dict[str, Any] | None:
    clean = clean_doi(doi)
    if not clean:
        return None

    url = f"https://api.crossref.org/works/{quote(clean)}"
    try:
        with urlopen(url, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8", errors="ignore"))
    except (URLError, HTTPError, TimeoutError, ValueError):
        return None

    msg = payload.get("message", {})
    title = (msg.get("title") or [None])[0]
    journal = (msg.get("container-title") or [None])[0]

    authors_arr = msg.get("author") or []
    authors = []
    for a in authors_arr:
        given = (a.get("given") or "").strip()
        family = (a.get("family") or "").strip()
        name = " ".join(x for x in [given, family] if x).strip()
        if name:
            authors.append(name)

    year = None
    for key in ("published-print", "published-online", "issued"):
        parts = (((msg.get(key) or {}).get("date-parts") or [[None]])[0])
        if parts and isinstance(parts[0], int):
            year = parts[0]
            break

    abstract = msg.get("abstract")
    if isinstance(abstract, str):
        abstract = re.sub(r"<[^>]+>", "", abstract).strip() or None
    else:
        abstract = None

    return {
        "title": title,
        "authors": "; ".join(authors) if authors else None,
        "journal": journal,
        "volume": msg.get("volume"),
        "pages": msg.get("page"),
        "year": year,
        "abstract": abstract,
        "is_referenced_by_count": msg.get("is-referenced-by-count"),
    }


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doi TEXT,
            paper_images_id INTEGER,
            title TEXT,
            authors TEXT,
            journal TEXT,
            volume TEXT,
            pages TEXT,
            year INTEGER,
            abstract TEXT,
            imagetxts TEXT,
            imagetxts_cn TEXT,
            "is-referenced-by-count" INTEGER
        );

        CREATE TABLE IF NOT EXISTS compounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chemical_formula TEXT,
            element_list TEXT,
            composition TEXT,
            element_id_list TEXT,
            element_ratio TEXT
        );

        CREATE TABLE IF NOT EXISTS paper_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id INTEGER,
            compound_id INTEGER,
            article_type TEXT,
            superconductor_type TEXT,
            chemical_formula TEXT,
            crystal_structure TEXT,
            tc TEXT,
            tc_press TEXT,
            lambda_val REAL,
            omega_log REAL,
            n_ef REAL,
            s_factor REAL,
            sample_name TEXT,
            data_source_note TEXT,
            sequence_in_paper INTEGER,
            FOREIGN KEY (paper_id) REFERENCES papers(id),
            FOREIGN KEY (compound_id) REFERENCES compounds(id)
        );

        CREATE TABLE IF NOT EXISTS paper_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id INTEGER,
            figs TEXT,
            image_data BLOB,
            thumbnail_data BLOB,
            image_order INTEGER,
            fig1 BLOB, fig2 BLOB, fig3 BLOB, fig4 BLOB, fig5 BLOB,
            fig6 BLOB, fig7 BLOB, fig8 BLOB, fig9 BLOB, fig10 BLOB,
            fig11 BLOB, fig12 BLOB, fig13 BLOB, fig14 BLOB, fig15 BLOB,
            fig16 BLOB, fig17 BLOB, fig18 BLOB, fig19 BLOB, fig20 BLOB,
            fig21 BLOB, fig22 BLOB, fig23 BLOB, fig24 BLOB, fig25 BLOB,
            fig26 BLOB, fig27 BLOB, fig28 BLOB, fig29 BLOB, fig30 BLOB,
            fig31 BLOB, fig32 BLOB, fig33 BLOB, fig34 BLOB, fig35 BLOB,
            fig36 BLOB, fig37 BLOB, fig38 BLOB, fig39 BLOB, fig40 BLOB,
            file_size INTEGER,
            created_at TEXT,
            FOREIGN KEY (paper_id) REFERENCES papers(id)
        );

        CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
        CREATE INDEX IF NOT EXISTS idx_paper_data_paper ON paper_data(paper_id);
        CREATE INDEX IF NOT EXISTS idx_paper_data_compound ON paper_data(compound_id);
        CREATE INDEX IF NOT EXISTS idx_paper_images_paper ON paper_images(paper_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_compounds_formula ON compounds(chemical_formula);
        """
    )
    conn.commit()


def ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    info = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {r[1] for r in info}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN \"{column}\" {col_type}")
        conn.commit()


def ensure_compat_columns(conn: sqlite3.Connection) -> None:
    ensure_column(conn, "papers", "paper_images_id", "INTEGER")
    ensure_column(conn, "papers", "imagetxts", "TEXT")
    ensure_column(conn, "papers", "imagetxts_cn", "TEXT")
    ensure_column(conn, "papers", "is-referenced-by-count", "INTEGER")
    ensure_column(conn, "compounds", "element_list", "TEXT")
    ensure_column(conn, "compounds", "composition", "TEXT")
    ensure_column(conn, "compounds", "element_id_list", "TEXT")
    ensure_column(conn, "compounds", "element_ratio", "TEXT")
    ensure_column(conn, "paper_data", "tc", "TEXT")
    ensure_column(conn, "paper_data", "tc_press", "TEXT")
    ensure_column(conn, "paper_images", "figs", "TEXT")
    for i in range(1, 41):
        ensure_column(conn, "paper_images", f"fig{i}", "BLOB")


def ensure_elements_table(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='elements' LIMIT 1"
    ).fetchone()
    if row:
        return

    conn.executescript(
        """
        CREATE TABLE elements (
            id INTEGER PRIMARY KEY,
            symbol TEXT UNIQUE,
            name TEXT,
            name_zh TEXT,
            atomic_number INTEGER UNIQUE
        );
        CREATE INDEX idx_elements_symbol ON elements(symbol);
        CREATE INDEX idx_elements_atomic_number ON elements(atomic_number);
        """
    )

    conn.executemany(
        "INSERT INTO elements (id, symbol, name, name_zh, atomic_number) VALUES (?, ?, ?, ?, ?)",
        ELEMENTS_SEED_ROWS,
    )
    conn.commit()


def upsert_paper_stub(conn: sqlite3.Connection, md_path: Path, md_text: str) -> int:
    h = heuristic_parse(md_text, md_path).paper
    doi = clean_doi(h.get("doi"))
    title = h.get("title")
    year = h.get("year")

    if doi:
        row = conn.execute("SELECT id FROM papers WHERE doi=? LIMIT 1", (doi,)).fetchone()
        if row:
            return int(row[0])

    if title:
        norm_title = normalize_paper_title_for_merge(title)
        rows = conn.execute("SELECT id, title FROM papers WHERE year IS ?", (year,)).fetchall()
        for row_id, row_title in rows:
            if normalize_paper_title_for_merge(row_title) == norm_title:
                return int(row_id)

    cur = conn.execute("INSERT INTO papers (doi,title,year) VALUES (?,?,?)", (doi, title, year))
    return int(cur.lastrowid)


def find_existing_paper_id(conn: sqlite3.Connection, md_path: Path, md_text: str) -> int | None:
    h = heuristic_parse(md_text, md_path).paper
    doi = clean_doi(h.get("doi"))
    title = h.get("title")
    year = h.get("year")

    if doi:
        row = conn.execute("SELECT id FROM papers WHERE doi=? LIMIT 1", (doi,)).fetchone()
        if row:
            return int(row[0])

    if title:
        norm_title = normalize_paper_title_for_merge(title)
        rows = conn.execute("SELECT id, title FROM papers WHERE year IS ?", (year,)).fetchall()
        for row_id, row_title in rows:
            if normalize_paper_title_for_merge(row_title) == norm_title:
                return int(row_id)
    return None


def extract_figure_blocks(md_path: Path) -> list[dict[str, Any]]:
    lines = md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    blocks: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        if not IMG_RE.search(lines[i]):
            i += 1
            continue

        img_refs: list[str] = []
        j = i
        while j < len(lines):
            line = lines[j]
            m = IMG_RE.search(line)
            if m:
                img_refs.append(m.group(1).strip())
                j += 1
                continue
            if not line.strip():
                j += 1
                continue
            break

        if not img_refs or j >= len(lines):
            i = j
            continue

        first = lines[j].strip()
        # 有效图片组要求：连续图片后第一条非空行必须是 FIG/Figure/图 开头。
        if not FIG_RE.match(first):
            i = j
            continue

        cap = [first]
        j += 1
        while j < len(lines):
            line = lines[j]
            if IMG_RE.search(line) or not line.strip():
                break
            cap.append(line.strip())
            j += 1

        blocks.append({"images": img_refs, "caption": " ".join(cap).strip(), "md": md_path})
        i = j
    return blocks


def collect_valid_images(md_path: Path, refs: list[str]) -> list[Path]:
    items: list[Path] = []
    for r in refs:
        # Markdown 中的图片相对路径以当前 .md 所在目录为基准解析。
        p = (md_path.parent / r).resolve()
        if p.exists() and p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES and p.stat().st_size >= MIN_IMAGE_BYTES:
            items.append(p)
    return items


def update_paper_image_texts(conn: sqlite3.Connection, paper_id: int, imagetxts: list[str], imagetxts_cn: list[str]) -> None:
    conn.execute(
        "UPDATE papers SET imagetxts=?, imagetxts_cn=? WHERE id=?",
        (
            json.dumps(imagetxts, ensure_ascii=False),
            json.dumps(imagetxts_cn, ensure_ascii=False),
            paper_id,
        ),
    )


def replace_paper_images(conn: sqlite3.Connection, paper_id: int, figs: list[int], images: list[bytes]) -> tuple[int, int | None]:
    conn.execute("DELETE FROM paper_images WHERE paper_id=?", (paper_id,))
    # 每篇文献在 paper_images 仅保留一行，最多写入 40 张图片到 BLOB 列。
    images = images[:40]
    values = images + [None] * (40 - len(images))
    total_size = sum(len(x) for x in images)
    cur = conn.execute(
        """
        INSERT INTO paper_images (
            paper_id, figs, image_data, thumbnail_data, image_order,
            fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig9, fig10,
            fig11, fig12, fig13, fig14, fig15, fig16, fig17, fig18, fig19, fig20,
            fig21, fig22, fig23, fig24, fig25, fig26, fig27, fig28, fig29, fig30,
            fig31, fig32, fig33, fig34, fig35, fig36, fig37, fig38, fig39, fig40,
            file_size, created_at
        ) VALUES (
            ?, ?, NULL, NULL, NULL,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, datetime('now')
        )
        """,
        (paper_id, json.dumps(figs, ensure_ascii=False), *values, total_size),
    )
    image_row_id = int(cur.lastrowid)
    conn.execute("UPDATE papers SET paper_images_id=? WHERE id=?", (image_row_id, paper_id))
    return len(images), image_row_id


def update_paper_fields(conn: sqlite3.Connection, paper_id: int, paper: dict[str, Any]) -> None:
    conn.execute(
        """
        UPDATE papers
        SET doi=COALESCE(?,doi),
            title=COALESCE(?,title),
            authors=COALESCE(?,authors),
            journal=COALESCE(?,journal),
            volume=COALESCE(?,volume),
            pages=COALESCE(?,pages),
            year=COALESCE(?,year),
            abstract=COALESCE(?,abstract)
        WHERE id=?
        """,
        (
            clean_doi(paper.get("doi")),
            paper.get("title"),
            paper.get("authors"),
            paper.get("journal"),
            paper.get("volume"),
            paper.get("pages"),
            paper.get("year"),
            paper.get("abstract"),
            paper_id,
        ),
    )


def enrich_with_crossref(conn: sqlite3.Connection, paper_id: int, doi: str) -> bool:
    data = fetch_crossref(doi)
    if not data:
        return False

    conn.execute(
        """
        UPDATE papers
        SET title=?, authors=?, journal=?, volume=?, pages=?, year=?, abstract=?,
            "is-referenced-by-count"=?
        WHERE id=?
        """,
        (
            data.get("title"),
            data.get("authors"),
            data.get("journal"),
            data.get("volume"),
            data.get("pages"),
            data.get("year"),
            data.get("abstract"),
            data.get("is_referenced_by_count"),
            paper_id,
        ),
    )
    return True


def get_or_create_compound(conn: sqlite3.Connection, formula: str | None) -> int | None:
    normalized = normalize_formula(formula)
    if not normalized:
        return None

    row = conn.execute("SELECT id FROM compounds WHERE chemical_formula=? LIMIT 1", (normalized,)).fetchone()
    if row:
        return int(row[0])

    counts = parse_formula_counts(normalized)
    if not counts:
        return None

    elements = sorted(counts.keys())
    composition: list[Any] = []
    for e in elements:
        composition.extend([e, counts[e]])

    reduced = reduce_counts(counts)
    element_ratio: list[Any] = []
    for e in elements:
        element_ratio.extend([e, reduced[e]])

    element_ids = [ELEMENT_ID_MAP[e] for e in elements if e in ELEMENT_ID_MAP]

    cur = conn.execute(
        """
        INSERT INTO compounds (chemical_formula, element_list, composition, element_id_list, element_ratio)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            normalized,
            json.dumps(elements, ensure_ascii=False),
            json.dumps(composition, ensure_ascii=False),
            json.dumps(element_ids, ensure_ascii=False),
            json.dumps(element_ratio, ensure_ascii=False),
        ),
    )
    return int(cur.lastrowid)


def replace_paper_data(conn: sqlite3.Connection, paper_id: int, points: list[dict[str, Any]]) -> int:
    conn.execute("DELETE FROM paper_data WHERE paper_id=?", (paper_id,))
    n = 0
    for idx, p in enumerate(points, start=1):
        formula = p.get("chemical_formula")
        compound_id = get_or_create_compound(conn, formula)
        conn.execute(
            """
            INSERT INTO paper_data (
                paper_id, compound_id, article_type, superconductor_type, chemical_formula,
                crystal_structure, tc, tc_press, lambda_val, omega_log, n_ef, s_factor,
                sample_name, data_source_note, sequence_in_paper
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                compound_id,
                p.get("article_type"),
                p.get("superconductor_type"),
                p.get("chemical_formula"),
                p.get("crystal_structure"),
                json.dumps(p.get("tc"), ensure_ascii=False) if p.get("tc") is not None else None,
                json.dumps(p.get("tc_press"), ensure_ascii=False) if p.get("tc_press") is not None else None,
                p.get("lambda_val"),
                p.get("omega_log"),
                p.get("n_ef"),
                calc_s_factor(p.get("tc"), p.get("tc_press")),
                p.get("sample_name"),
                p.get("data_source_note"),
                idx,
            ),
        )
        n += 1
    return n


def iter_mineru_md_files(root: Path) -> list[Path]:
    return sorted([p for p in root.rglob("*.md") if p.parent.name == "auto"])


def is_supplementary_name(name: str) -> bool:
    n = name.casefold()
    return bool(
        re.search(
            r"(?:^|[\s\-_()\[\]])(si|supp|suppl|supplementary|supporting\s*information|supporting\s*info|sm)(?:$|[\s\-_()\[\]])",
            n,
        )
    ) or ("补充" in n) or ("支撑材料" in n)


def canonical_doc_name(name: str) -> str:
    n = name.casefold()
    n = re.sub(
        r"(supporting\s*information|supporting\s*info|supplementary|supplemental|supp|suppl|si|sm|补充材料|支撑材料)",
        "",
        n,
    )
    n = re.sub(r"[\s\-_()\[\]:]+", " ", n).strip()
    return n


def build_paper_jobs(root: Path, md_files: list[Path]) -> list[tuple[Path, list[Path]]]:
    groups: dict[tuple[str, str], list[Path]] = {}
    for md in md_files:
        paper_folder = md.parent.parent.name if md.parent.name == "auto" else md.parent.name
        category = md.parent.parent.parent if md.parent.name == "auto" and len(md.parents) >= 3 else md.parent
        category_key = category.relative_to(root).as_posix() if category.is_relative_to(root) else category.as_posix()
        key = (category_key, canonical_doc_name(paper_folder))
        groups.setdefault(key, []).append(md)

    jobs: list[tuple[Path, list[Path]]] = []
    for _, files in sorted(groups.items()):
        files = sorted(files)
        main_candidates = [
            p for p in files if not is_supplementary_name(p.stem) and not is_supplementary_name(p.parent.parent.name)
        ]
        main = main_candidates[0] if main_candidates else files[0]
        supp = [p for p in files if p != main]
        jobs.append((main, supp))
    return jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Import MinerU outputs into SQLite")
    # 按用户要求使用短参数：--in 指输入 MinerU 根目录，--out 指输出数据库路径。
    parser.add_argument("--in", dest="input_root", required=True, help="MinerU root folder")
    parser.add_argument(
        "--out",
        dest="output_db",
        default=None,
        help="SQLite file path OR existing directory. If omitted, use <in>/mineru_import.db",
    )
    parser.add_argument("--max-papers", type=int, default=0)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--llm-model", default="deepseek-chat")
    args = parser.parse_args()

    root = Path(args.input_root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Invalid --in: {root}")

    if args.output_db is None:
        db = root / "mineru_import.db"
    else:
        db_input = Path(args.output_db).expanduser()
        # If user passes an existing directory, place default DB file inside it.
        if db_input.exists() and db_input.is_dir():
            db = db_input / "mineru_import.db"
        # Also support paths ending with slash as directory intent.
        elif str(args.output_db).endswith(("/", "\\")):
            db_input.mkdir(parents=True, exist_ok=True)
            db = db_input / "mineru_import.db"
        else:
            db = db_input
    db = db.resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    use_llm = not args.no_llm

    md_files = iter_mineru_md_files(root)
    # 主文献与补充材料合并为一个导入任务。
    jobs = build_paper_jobs(root, md_files)
    if args.max_papers > 0:
        jobs = jobs[:args.max_papers]

    print(f"MinerU root: {root}")
    print(f"DB path: {db}")
    print(f"Found auto markdown files: {len(md_files)}")
    print(f"Resolved paper jobs (main + supplementary merged): {len(jobs)}")
    print(f"DeepSeek enabled: {use_llm}")
    if not jobs:
        print("No markdown files found under auto/; nothing to import.")
        return

    conn = sqlite3.connect(db.as_posix())
    create_schema(conn)
    ensure_compat_columns(conn)
    ensure_elements_table(conn)

    papers_n = 0
    images_n = 0
    data_n = 0
    crossref_n = 0
    failed_n = 0
    skipped_n = 0

    for i, (main_md, supp_mds) in enumerate(jobs, start=1):
        try:
            md_text = main_md.read_text(encoding="utf-8", errors="ignore")
            if supp_mds:
                for s in supp_mds:
                    s_text = s.read_text(encoding="utf-8", errors="ignore")
                    md_text += f"\n\n# Supplementary Material: {s.stem}\n\n{s_text}"
            print(f"[{i}/{len(jobs)}] {main_md}")
            print(f"  supplementary merged: {len(supp_mds)}")

            # 断点续跑：数据库已存在同一篇文献时直接跳过。
            existed_id = find_existing_paper_id(conn, main_md, md_text)
            if existed_id is not None:
                skipped_n += 1
                print(f"  skip existing paper_id={existed_id}")
                continue

            paper_id = upsert_paper_stub(conn, main_md, md_text)
            blocks: list[dict[str, Any]] = []
            for md in [main_md] + supp_mds:
                blocks.extend(extract_figure_blocks(md))

            imagetxts: list[str] = []
            figs: list[int] = []
            image_bytes_all: list[bytes] = []
            for b in blocks:
                items = collect_valid_images(Path(b["md"]), b["images"])
                if not items:
                    continue
                imgs = [p.read_bytes() for p in items]
                imagetxts.append(b["caption"])
                figs.append(len(imgs))
                image_bytes_all.extend(imgs)

            imagetxts_cn = list(imagetxts)
            if use_llm and imagetxts:
                try:
                    # 翻译为尽力而为策略；失败时回退为原始图注。
                    imagetxts_cn = llm_translate_captions(imagetxts, args.llm_model)
                except Exception as exc:
                    print(f"  Caption translate failed, fallback original captions: {exc}")
            update_paper_image_texts(conn, paper_id, imagetxts, imagetxts_cn)
            img_count, first_image_id = replace_paper_images(conn, paper_id, figs, image_bytes_all)
            print(f"  paper_id={paper_id}, fig_blocks={len(imagetxts)}, images={img_count}, paper_images_id={first_image_id}")

            if use_llm:
                try:
                    parsed = llm_parse(md_text, args.llm_model)
                except Exception as exc:
                    print(f"  DeepSeek parse failed, fallback heuristic: {exc}")
                    parsed = heuristic_parse(md_text, main_md)
            else:
                parsed = heuristic_parse(md_text, main_md)

            parsed = normalize_parsed_doc(parsed, md_text, main_md)
            update_paper_fields(conn, paper_id, parsed.paper)

            doi = clean_doi(parsed.paper.get("doi")) or parse_doi(md_text)
            if doi and enrich_with_crossref(conn, paper_id, doi):
                crossref_n += 1

            points = replace_paper_data(conn, paper_id, parsed.data_points)

            conn.commit()
            papers_n += 1
            images_n += img_count
            data_n += points
        except Exception as exc:
            conn.rollback()
            failed_n += 1
            print(f"  ERROR: {exc}")

    print("\nImport completed.")
    print(f"Papers: {papers_n}")
    print(f"Paper data rows: {data_n}")
    print(f"Images: {images_n}")
    print(f"Crossref enriched: {crossref_n}")
    print(f"Skipped existing: {skipped_n}")
    print(f"Failed: {failed_n}")


if __name__ == "__main__":
    main()
