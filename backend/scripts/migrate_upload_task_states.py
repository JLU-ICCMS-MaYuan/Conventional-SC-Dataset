"""一次性迁移旧版 duplicate Redis 状态。"""

from __future__ import annotations

import argparse
import json
import time
from types import SimpleNamespace
from typing import Any, Callable

from redis.exceptions import WatchError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.ingest.upload_contracts import TASK_TTL, UPLOAD_STATE_SCHEMA_VERSION


MigrationSummary = dict[str, int]
PaperLookup = Callable[[int], Any | None]


def _is_legacy_duplicate(state: dict[str, Any]) -> bool:
    return bool(state.get("duplicate")) and int(state.get("state_schema_version") or 0) != (
        UPLOAD_STATE_SCHEMA_VERSION
    )


def _migrated_duplicate_state(state: dict[str, Any], paper: Any) -> dict[str, Any] | None:
    if state.get("updated_at") is None:
        return None
    terminal_at = int(state["updated_at"])
    user_id = int(state.get("user_id") or 0)
    owner_id = int(getattr(paper, "uploaded_by_user_id", None) or 0)
    review_status = str(getattr(paper, "review_status", "") or "")
    can_view = review_status in {"approved", "pending"} or (
        review_status == "rejected" and owner_id == user_id
    )
    allowed_actions = ["view"] if can_view else []
    if can_view and owner_id == user_id:
        allowed_actions.append("edit")
    return {
        **state,
        "status": "duplicate",
        "existing_paper_status": review_status,
        "allowed_actions": allowed_actions,
        "duplicate_reason": (
            "数据库中已有该论文"
            if can_view
            else "数据库中已有该论文，但当前账号无权查看"
        ),
        "terminal_at": terminal_at,
        "cleanup_at": terminal_at + TASK_TTL,
        "state_schema_version": UPLOAD_STATE_SCHEMA_VERSION,
    }


def _compare_and_set(client, key: str, original: str, state: dict[str, Any], *, now: int) -> bool:
    encoded = json.dumps(state, ensure_ascii=False)
    ttl = max(1, int(state["cleanup_at"]) - now)
    while True:
        with client.pipeline(transaction=True) as pipeline:
            try:
                pipeline.watch(key)
                if pipeline.get(key) != original:
                    pipeline.unwatch()
                    return False
                pipeline.multi()
                pipeline.setex(key, ttl, encoded)
                pipeline.execute()
                return True
            except WatchError:
                continue


def migrate_upload_task_states(
    client,
    paper_lookup: PaperLookup,
    *,
    apply: bool,
    now: int | None = None,
    schedule_cleanup: Callable[[str], None] | None = None,
) -> MigrationSummary:
    current_time = int(time.time()) if now is None else int(now)
    summary = {"legacy": 0, "migrated": 0, "unresolved": 0, "changed": 0}
    for key in client.scan_iter(match="upload:*:state"):
        raw = client.get(key)
        if not raw:
            continue
        try:
            state = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        if not _is_legacy_duplicate(state):
            continue
        summary["legacy"] += 1
        if not apply:
            continue
        try:
            paper_id = int(state.get("existing_paper_id") or 0)
        except (TypeError, ValueError):
            paper_id = 0
        try:
            paper = paper_lookup(paper_id) if paper_id > 0 else None
        except SQLAlchemyError:
            summary["unresolved"] += 1
            continue
        migrated = _migrated_duplicate_state(state, paper) if paper is not None else None
        if migrated is None or not _compare_and_set(
            client, key, raw, migrated, now=current_time,
        ):
            summary["unresolved"] += 1
            continue
        summary["migrated"] += 1
        summary["changed"] += 1
        if schedule_cleanup is not None:
            schedule_cleanup(str(migrated["task_id"]))
    return summary


def _database_lookup() -> tuple[PaperLookup, Callable[[], None]]:
    from backend.database import SessionLocal

    session = SessionLocal()

    def lookup(paper_id: int):
        row = session.execute(
            text(
                "SELECT id, review_status, uploaded_by_user_id "
                "FROM papers WHERE id = :paper_id"
            ),
            {"paper_id": paper_id},
        ).mappings().first()
        if row is None:
            return None
        return SimpleNamespace(
            id=row["id"],
            review_status=row["review_status"],
            uploaded_by_user_id=row["uploaded_by_user_id"],
        )

    return lookup, session.close


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="实际写入；默认只执行 dry-run")
    args = parser.parse_args()

    from backend.ingest.upload_tasks import redis_client, schedule_cleanup

    lookup, close = _database_lookup()
    try:
        summary = migrate_upload_task_states(
            redis_client(),
            lookup,
            apply=args.apply,
            schedule_cleanup=schedule_cleanup if args.apply else None,
        )
    finally:
        close()
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", **summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
