from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskState(StrEnum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    PREPROCESSING = "PREPROCESSING"
    GEOMETRY = "GEOMETRY"
    TEXTURING = "TEXTURING"
    POST_PROCESSING = "POST_PROCESSING"
    QA = "QA"
    READY = "READY"
    NEEDS_FIX = "NEEDS_FIX"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CandidateState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    engine: Mapped[str] = mapped_column(String(32), default="unity")
    platform: Mapped[str] = mapped_column(String(32), default="mobile")
    locale: Mapped[str] = mapped_column(String(12), default="zh-CN")
    spec_profile: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tasks: Mapped[list[GenerationTask]] = relationship(back_populates="project")


class ReferenceFile(Base):
    __tablename__ = "reference_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    original_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(80))
    storage_path: Mapped[str] = mapped_column(String(500), unique=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConceptBundle(Base):
    __tablename__ = "concept_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    prompt: Mapped[str] = mapped_column(Text)
    asset_type: Mapped[str] = mapped_column(String(32), default="prop")
    locale: Mapped[str] = mapped_column(String(12), default="zh-CN")
    model: Mapped[str] = mapped_column(String(120))
    view_file_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    accessories: Mapped[list[dict]] = mapped_column(JSON, default=list)
    usage_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_fen: Mapped[int] = mapped_column(Integer, default=0)
    quality_warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    ready_for_3d: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class GenerationTask(Base):
    __tablename__ = "generation_tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "idempotency_key", name="uq_task_project_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    state: Mapped[str] = mapped_column(String(32), default=TaskState.DRAFT.value, index=True)
    input_mode: Mapped[str] = mapped_column(String(16), default="text")
    original_prompt: Mapped[str] = mapped_column(Text, default="")
    reference_file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reference_file_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    concept_bundle_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    accessory_references: Mapped[list[dict]] = mapped_column(JSON, default=list)
    asset_type: Mapped[str] = mapped_column(String(32), default="prop")
    candidate_count: Mapped[int] = mapped_column(Integer, default=4)
    quality_tier: Mapped[str] = mapped_column(String(16), default="high")
    idempotency_key: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(64), default="mock")
    model_version: Mapped[str] = mapped_column(String(120), default="mock-v1")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    diagnostic_id: Mapped[str] = mapped_column(String(32), default=lambda: f"diag_{uuid4().hex[:12]}")
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="tasks")
    candidates: Mapped[list[TaskCandidate]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskCandidate.position",
    )


class TaskCandidate(Base):
    __tablename__ = "task_candidates"
    __table_args__ = (UniqueConstraint("task_id", "position", name="uq_candidate_task_position"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(ForeignKey("generation_tasks.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    asset_role: Mapped[str] = mapped_column(String(32), default="main")
    asset_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str] = mapped_column(String(16), default=CandidateState.PENDING.value)
    model_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preview_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped[GenerationTask] = relationship(back_populates="candidates")
