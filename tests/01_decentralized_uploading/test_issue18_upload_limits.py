from pathlib import Path
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile


ROOT = Path(__file__).resolve().parents[2]


def test_current_upload_panel_displays_limit_and_handles_plain_text_413():
    source = (ROOT / "frontend/src/components/MultiFileUploadPanel.tsx").read_text(encoding="utf-8")

    assert "最大 50 MB" in source
    assert "MAX_BYTES" in source
    assert "xhr.status === 413" in source


def test_nginx_keeps_fifty_megabyte_server_limit_and_allows_multipart_overhead():
    config = (ROOT / "docker/nginx.conf").read_text(encoding="utf-8")

    assert "client_max_body_size 50M;" in config
    assert "client_max_body_size 51M;" in config


@pytest.mark.parametrize(
    ("size", "accepted"),
    [(50 * 1024 * 1024, True), (50 * 1024 * 1024 + 1, False)],
)
def test_python_enforces_exact_fifty_megabyte_file_limit(tmp_path, monkeypatch, size, accepted):
    import asyncio
    import shutil

    from backend.api import rag
    from backend.ingest import upload_jobs, upload_tasks

    task_id = "f" * 32
    state = {
        "task_id": task_id,
        "user_id": 7,
        "filename": "paper.pdf",
        "stage": "saving_file",
        "stage_index": 1,
        "stage_total": 5,
        "processing_status": "processing",
    }
    monkeypatch.setattr(upload_tasks, "create_task", lambda *_args: dict(state))
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: dict(state))
    monkeypatch.setattr(upload_tasks, "task_directory", lambda _task_id: tmp_path / task_id)
    monkeypatch.setattr(upload_tasks, "enqueue_processing", lambda _task_id: "job")
    monkeypatch.setattr(upload_tasks, "schedule_cleanup", lambda _task_id: None)
    monkeypatch.setattr(upload_jobs, "sha256_file", lambda _path: "hash")

    def update_state(_task_id, **changes):
        state.update(changes)
        return dict(state)

    def cleanup(_task_id):
        shutil.rmtree(tmp_path / task_id, ignore_errors=True)

    monkeypatch.setattr(upload_tasks, "update_state", update_state)
    monkeypatch.setattr(upload_tasks, "cleanup_task_files", cleanup)
    (tmp_path / task_id).mkdir()
    upload = UploadFile(filename="paper.pdf", file=BytesIO(b"x" * size))

    if accepted:
        result = asyncio.run(rag._save_task_upload(upload, SimpleNamespace(id=7), "pdf"))
        assert result["file_size"] == size
        assert (tmp_path / task_id / "paper.pdf").stat().st_size == size
    else:
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(rag._save_task_upload(upload, SimpleNamespace(id=7), "pdf"))
        assert exc_info.value.status_code == 413
        assert exc_info.value.detail["code"] == "file_too_large"
        assert not (tmp_path / task_id).exists()
