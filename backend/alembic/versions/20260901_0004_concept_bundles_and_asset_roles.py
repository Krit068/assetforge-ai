"""persist concept bundles and generated asset roles

Revision ID: 20260901_0004
Revises: 20260831_0003
"""

from alembic import op
import sqlalchemy as sa


revision = "20260901_0004"
down_revision = "20260831_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "concept_bundles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("locale", sa.String(12), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("view_file_ids", sa.JSON(), nullable=False),
        sa.Column("accessories", sa.JSON(), nullable=False),
        sa.Column("usage_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_fen", sa.Integer(), nullable=False),
        sa.Column("quality_warnings", sa.JSON(), nullable=False),
        sa.Column("ready_for_3d", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_concept_bundles_created_at", "concept_bundles", ["created_at"])
    with op.batch_alter_table("generation_tasks") as batch:
        batch.add_column(sa.Column("concept_bundle_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("accessory_references", sa.JSON(), nullable=False, server_default="[]"))
        batch.create_index("ix_generation_tasks_concept_bundle_id", ["concept_bundle_id"])
    with op.batch_alter_table("task_candidates") as batch:
        batch.add_column(sa.Column("asset_role", sa.String(32), nullable=False, server_default="main"))
        batch.add_column(sa.Column("asset_name", sa.String(120), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("task_candidates") as batch:
        batch.drop_column("asset_name")
        batch.drop_column("asset_role")
    with op.batch_alter_table("generation_tasks") as batch:
        batch.drop_index("ix_generation_tasks_concept_bundle_id")
        batch.drop_column("accessory_references")
        batch.drop_column("concept_bundle_id")
    op.drop_index("ix_concept_bundles_created_at", table_name="concept_bundles")
    op.drop_table("concept_bundles")
