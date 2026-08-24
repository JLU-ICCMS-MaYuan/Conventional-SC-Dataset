from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.models import Paper, PaperFile


ROOT = Path(__file__).resolve().parents[2]


def test_upload_task_id_is_unique_and_multifile_transaction_rolls_back(sqlite_engine):
    Session = sessionmaker(bind=sqlite_engine, future=True)
    task_id = "f" * 32
    with pytest.raises(RuntimeError, match="rollback"):
        with Session.begin() as session:
            paper = Paper(title="paper", review_status="pending", upload_task_id=task_id)
            session.add(paper)
            session.flush()
            session.add(PaperFile(
                paper_id=paper.id, role="main", original_filename="paper.pdf",
                stored_path="upload_PDFs/task/paper.pdf", sha256="a" * 64, size=3, sort_order=0,
            ))
            raise RuntimeError("rollback")
    with Session() as session:
        assert session.query(Paper).count() == 0
        assert session.query(PaperFile).count() == 0

    with Session.begin() as session:
        session.add(Paper(title="one", review_status="pending", upload_task_id=task_id))
    with pytest.raises(IntegrityError):
        with Session.begin() as session:
            session.add(Paper(title="two", review_status="pending", upload_task_id=task_id))


def test_frontend_contract_has_three_upload_workers_and_server_countdown():
    multi = (ROOT / "frontend/src/components/MultiFileUploadPanel.tsx").read_text(encoding="utf-8")
    center = (ROOT / "frontend/src/components/UploadTaskCenter.tsx").read_text(encoding="utf-8")
    detail = (ROOT / "frontend/src/components/UploadParsingDetail.tsx").read_text(encoding="utf-8")

    assert "Math.min(3, queue.length)" in multi
    assert "cleanup_at" in center and "setInterval" in center and "等待清理" in center
    assert "/api/upload-tasks/${taskId}/parsing" in detail
    assert "/activity" not in detail


def test_parsing_detail_filters_prompt_and_internal_paths(tmp_path, monkeypatch):
    import json
    from backend.ingest import upload_jobs

    task_id = "e" * 32
    monkeypatch.setattr(upload_jobs, "get_state", lambda _task_id: {
        "task_id": task_id, "status": "reading", "stage": "reading",
        "completed_chunks": 1, "total_chunks": 1, "revision": 2, "files": [],
    })
    artifact_root = tmp_path / "review_artifacts"
    task_root = artifact_root / task_id
    monkeypatch.setattr(upload_jobs, "data_path", lambda _name: artifact_root)
    manifest = task_root / "chunks/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"items": [{
        "chunk_id": "main:0", "file_id": "main", "index": 0,
        "status": "completed", "cache_file_id": None,
    }]}), encoding="utf-8")
    (task_root / "chunks/00000.json").write_text(json.dumps({
        "metadata": {"title": "Safe"}, "key_properties": [],
        "prompt": "secret prompt", "raw_response": "secret response",
        "file_path": "/data/private",
    }), encoding="utf-8")

    detail = upload_jobs.public_parsing_detail(task_id)
    result = detail["chunks"][0]["result"]

    assert result["metadata"]["title"] == "Safe"
    assert "prompt" not in result
    assert "raw_response" not in result
    assert "file_path" not in result


def test_parsing_detail_get_does_not_create_artifact_directory(tmp_path, monkeypatch):
    from backend.ingest import upload_jobs

    task_id = "d" * 32
    monkeypatch.setattr(upload_jobs, "get_state", lambda _task_id: {
        "task_id": task_id, "status": "reading", "stage": "reading", "files": [],
    })
    monkeypatch.setattr(upload_jobs, "data_path", lambda name: tmp_path / name)

    detail = upload_jobs.public_parsing_detail(task_id)

    assert detail["chunks"] == []
    assert not (tmp_path / "review_artifacts" / task_id).exists()


def test_parsing_detail_builds_one_read_only_form_with_conflicting_sourced_candidates(tmp_path, monkeypatch):
    import json
    from backend.ingest import upload_jobs

    task_id = "c" * 32
    monkeypatch.setattr(upload_jobs, "get_state", lambda _task_id: {
        "task_id": task_id, "status": "reading", "stage": "reading",
        "completed_chunks": 2, "total_chunks": 2, "revision": 4,
        "files": [
            {"file_id": "main", "role": "main", "original_filename": "paper.pdf"},
            {"file_id": "supp", "role": "supplementary", "original_filename": "supp.pdf"},
        ],
    })
    artifact_root = tmp_path / "review_artifacts"
    task_root = artifact_root / task_id
    monkeypatch.setattr(upload_jobs, "data_path", lambda _name: artifact_root)
    manifest = task_root / "chunks/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"items": [
        {
            "chunk_id": "main:0", "file_id": "main", "filename": "paper.pdf",
            "file_role": "main", "index": 0, "section": "Title", "page_start": 1,
            "page_end": 1, "status": "completed", "cache_file_id": "main", "error": None,
        },
        {
            "chunk_id": "supp:0", "file_id": "supp", "filename": "supp.pdf",
            "file_role": "supplementary", "index": 0, "section": "Cover", "page_start": 2,
            "page_end": 2, "status": "completed", "cache_file_id": "supp", "error": None,
        },
    ]}), encoding="utf-8")
    for file_id, title, material in (
        ("main", "Hydride under pressure", "LaH10"),
        ("supp", "Supplement to hydride study", "LaH10"),
    ):
        result = task_root / f"chunks/{file_id}/00000.json"
        result.parent.mkdir(parents=True)
        result.write_text(json.dumps({
            "metadata": {"title": title, "doi": "10.1000/example", "authors": ["A. Author"]},
            "research_materials": [{"value": material, "page": 1, "quote": "We study LaH10."}],
            "key_properties": [],
        }), encoding="utf-8")

    detail = upload_jobs.public_parsing_detail(task_id)
    fields = {
        field["path"]: field
        for group in detail["form_preview"]["groups"]
        for field in group["fields"]
    }

    assert detail["form_preview"]["read_only"] is True
    assert fields["paper.title"]["state"] == "conflict"
    assert {candidate["value"] for candidate in fields["paper.title"]["candidates"]} == {
        "Hydride under pressure", "Supplement to hydride study",
    }
    assert {source["filename"] for candidate in fields["paper.title"]["candidates"] for source in candidate["sources"]} == {
        "paper.pdf", "supp.pdf",
    }
    assert fields["paper.research_materials"]["state"] == "filled"
    assert [candidate["value"] for candidate in fields["paper.research_materials"]["candidates"]] == ["LaH10"]


def test_parsing_detail_scopes_li_mg_h_classification_without_hiding_references(tmp_path, monkeypatch):
    import json
    from backend.ingest import upload_jobs

    task_id = "4" * 32
    monkeypatch.setattr(upload_jobs, "get_state", lambda _task_id: {
        "task_id": task_id, "status": "reading", "stage": "reading",
        "completed_chunks": 1, "total_chunks": 2, "revision": 5,
        "files": [{
            "file_id": "main", "role": "main",
            "original_filename": "2019 Li-Mg-H-孙莹.pdf",
        }],
    })
    artifact_root = tmp_path / "review_artifacts"
    task_root = artifact_root / task_id
    monkeypatch.setattr(upload_jobs, "data_path", lambda _name: artifact_root)
    manifest = task_root / "chunks/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"items": [{
        "chunk_id": "main:0", "file_id": "main", "filename": "2019 Li-Mg-H-孙莹.pdf",
        "file_role": "main", "index": 0, "section": "全文", "page_start": 1,
        "page_end": 2, "status": "completed", "cache_file_id": "main", "error": None,
    }]}), encoding="utf-8")
    result_path = task_root / "chunks/main/00000.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(json.dumps({
        "paper_type_evidence": [
            {
                "candidate": "unknown", "scope": "current_paper", "page": 1,
                "quote": "Route to a Superconducting Phase above Room Temperature",
            },
            {
                "candidate": "theoretical", "scope": "current_paper", "page": 2,
                "quote": "The phase diagram is constructed through structure searching simulations.",
            },
            {
                "candidate": "experimental", "scope": "referenced_work", "page": 1,
                "quote": "Subsequent experimental work found two superconducting states.",
            },
            {
                "candidate": "review", "scope": "referenced_work", "page": 2,
                "quote": "There have been few studies on compressed ternary hydrides.",
            },
            {
                "candidate": "experimental", "page": 1,
                "quote": "Legacy cached evidence without a scope.",
            },
        ],
        "sc_type_candidates": [
            {
                "value": "高压三元氢化物超导体", "scope": "current_paper", "page": 1,
                "quote": "ternary Li2MgH16",
            },
            {
                "value": "Bardeen-Cooper-Schrieffer superconductor",
                "scope": "referenced_work", "page": 1,
                "quote": "the materials were Bardeen-Cooper-Schrieffer superconductors",
            },
        ],
        "key_properties": [],
    }, ensure_ascii=False), encoding="utf-8")

    detail = upload_jobs.public_parsing_detail(task_id)
    fields = {
        field["path"]: field
        for group in detail["form_preview"]["groups"]
        for field in group["fields"]
    }

    assert fields["paper.paper_type"]["state"] == "pending_summary"
    assert [item["value"] for item in fields["paper.paper_type"]["candidates"]] == ["theoretical"]
    assert fields["sc_type"]["state"] == "pending_summary"
    assert [item["value"] for item in fields["sc_type"]["candidates"]] == ["高压三元氢化物超导体"]
    public_evidence = detail["chunks"][0]["result"]["paper_type_evidence"]
    assert {item["scope"] for item in public_evidence if item.get("scope")} == {
        "current_paper", "referenced_work",
    }
    assert any(item["candidate"] == "experimental" for item in public_evidence)
    assert any(item["candidate"] == "review" for item in public_evidence)
