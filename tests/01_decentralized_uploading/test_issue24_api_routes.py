from backend.main import app
from backend.rag.config import RagSettings


def test_canonical_upload_task_routes_are_registered():
    schema = app.openapi()
    routes = {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        for method in operations
    }

    expected = {
        ("POST", "/api/upload-tasks"),
        ("GET", "/api/upload-tasks"),
        ("GET", "/api/upload-tasks/{task_id}"),
        ("PUT", "/api/upload-tasks/{task_id}/files/{file_id}"),
        ("POST", "/api/upload-tasks/{task_id}/cancel"),
        ("DELETE", "/api/upload-tasks/{task_id}"),
        ("GET", "/api/upload-tasks/{task_id}/parsing"),
        ("GET", "/api/upload-tasks/{task_id}/chunks"),
    }

    missing = expected - routes
    assert not missing, "missing=" + repr(missing) + "\nroutes=\n" + "\n".join(
        f"{method} {path}" for method, path in sorted(routes)
    )


def test_worker_concurrency_defaults_to_two_and_keeps_scheduler():
    from backend.scripts import run_upload_workers

    assert RagSettings(_env_file=None).upload_llm_concurrency == 2
    assert run_upload_workers.QUEUE_NAME == "scwiki-upload"
