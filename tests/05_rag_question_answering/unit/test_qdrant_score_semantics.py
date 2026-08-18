"""Qdrant cosine score 的公共返回语义。"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

pytest.importorskip("qdrant_client")

from backend.rag import vectordb


@dataclass
class _Point:
    id: int
    score: float
    payload: dict


class _QdrantBoundary:
    def query_points(self, **_: object) -> SimpleNamespace:
        return SimpleNamespace(
            points=[
                _Point(1, 0.92, {"paper_id": "7", "chunk_index": 2, "document": "相关"}),
                _Point(2, 0.31, {"paper_id": "8", "chunk_index": 1, "document": "较弱"}),
            ]
        )


def test_vector_search_exposes_qdrant_similarity_score_without_inversion(monkeypatch) -> None:
    monkeypatch.setattr(vectordb, "_get_client", lambda: _QdrantBoundary())

    results = vectordb.search_chunks([0.1, 0.2], top_k=2)

    assert [result["score"] for result in results] == [0.92, 0.31]
    assert all("distance" not in result for result in results)
