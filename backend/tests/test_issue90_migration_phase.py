import pytest

from backend.services.issue90_migration import MigrationBlocked, MigrationCheckpoint, MigrationPhase, advance


def test_issue90_migration_requires_reconcile_before_read_switch():
    checkpoint = MigrationCheckpoint()
    advance(checkpoint, MigrationPhase.COPY)
    with pytest.raises(MigrationBlocked):
        advance(checkpoint, MigrationPhase.RECONCILE)
    advance(checkpoint, MigrationPhase.RECONCILE, reconcile_ok=True)
    advance(checkpoint, MigrationPhase.READ_SWITCH)
    assert checkpoint.writes_blocked and checkpoint.reads_target


def test_issue90_migration_contract_is_guarded_by_observe():
    checkpoint = MigrationCheckpoint(phase=MigrationPhase.WRITE_SWITCH, reads_target=True, writes_target=True, reconciled=True)
    with pytest.raises(MigrationBlocked):
        advance(checkpoint, MigrationPhase.OBSERVE)
    advance(checkpoint, MigrationPhase.OBSERVE, observe_ok=True)
    advance(checkpoint, MigrationPhase.CONTRACT)
    assert checkpoint.phase == MigrationPhase.CONTRACT

