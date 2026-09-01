"""Add ordered multiview reference IDs to generation tasks."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260831_0003"
down_revision: str | None = "20260831_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generation_tasks",
        sa.Column("reference_file_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.execute(
        "UPDATE generation_tasks SET reference_file_ids = "
        "json_array(reference_file_id) WHERE reference_file_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("generation_tasks", "reference_file_ids")
