import time

import pytest

from backend.ingest import upload_contracts as upload_tasks


def test_public_task_state_does_not_leak_internal_fields():
    state = {
        "task_id": "a" * 32,
        "user_id": 7,
        "status": "ready",
        "stage": "ready",
        "cleanup_at": 123,
        "file_path": "/data/private/paper.pdf",
        "job_id": "rq-secret",
        "redis_key": "upload:secret",
        "files": [{"file_id": "f1", "role": "main", "stored_path": "/data/private"}],
    }

    public = upload_tasks.public_task_state(state)

    assert public["task_id"] == state["task_id"]
    assert public["cleanup_at"] == 123
    assert "file_path" not in public
    assert "job_id" not in public
    assert "user_id" not in public
    assert "stored_path" not in public["files"][0]


@pytest.mark.parametrize("status", ["failed", "duplicate", "cancelled"])
def test_terminal_cleanup_is_fixed_from_state_entry(status):
    state = {"status": "reading", "updated_at": 1}

    updated = upload_tasks.apply_state_changes(state, now=100, status=status)
    viewed = upload_tasks.apply_user_activity(updated, now=200)

    assert updated["terminal_at"] == 100
    assert updated["cleanup_at"] == 100 + upload_tasks.TASK_TTL
    assert viewed["cleanup_at"] == updated["cleanup_at"]


def test_ready_cleanup_slides_only_for_explicit_user_activity():
    ready = upload_tasks.apply_state_changes(
        {"status": "summarizing", "updated_at": 1}, now=100, status="ready"
    )

    polled = upload_tasks.apply_state_changes(ready, now=200, progress={"done": 2})
    touched = upload_tasks.apply_user_activity(polled, now=300)

    assert polled["cleanup_at"] == 100 + upload_tasks.TASK_TTL
    assert touched["cleanup_at"] == 300 + upload_tasks.TASK_TTL


def test_running_states_have_no_cleanup_countdown():
    state = upload_tasks.apply_state_changes(
        {"status": "uploading"}, now=100, status="queued"
    )

    assert state["cleanup_at"] is None


def test_manifest_requires_exactly_one_main_and_supported_types():
    valid = [
        {"client_id": "1", "role": "main", "filename": "paper.pdf", "size": 12},
        {"client_id": "2", "role": "supplementary", "filename": "supp.md", "size": 8},
    ]

    normalized = upload_tasks.validate_manifest(valid)
    assert [item["role"] for item in normalized] == ["main", "supplementary"]

    with pytest.raises(ValueError, match="恰好一个正文"):
        upload_tasks.validate_manifest([valid[1]])
    with pytest.raises(ValueError, match="不支持"):
        upload_tasks.validate_manifest([{**valid[0], "filename": "paper.docx"}])


def test_cancelled_task_rejects_late_worker_transition():
    cancelled = {"status": "cancelled", "revision": 3}

    with pytest.raises(ValueError, match="终态"):
        upload_tasks.apply_state_changes(cancelled, now=int(time.time()), status="reading")


def test_consistency_missing_metadata_is_unknown_but_conflict_warns():
    unknown = upload_tasks.compare_file_identities([
        {"file_id": "m", "role": "main", "title": "Paper", "doi": "10.1000/main"},
        {"file_id": "a", "role": "attachment", "title": None, "doi": None},
    ])
    warning = upload_tasks.compare_file_identities([
        {"file_id": "m", "role": "main", "title": "Paper", "doi": "10.1000/main"},
        {"file_id": "a", "role": "attachment", "title": "Other", "doi": "10.1000/other"},
    ])

    assert unknown["status"] == "unknown"
    assert warning["status"] == "warning"
    assert {item["field"] for item in warning["conflicts"]} == {"title", "doi"}
