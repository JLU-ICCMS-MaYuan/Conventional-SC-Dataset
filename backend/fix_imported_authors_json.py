"""
将 HydrideLiteratureData Import 导入的普通字符串 authors 修正为 JSON 字符串数组。
"""

from __future__ import annotations

import json

from backend.database import SessionLocal
from backend import models


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


def main() -> None:
    db = SessionLocal()
    updated = 0
    try:
        papers = (
            db.query(models.Paper)
            .filter(models.Paper.contributor_name == "HydrideLiteratureData Import")
            .all()
        )
        for paper in papers:
            normalized = normalize_authors(paper.authors)
            if paper.authors != normalized:
                paper.authors = normalized
                updated += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"修正 authors 记录数: {updated}")


if __name__ == "__main__":
    main()
