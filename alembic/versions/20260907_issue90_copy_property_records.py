"""Issue #90 Copy: execute the repeatable data copy."""

from alembic import op

revision = "issue90_copy_v1"
down_revision = "issue90_expand_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from backend.scripts.migrate_issue90_properties import copy_legacy_data

    report = copy_legacy_data(op.get_bind())
    if report["errors"]:
        raise RuntimeError(f"Issue #90 Copy failed with {len(report['errors'])} anomalies")


def downgrade() -> None:
    raise RuntimeError("Issue #90 Copy contains data changes; restore the pre-copy checkpoint")
