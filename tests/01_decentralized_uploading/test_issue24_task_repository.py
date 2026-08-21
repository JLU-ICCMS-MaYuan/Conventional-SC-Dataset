import pytest

from backend.ingest import upload_tasks


class MemoryRedis:
    def __init__(self):
        self.values = {}
        self.zsets = {}

    def pipeline(self, transaction=True):
        return self
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def watch(self, *_keys):
        return None
    def multi(self):
        return None
    def execute(self):
        return []
    def get(self, key):
        return self.values.get(key)
    def mget(self, keys):
        return [self.get(key) for key in keys]
    def set(self, key, value):
        self.values[key] = value
    def setex(self, key, _ttl, value):
        self.set(key, value)
    def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)
    def zadd(self, key, mapping):
        self.zsets.setdefault(key, {}).update(mapping)
    def zrange(self, key, start, end):
        members = sorted(self.zsets.get(key, {}), key=self.zsets.get(key, {}).get)
        return members[start:] if end == -1 else members[start:end + 1]
    def zrevrange(self, key, start, end):
        return list(reversed(self.zrange(key, 0, -1)))[start:] if end == -1 else list(reversed(self.zrange(key, 0, -1)))[start:end + 1]
    def zrem(self, key, *members):
        for member in members:
            self.zsets.setdefault(key, {}).pop(member, None)


def test_repository_enforces_limit_and_submitted_task_releases_slot(monkeypatch):
    redis = MemoryRedis()
    monkeypatch.setattr(upload_tasks, "redis_client", lambda: redis)
    monkeypatch.setattr(upload_tasks, "ACTIVE_TASK_LIMIT", 2)

    first = upload_tasks.create_task(7, "one.pdf", "pdf")
    upload_tasks.create_task(7, "two.pdf", "pdf")
    with pytest.raises(ValueError, match="100 个上限"):
        upload_tasks.create_task(7, "three.pdf", "pdf")

    upload_tasks.update_state(first["task_id"], status="submitted", paper_id=42)
    third = upload_tasks.create_task(7, "three.pdf", "pdf")

    assert third["task_id"] in {item["task_id"] for item in upload_tasks.list_user_tasks(7)}
    assert first["task_id"] not in {item["task_id"] for item in upload_tasks.list_user_tasks(7)}


def test_repository_list_returns_public_dto(monkeypatch):
    redis = MemoryRedis()
    monkeypatch.setattr(upload_tasks, "redis_client", lambda: redis)
    task = upload_tasks.create_task(8, "paper.pdf", "pdf")
    upload_tasks.update_state(task["task_id"], file_path="/data/private.pdf", job_id="secret")

    listed = upload_tasks.list_user_tasks(8)

    assert len(listed) == 1
    assert "file_path" not in listed[0]
    assert "job_id" not in listed[0]


def test_manifest_locks_once_and_rejects_duplicate_content(monkeypatch):
    redis = MemoryRedis()
    monkeypatch.setattr(upload_tasks, "redis_client", lambda: redis)
    task = upload_tasks.create_task(9, files=[
        {"client_id": "m", "role": "main", "filename": "paper.pdf", "size": 3},
        {"client_id": "a", "role": "attachment", "filename": "notes.md", "size": 3},
    ])
    main, attachment = task["files"]
    upload_tasks.update_task_file(
        task["task_id"], main["file_id"], upload_status="completed", sha256="a" * 64,
    )
    with pytest.raises(ValueError, match="完全相同"):
        upload_tasks.update_task_file(
            task["task_id"], attachment["file_id"], upload_status="completed", sha256="a" * 64,
        )
    upload_tasks.update_task_file(
        task["task_id"], attachment["file_id"], upload_status="completed", sha256="b" * 64,
    )

    first_state, first_won = upload_tasks.lock_uploaded_manifest(task["task_id"])
    second_state, second_won = upload_tasks.lock_uploaded_manifest(task["task_id"])

    assert first_state["status"] == second_state["status"] == "queued"
    assert first_won is True
    assert second_won is False
