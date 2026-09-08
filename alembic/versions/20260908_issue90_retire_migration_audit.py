"""Retire Issue #90 migration bookkeeping after completed Contract."""

from alembic import op
import sqlalchemy as sa

revision = "issue90_audit_cleanup_v1"
down_revision = "issue90_contract_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    # Keep the checkpoint until last so interrupted MySQL DDL can be retried.
    if "issue90_migration_checkpoint" in tables:
        row = bind.execute(sa.text(
            "SELECT phase, writes_blocked, reads_target, writes_target, reconciled, observed "
            "FROM issue90_migration_checkpoint WHERE id=1"
        )).mappings().first()
        if not row or row["phase"] != "contract" or row["writes_blocked"] or not all(
            row[key] for key in ("reads_target", "writes_target", "reconciled", "observed")
        ):
            raise RuntimeError("Issue #90 Contract is incomplete; refusing audit cleanup")
    if "issue90_migration_anomalies" in tables:
        unresolved = bind.execute(sa.text(
            "SELECT COUNT(*) FROM issue90_migration_anomalies WHERE resolved=0"
        )).scalar_one()
        if unresolved:
            raise RuntimeError("Issue #90 has unresolved anomalies; refusing audit cleanup")
    for name in (
        "issue90_property_migration_map", "issue90_migration_anomalies",
        "issue90_migration_checkpoint",
    ):
        if name in tables:
            op.drop_table(name)


def downgrade() -> None:
    raise RuntimeError("Restore the archived migration audit backup to recover its original rows")
