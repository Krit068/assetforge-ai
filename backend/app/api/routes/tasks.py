import json
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import AppError, error_payload
from app.db.database import SessionLocal, get_db
from app.db.models import CandidateState, ConceptBundle, GenerationTask, Project, ReferenceFile, TaskState
from app.schemas.files import ReferenceFileResponse
from app.schemas.tasks import GenerationTaskCreate, GenerationTaskResponse
from app.services.mock_generation import process_mock_task
from app.services.prompt_clarity import analyze_prompt
from app.services.state_machine import transition
from app.services.tokenhub_generation import process_tokenhub_task
from app.services.tripo_generation import process_tripo_task


router = APIRouter(prefix="/generation-tasks", tags=["generation-tasks"])


def load_task(db: Session, task_id: str) -> GenerationTask:
    task = db.scalar(
        select(GenerationTask)
        .options(selectinload(GenerationTask.candidates))
        .where(GenerationTask.id == task_id)
    )
    if task is None:
        raise AppError("TASK_NOT_FOUND", "生成任务不存在", 404)
    return task


def _task_response(task: GenerationTask, db: Session) -> GenerationTaskResponse:
    settings = get_settings()
    public_base = settings.public_base_url.rstrip("/")

    def serialize(record: ReferenceFile) -> ReferenceFileResponse:
        return ReferenceFileResponse(
            id=record.id, original_name=record.original_name, mime_type=record.mime_type,
            size_bytes=record.size_bytes, width=record.width, height=record.height,
            preview_url=f"{public_base}/assets/{record.storage_path}",
        )

    reference_files = [db.get(ReferenceFile, item) for item in task.reference_file_ids or []]
    accessory_files = []
    for item in task.accessory_references or []:
        record = db.get(ReferenceFile, item.get("file_id"))
        if record:
            accessory_files.append({"name": item.get("name", "配件"), "reference_file": serialize(record).model_dump()})
    response = GenerationTaskResponse.model_validate(task)
    return response.model_copy(update={
        "reference_files": [serialize(item) for item in reference_files if item],
        "accessory_reference_files": accessory_files,
    })


@router.post("", status_code=202)
def create_task(
    payload: GenerationTaskCreate,
    background_tasks: BackgroundTasks,
    idempotency_key: str = Header(min_length=8, max_length=120, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> dict:
    project = db.get(Project, payload.project_id)
    if project is None:
        raise AppError("PROJECT_NOT_FOUND", "项目不存在", 404)

    reference_file_ids = payload.reference_file_ids or (
        [payload.reference_file_id] if payload.reference_file_id else []
    )
    accessory_references = [item.model_dump() for item in payload.accessory_references]

    if payload.concept_bundle_id:
        bundle = db.get(ConceptBundle, payload.concept_bundle_id)
        if bundle is None:
            raise AppError("CONCEPT_NOT_FOUND", "参考图记录不存在", 404)
        if not bundle.ready_for_3d:
            raise AppError(
                "CONCEPT_QUALITY_CHECK_FAILED",
                "参考图未通过多视图质量检查，请重新生成后再提交 3D",
                422,
                details=[{"warning": item} for item in bundle.quality_warnings],
            )
        if reference_file_ids != bundle.view_file_ids:
            raise AppError("CONCEPT_REFERENCE_MISMATCH", "提交的参考图与已确认概念不一致", 422)
        accessory_references = bundle.accessories or []

    if payload.prompt.strip() and not reference_file_ids:
        analysis = analyze_prompt(payload.prompt, project.locale, payload.asset_type)
        if not analysis.ready_to_generate:
            raise AppError(
                "PROMPT_NEEDS_CLARIFICATION",
                "描述信息不足，请先补充生成需求",
                422,
                details=[question.model_dump() for question in analysis.clarifying_questions],
            )

    if any(db.get(ReferenceFile, file_id) is None for file_id in reference_file_ids):
        raise AppError("REFERENCE_FILE_NOT_FOUND", "参考图不存在或已被移除", 404)
    if any(db.get(ReferenceFile, item.get("file_id")) is None for item in accessory_references):
        raise AppError("REFERENCE_FILE_NOT_FOUND", "独立配件参考图不存在或已被移除", 404)

    existing = db.scalar(
        select(GenerationTask)
        .options(selectinload(GenerationTask.candidates))
        .where(
            GenerationTask.project_id == payload.project_id,
            GenerationTask.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return {"data": _task_response(existing, db)}

    settings = get_settings()
    is_tokenhub = settings.model_provider == "tencent_tokenhub"
    is_tripo = settings.model_provider == "tripo_official"
    if settings.model_provider not in {"mock", "tencent_tokenhub", "tripo_official"}:
        raise AppError(
            "MODEL_PROVIDER_CONFIG_INVALID",
            "不支持当前配置的 3D 模型供应商",
            500,
        )
    if settings.model_provider != "mock" and not reference_file_ids:
        raise AppError(
            "CONCEPT_IMAGE_REQUIRED",
            "文字生成 3D 前必须先生成并确认 Seedream 参考图",
            422,
        )
    task = GenerationTask(
        project_id=payload.project_id,
        state=TaskState.DRAFT.value,
        input_mode="image" if reference_file_ids else "text",
        original_prompt=payload.prompt,
        reference_file_id=reference_file_ids[0] if reference_file_ids else None,
        reference_file_ids=reference_file_ids,
        concept_bundle_id=payload.concept_bundle_id,
        accessory_references=accessory_references,
        asset_type=payload.asset_type,
        candidate_count=payload.candidate_count,
        quality_tier=payload.quality_tier,
        idempotency_key=idempotency_key,
        provider=(
            "tencent_tokenhub"
            if is_tokenhub
            else "tripo_official"
            if is_tripo
            else "mock"
        ),
        model_version=(
            "hy-3d-3.1"
            if is_tokenhub and reference_file_ids
            else (settings.model_name or "tripo-3d-p1")
            if is_tokenhub
            else settings.tripo_model_version
            if is_tripo
            else "mock-v1"
        ),
    )
    task.state = transition(task.state, TaskState.VALIDATING)
    task.state = transition(task.state, TaskState.QUEUED)
    db.add(task)
    db.commit()
    db.refresh(task)
    if is_tokenhub:
        background_tasks.add_task(process_tokenhub_task, task.id, SessionLocal)
    elif is_tripo:
        background_tasks.add_task(process_tripo_task, task.id, SessionLocal)
    else:
        background_tasks.add_task(process_mock_task, task.id, SessionLocal)
    return {"data": _task_response(task, db)}


@router.get("/latest")
def get_latest_task(db: Session = Depends(get_db)) -> dict:
    task = db.scalar(
        select(GenerationTask)
        .options(selectinload(GenerationTask.candidates))
        .order_by(GenerationTask.created_at.desc())
        .limit(1)
    )
    if task is None:
        raise AppError("TASK_NOT_FOUND", "还没有生成任务", 404)
    return {"data": _task_response(task, db)}


@router.get("")
def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    tasks = db.scalars(
        select(GenerationTask)
        .options(selectinload(GenerationTask.candidates))
        .order_by(GenerationTask.created_at.desc())
        .limit(limit)
    ).all()
    return {"data": [_task_response(task, db) for task in tasks]}


@router.get("/{task_id}/candidates/{position}/download")
def download_candidate(
    task_id: str,
    position: int,
    db: Session = Depends(get_db),
):
    task = load_task(db, task_id)
    candidate = next((item for item in task.candidates if item.position == position), None)
    if candidate is None:
        raise AppError("CANDIDATE_NOT_FOUND", "候选模型不存在", 404)
    if candidate.state != CandidateState.READY.value or not candidate.model_url:
        raise AppError("CANDIDATE_NOT_READY", "候选模型尚未准备好导出", 409)

    asset_path = unquote(urlparse(candidate.model_url).path)
    prefix = "/assets/"
    if not asset_path.startswith(prefix):
        raise AppError("MODEL_FILE_UNAVAILABLE", "模型文件尚未归档到本地存储", 404)

    storage_root = get_settings().asset_storage_root.resolve()
    model_path = (storage_root / Path(asset_path.removeprefix(prefix))).resolve()
    if not model_path.is_relative_to(storage_root) or model_path.suffix.casefold() != ".glb":
        raise AppError("MODEL_FILE_INVALID", "模型文件路径或格式无效", 422)
    if not model_path.is_file():
        raise AppError("MODEL_FILE_NOT_FOUND", "模型文件不存在或已被移除", 404)

    filename = f"assetforge-{task.id[:8]}-candidate-{position}.glb"
    return FileResponse(
        model_path,
        media_type="model/gltf-binary",
        filename=filename,
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)) -> dict:
    return {"data": _task_response(load_task(db, task_id), db)}


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, db: Session = Depends(get_db)) -> dict:
    task = load_task(db, task_id)
    if task.state in {
        TaskState.READY.value,
        TaskState.NEEDS_FIX.value,
        TaskState.FAILED.value,
        TaskState.CANCELLED.value,
    }:
        raise AppError("INVALID_STATE_TRANSITION", "当前任务已经结束，不能取消", 409)
    task.state = transition(task.state, TaskState.CANCELLED)
    db.commit()
    db.refresh(task)
    return {"data": _task_response(task, db)}


@router.get("/{task_id}/events")
def task_events(task_id: str):
    def stream():
        emitted: set[str] = set()
        for _ in range(100):
            with SessionLocal() as db:
                try:
                    task = load_task(db, task_id)
                except AppError as error:
                    yield f"event: error\ndata: {json.dumps(error_payload(error), ensure_ascii=False)}\n\n"
                    return

                for candidate in task.candidates:
                    if candidate.id not in emitted:
                        emitted.add(candidate.id)
                        payload = {
                            "type": "candidate_ready",
                            "task_id": task.id,
                            "candidate": {
                                "id": candidate.id,
                                "position": candidate.position,
                                "state": candidate.state,
                                "metrics": candidate.metrics,
                            },
                        }
                        yield f"event: chunk\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

                if task.state in {
                    TaskState.READY.value,
                    TaskState.NEEDS_FIX.value,
                    TaskState.CANCELLED.value,
                }:
                    payload = {
                        "task_id": task.id,
                        "state": task.state,
                        "candidate_count": len(task.candidates),
                    }
                    yield f"event: done\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    return
                if task.state == TaskState.FAILED.value:
                    error = AppError(
                        task.error_code or "GENERATION_FAILED",
                        task.error_message or "生成失败",
                        502,
                    )
                    yield f"event: error\ndata: {json.dumps(error_payload(error), ensure_ascii=False)}\n\n"
                    return
            time.sleep(0.1)

        error = AppError("PROVIDER_TIMEOUT", "生成任务等待超时", 504)
        yield f"event: error\ndata: {json.dumps(error_payload(error), ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
