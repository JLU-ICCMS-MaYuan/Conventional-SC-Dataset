"""Issue #73: upload-worker LLM credentials are isolated and short lived."""

import pytest

from backend.ingest import upload_jobs, upload_tasks
from backend.rag import llm_context


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}
        self.deleted = []

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.ttls[key] = ttl

    def get(self, key):
        return self.values.get(key)

    def delete(self, *keys):
        self.deleted.extend(keys)
        for key in keys:
            self.values.pop(key, None)
        return len(keys)


@pytest.mark.parametrize("outcome", ["succeeded", "failed", "cancelled"])
def test_upload_llm_config_has_ttl_and_worker_cleans_it(monkeypatch, outcome):
    task_id = "a" * 32
    config = llm_context.LlmConfig(
        "kimi", "https://api.moonshot.cn/v1", "moonshot-v1-8k", "user-key", True,
    )
    redis = FakeRedis()
    monkeypatch.setattr(upload_tasks, "redis_client", lambda: redis)
    monkeypatch.setattr(upload_tasks.settings, "upload_task_ttl_seconds", 3600)

    upload_tasks.save_llm_config(task_id, config)
    key = upload_tasks.llm_config_key(task_id)
    assert redis.ttls[key] == 3600
    assert upload_tasks.load_llm_config(task_id) == config

    observed = []
    monkeypatch.setattr(upload_jobs, "load_llm_config", upload_tasks.load_llm_config)
    monkeypatch.setattr(upload_jobs, "delete_llm_config", upload_tasks.delete_llm_config)
    def process(_task_id):
        observed.append(llm_context.get_llm_config())
        if outcome != "succeeded":
            raise RuntimeError(outcome)
        return {"status": outcome}

    monkeypatch.setattr(upload_jobs, "_process_upload_task", process)

    if outcome == "succeeded":
        assert upload_jobs.process_upload_task(task_id) == {"status": outcome}
    else:
        with pytest.raises(RuntimeError, match=outcome):
            upload_jobs.process_upload_task(task_id)
    assert observed == [config]
    assert key in redis.deleted
    assert key not in redis.values


def test_transient_cleanup_deletes_upload_llm_config(monkeypatch):
    task_id = "b" * 32
    redis = FakeRedis()
    monkeypatch.setattr(upload_tasks, "redis_client", lambda: redis)
    monkeypatch.setattr(upload_tasks, "_delete_processing_job", lambda _job_id: None)

    upload_tasks.cleanup_transient_data(task_id)

    assert upload_tasks.llm_config_key(task_id) in redis.deleted
