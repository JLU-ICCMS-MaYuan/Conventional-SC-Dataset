"""Issue #90 Contract: retire legacy tables after observed target cutover."""

from __future__ import annotations

import json
import os

from alembic import op
import sqlalchemy as sa

revision = "issue90_contract_v1"
down_revision = "issue90_copy_v1"
branch_labels = None
depends_on = None

LEGACY_TABLES = (
    "tc_result_evidences", "superconductor_property_evidences", "tc_results",
    "superconductor_properties", "experimental_contexts", "calculation_contexts",
    "legacy_issue90_superconductors", "legacy_issue90_chemical_systems",
)


def upgrade() -> None:
    if os.environ.get("ISSUE90_CONTRACT_CONFIRMED") != "1":
        raise RuntimeError("Issue #90 Contract requires ISSUE90_CONTRACT_CONFIRMED=1")
    bind = op.get_bind()
    checkpoint = bind.execute(sa.text(
        "SELECT phase, observed, writes_target FROM issue90_migration_checkpoint WHERE id=1"
    )).mappings().first()
    if not checkpoint or checkpoint["phase"] != "observe" or not checkpoint["observed"] or not checkpoint["writes_target"]:
        raise RuntimeError("Issue #90 Observe checkpoint is incomplete; refusing Contract")
    unresolved = bind.execute(sa.text(
        "SELECT COUNT(*) FROM issue90_migration_anomalies WHERE resolved=0"
    )).scalar_one()
    if unresolved:
        raise RuntimeError(f"Issue #90 has {unresolved} unresolved migration anomalies")
    existing = set(sa.inspect(bind).get_table_names())
    dropped = []
    for table in LEGACY_TABLES:
        if table in existing:
            op.drop_table(table)
            dropped.append(table)
    bind.execute(sa.text(
        "UPDATE issue90_migration_checkpoint SET phase='contract', checkpoint_json=:snapshot WHERE id=1"
    ), {"snapshot": json.dumps({"legacy_tables_dropped": dropped}, sort_keys=True)})


def downgrade() -> None:
    raise RuntimeError("Issue #90 Contract is irreversible; restore the target-schema backup")
