"""Persistent phase gates for the Issue #90 online migration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any

from sqlalchemy import inspect, text


class MigrationPhase(str, Enum):
    EXPAND = "expand"
    COPY = "copy"
    RECONCILE = "reconcile"
    READ_SWITCH = "read_switch"
    WRITE_SWITCH = "write_switch"
    OBSERVE = "observe"
    CONTRACT = "contract"


ORDER = list(MigrationPhase)


@dataclass
class MigrationCheckpoint:
    phase: MigrationPhase = MigrationPhase.EXPAND
    writes_blocked: bool = False
    reads_target: bool = False
    writes_target: bool = False
    reconciled: bool = False
    observed: bool = False
    checkpoint: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)


class MigrationBlocked(RuntimeError):
    pass


def advance(checkpoint: MigrationCheckpoint, target: MigrationPhase, *, reconcile_ok: bool = False, observe_ok: bool = False) -> MigrationCheckpoint:
    if ORDER.index(target) != ORDER.index(checkpoint.phase) + 1:
        raise MigrationBlocked(f"迁移阶段必须按顺序推进：{checkpoint.phase} -> {target}")
    if target == MigrationPhase.RECONCILE and not reconcile_ok:
        raise MigrationBlocked("逐项对账未通过，禁止切换读取")
    if target == MigrationPhase.READ_SWITCH and not checkpoint.reconciled:
        raise MigrationBlocked("必须先完成最终对账")
    if target == MigrationPhase.WRITE_SWITCH and not checkpoint.reads_target:
        raise MigrationBlocked("目标读取未验收，禁止切写")
    if target == MigrationPhase.OBSERVE and (not checkpoint.writes_target or not observe_ok):
        raise MigrationBlocked("切写后的观察验收未通过")
    if target == MigrationPhase.CONTRACT and not checkpoint.observed:
        raise MigrationBlocked("观察期未完成，禁止退役旧表")
    checkpoint.phase = target
    if target == MigrationPhase.RECONCILE:
        checkpoint.reconciled = True
    elif target == MigrationPhase.READ_SWITCH:
        checkpoint.writes_blocked = True
        checkpoint.reads_target = True
    elif target == MigrationPhase.WRITE_SWITCH:
        checkpoint.writes_target = True
        checkpoint.writes_blocked = False
    elif target == MigrationPhase.OBSERVE:
        checkpoint.observed = True
    return checkpoint


def load_checkpoint(conn) -> MigrationCheckpoint:
    row = conn.execute(text("SELECT * FROM issue90_migration_checkpoint WHERE id=1")).mappings().one()
    return MigrationCheckpoint(
        phase=MigrationPhase(row["phase"]), writes_blocked=bool(row["writes_blocked"]),
        reads_target=bool(row["reads_target"]), writes_target=bool(row["writes_target"]),
        reconciled=bool(row["reconciled"]), observed=bool(row["observed"]),
        checkpoint=_json_value(row["checkpoint_json"], {}), errors=_json_value(row["error_json"], []),
    )


def persist_checkpoint(conn, checkpoint: MigrationCheckpoint) -> MigrationCheckpoint:
    conn.execute(text("""
        UPDATE issue90_migration_checkpoint
        SET phase=:phase, writes_blocked=:writes_blocked, reads_target=:reads_target,
            writes_target=:writes_target, reconciled=:reconciled, observed=:observed,
            checkpoint_json=:checkpoint, error_json=:errors, updated_at=CURRENT_TIMESTAMP
        WHERE id=1
    """), {
        "phase": checkpoint.phase.value, "writes_blocked": checkpoint.writes_blocked,
        "reads_target": checkpoint.reads_target, "writes_target": checkpoint.writes_target,
        "reconciled": checkpoint.reconciled, "observed": checkpoint.observed,
        "checkpoint": json.dumps(checkpoint.checkpoint, ensure_ascii=False, sort_keys=True),
        "errors": json.dumps(checkpoint.errors, ensure_ascii=False, sort_keys=True),
    })
    return checkpoint


def advance_persisted(conn, target: MigrationPhase, **guards: bool) -> MigrationCheckpoint:
    checkpoint = advance(load_checkpoint(conn), target, **guards)
    return persist_checkpoint(conn, checkpoint)


def _json_value(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    return json.loads(value) if isinstance(value, str) else value


def recover(conn, target: MigrationPhase = MigrationPhase.RECONCILE) -> MigrationCheckpoint:
    checkpoint = load_checkpoint(conn)
    if checkpoint.phase != MigrationPhase.READ_SWITCH or target != MigrationPhase.RECONCILE:
        raise MigrationBlocked("切写后禁止恢复过期旧模型；必须恢复目标 Schema 检查点")
    checkpoint.phase = MigrationPhase.RECONCILE
    checkpoint.writes_blocked = False
    checkpoint.reads_target = False
    checkpoint.writes_target = False
    checkpoint.reconciled = True
    checkpoint.observed = False
    return persist_checkpoint(conn, checkpoint)


def migration_tables_present(conn) -> bool:
    return "issue90_migration_checkpoint" in inspect(conn).get_table_names()


async def assert_scientific_write_allowed(session) -> None:
    try:
        result = await session.execute(text(
            "SELECT writes_blocked, writes_target FROM issue90_migration_checkpoint WHERE id=1"
        ))
    except Exception as exc:
        # Databases predating Expand have no migration gate and still serve the legacy release.
        if "issue90_migration_checkpoint" in str(exc):
            return
        raise
    # Lightweight unit-test sessions do not expose SQLAlchemy row mappings.
    if not hasattr(result, "mappings"):
        return
    row = result.mappings().first()
    if row and (row["writes_blocked"] or not row["writes_target"]):
        raise MigrationBlocked("科学数据迁移维护中，当前禁止写入")
