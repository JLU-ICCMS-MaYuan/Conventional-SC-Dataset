"""独立自动资讯表，不修改正式科研数据。"""
from alembic import op
import sqlalchemy as sa

revision = "20260831_0063"
down_revision = "20260826_0016"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "news_feed_items",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("summary_source", sa.String(16), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("doi", sa.String(500), nullable=False),
        sa.Column("arxiv_id", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("authors", sa.Text(), nullable=False),
        sa.Column("journal", sa.Text(), nullable=False),
        sa.Column("links", sa.Text(), nullable=False),
        sa.Column("published_at", sa.String(20), nullable=False),
        sa.Column("date_precision", sa.String(10), nullable=False),
        sa.Column("source_updated_at", sa.String(20), nullable=False),
        sa.Column("first_seen_at", sa.String(20), nullable=False),
        sa.Column("last_seen_at", sa.String(20), nullable=False),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_news_feed_published", "news_feed_items", ["published_at"])
    op.create_index("ix_news_feed_kind_published", "news_feed_items", ["kind", "published_at"])
    op.create_table(
        "news_feed_identities",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("item_id", sa.String(32), sa.ForeignKey("news_feed_items.id"), nullable=False),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_news_feed_identities_item_id", "news_feed_identities", ["item_id"])
    op.create_table(
        "news_feed_sources",
        sa.Column("source", sa.String(16), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("last_started_at", sa.String(20), nullable=False),
        sa.Column("last_finished_at", sa.String(20), nullable=False),
        sa.Column("last_success_at", sa.String(20), nullable=False),
        sa.Column("error_code", sa.String(40), nullable=False),
        sa.Column("fetched", sa.Integer(), nullable=False),
        sa.Column("accepted", sa.Integer(), nullable=False),
        mysql_charset="utf8mb4",
    )


def downgrade():
    op.drop_table("news_feed_identities")
    op.drop_table("news_feed_sources")
    op.drop_table("news_feed_items")
