"""Issue #90 Contract 占位：旧表退役必须在 Observe 通过后显式执行。"""

from alembic import op

revision = "issue90_contract_legacy_properties"
down_revision = "issue90_copy_property_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 不自动删除旧表。生产执行前需提交迁移对账报告并设置
    # ISSUE90_CONTRACT_CONFIRMED=1，防止误删尚未归档的数据。
    if op.get_context().config.get_main_option("issue90_contract_confirmed") != "1":
        return
    bind = op.get_bind()
    for table in ("tc_result_evidences", "superconductor_property_evidences", "tc_results", "superconductor_properties", "experimental_contexts", "calculation_contexts", "issue90_legacy_superconductors", "issue90_legacy_chemical_systems", "issue90_property_migration_map"):
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS `{table}`")


def downgrade() -> None:
    raise RuntimeError("旧表退役不可自动回滚，请从备份恢复")
