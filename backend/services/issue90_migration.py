"""Issue #90 分阶段迁移控制器。

把停写、对账和切换状态持久化在调用方提供的 checkpoint 中，避免把 MySQL
非事务 DDL 误当成单个可回滚事务。实际 Copy 由 migrate_issue90_properties 执行。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
    errors: list[dict[str, Any]] = field(default_factory=list)


class MigrationBlocked(RuntimeError):
    pass


def advance(checkpoint: MigrationCheckpoint, target: MigrationPhase, *, reconcile_ok: bool = False, observe_ok: bool = False) -> MigrationCheckpoint:
    current_index = ORDER.index(checkpoint.phase)
    target_index = ORDER.index(target)
    if target_index != current_index + 1:
        raise MigrationBlocked(f"迁移阶段必须按顺序推进：{checkpoint.phase} -> {target}")
    if target == MigrationPhase.RECONCILE and not reconcile_ok:
        raise MigrationBlocked("逐项对账未通过，禁止切换读取")
    if target == MigrationPhase.READ_SWITCH:
        checkpoint.writes_blocked = True
        if not checkpoint.reconciled:
            raise MigrationBlocked("必须先完成最终对账")
        checkpoint.reads_target = True
    if target == MigrationPhase.WRITE_SWITCH:
        if not checkpoint.reads_target:
            raise MigrationBlocked("目标读取未验收，禁止切写")
        checkpoint.writes_target = True
    if target == MigrationPhase.OBSERVE:
        if not checkpoint.writes_target or not observe_ok:
            raise MigrationBlocked("切写后的观察验收未通过")
        checkpoint.observed = True
    if target == MigrationPhase.CONTRACT and not checkpoint.observed:
        raise MigrationBlocked("观察期未完成，禁止退役旧表")
    checkpoint.phase = target
    if target == MigrationPhase.RECONCILE:
        checkpoint.reconciled = True
    if target == MigrationPhase.WRITE_SWITCH:
        checkpoint.writes_blocked = False
    return checkpoint
