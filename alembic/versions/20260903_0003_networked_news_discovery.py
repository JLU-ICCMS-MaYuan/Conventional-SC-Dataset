"""为联网超导资讯发现增加溯源和内容语义字段。"""
from alembic import op
import sqlalchemy as sa

revision = "networked_news_discovery"
down_revision = "paper_history_events"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("news_feed_items") as batch:
        batch.add_column(sa.Column("content_type", sa.String(24), nullable=False, server_default=""))
        batch.add_column(sa.Column("display_kind", sa.String(24), nullable=False, server_default=""))
        batch.add_column(sa.Column("discovery_source", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("original_source", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("relevance_evidence", sa.String(500), nullable=False, server_default=""))
    op.execute("UPDATE news_feed_items SET display_kind = kind WHERE display_kind = ''")


def downgrade():
    with op.batch_alter_table("news_feed_items") as batch:
        batch.drop_column("relevance_evidence")
        batch.drop_column("original_source")
        batch.drop_column("discovery_source")
        batch.drop_column("display_kind")
        batch.drop_column("content_type")
