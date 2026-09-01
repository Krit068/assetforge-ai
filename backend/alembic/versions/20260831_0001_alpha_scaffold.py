"""Create Alpha project and generation task tables."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260831_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("engine", sa.String(length=32), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("locale", sa.String(length=12), nullable=False),
        sa.Column("spec_profile", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "generation_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("input_mode", sa.String(length=16), nullable=False),
        sa.Column("original_prompt", sa.Text(), nullable=False),
        sa.Column("reference_file_id", sa.String(length=36), nullable=True),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("quality_tier", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("diagnostic_id", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint(
            "project_id",
            "idempotency_key",
            name="uq_task_project_idempotency",
        ),
    )
    op.create_index("ix_generation_tasks_project_id", "generation_tasks", ["project_id"])
    op.create_index("ix_generation_tasks_state", "generation_tasks", ["state"])
    op.create_table(
        "task_candidates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("model_url", sa.String(length=500), nullable=True),
        sa.Column("preview_url", sa.String(length=500), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["generation_tasks.id"]),
        sa.UniqueConstraint("task_id", "position", name="uq_candidate_task_position"),
    )
    op.create_index("ix_task_candidates_task_id", "task_candidates", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_task_candidates_task_id", table_name="task_candidates")
    op.drop_table("task_candidates")
    op.drop_index("ix_generation_tasks_state", table_name="generation_tasks")
    op.drop_index("ix_generation_tasks_project_id", table_name="generation_tasks")
    op.drop_table("generation_tasks")
    op.drop_table("projects")

