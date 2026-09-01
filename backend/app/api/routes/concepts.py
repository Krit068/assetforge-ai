from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.database import get_db
from app.db.models import ConceptBundle, ReferenceFile
from app.schemas.concepts import (
    ConceptAccessory,
    ConceptImageCreate,
    ConceptImageResponse,
    ConceptReferenceView,
)
from app.schemas.files import ReferenceFileResponse
from app.services.concept_image import TokenHubConceptImageProvider
from app.services.concept_quality import assess_character_views
from app.services.prompt_clarity import detect_accessories


router = APIRouter(prefix="/concept-images", tags=["concept-images"])


def _file_response(record: ReferenceFile, settings) -> ReferenceFileResponse:
    return ReferenceFileResponse(
        id=record.id,
        original_name=record.original_name,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        width=record.width,
        height=record.height,
        preview_url=f"{settings.public_base_url.rstrip('/')}/assets/{record.storage_path}",
    )


def _bundle_response(bundle: ConceptBundle, db: Session, settings) -> ConceptImageResponse:
    files = {item.id: item for item in db.scalars(select(ReferenceFile).where(ReferenceFile.id.in_(bundle.view_file_ids))).all()}
    views = []
    for view, file_id in zip(("front", "left", "back", "right"), bundle.view_file_ids, strict=False):
        if file_id in files:
            views.append(ConceptReferenceView(view=view, reference_file=_file_response(files[file_id], settings)))
    accessories = []
    for item in bundle.accessories or []:
        record = db.get(ReferenceFile, item.get("file_id"))
        if record:
            accessories.append(ConceptAccessory(name=item.get("name", "配件"), reference_file=_file_response(record, settings)))
    if not views:
        raise AppError("CONCEPT_FILES_MISSING", "概念图文件已丢失", 404)
    return ConceptImageResponse(
        id=bundle.id,
        reference_file=views[0].reference_file,
        views=views,
        accessories=accessories,
        model=bundle.model,
        usage_tokens=bundle.usage_tokens,
        estimated_cost_cny=bundle.estimated_cost_fen / 100,
        ready_for_3d=bundle.ready_for_3d,
        quality_warnings=bundle.quality_warnings or [],
    )


def _persist_concept(concept, original_name: str, settings, db: Session) -> ReferenceFileResponse:
    file_id = str(uuid4())
    relative_path = Path("concepts") / f"{file_id}{concept.suffix}"
    destination = settings.asset_storage_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(concept.contents)
    temporary.replace(destination)

    record = ReferenceFile(
        id=file_id,
        original_name=original_name,
        mime_type=concept.mime_type,
        storage_path=relative_path.as_posix(),
        size_bytes=len(concept.contents),
        width=concept.width,
        height=concept.height,
    )
    db.add(record)
    db.flush()
    public_base = settings.public_base_url.rstrip("/")
    return ReferenceFileResponse(
        id=record.id,
        original_name=record.original_name,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        width=record.width,
        height=record.height,
        preview_url=f"{public_base}/assets/{record.storage_path}",
    )


@router.post("", status_code=201)
def create_concept_image(payload: ConceptImageCreate, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    if not settings.model_api_base_url.strip() or not settings.model_api_key.strip():
        raise AppError("CONCEPT_PROVIDER_NOT_CONFIGURED", "当前未配置真实概念图模型", 503)

    provider = TokenHubConceptImageProvider(settings)
    generated: list = []
    try:
        accessories = (
            detect_accessories(payload.prompt, payload.locale)
            if payload.asset_type == "character"
            else []
        )
        excluded = tuple(accessories)
        front = provider.generate(
            payload.prompt,
            payload.asset_type,
            view="front",
            excluded_accessories=excluded,
        )
        generated.append(front)
        view_concepts = [("front", front)]
        if payload.asset_type == "character":
            for view in ("left", "back", "right"):
                concept = provider.generate(
                    payload.prompt,
                    payload.asset_type,
                    view=view,
                    reference_images=[front],
                    excluded_accessories=excluded,
                )
                generated.append(concept)
                view_concepts.append((view, concept))
        accessory_concepts = []
        for accessory_name in accessories:
            concept = provider.generate(
                payload.prompt,
                payload.asset_type,
                reference_images=[front],
                accessory_name=accessory_name,
            )
            generated.append(concept)
            accessory_concepts.append((accessory_name, concept))
    finally:
        provider.close()

    views = [
        ConceptReferenceView(
            view=view,
            reference_file=_persist_concept(
                concept,
                f"concept-{payload.asset_type}-{view}{concept.suffix}",
                settings,
                db,
            ),
        )
        for view, concept in view_concepts
    ]
    accessory_records = [
        ConceptAccessory(
            name=name,
            reference_file=_persist_concept(
                concept,
                f"concept-accessory-{name}{concept.suffix}",
                settings,
                db,
            ),
        )
        for name, concept in accessory_concepts
    ]
    usage_tokens = sum(item.usage_tokens or 0 for item in generated) or None
    quality_warnings = (
        assess_character_views(view_concepts) if payload.asset_type == "character" else []
    )
    bundle = ConceptBundle(
        prompt=payload.prompt,
        asset_type=payload.asset_type,
        locale=payload.locale,
        model=provider.model_name,
        view_file_ids=[item.reference_file.id for item in views],
        accessories=[{"name": item.name, "file_id": item.reference_file.id} for item in accessory_records],
        usage_tokens=usage_tokens,
        estimated_cost_fen=30 * len(generated),
        quality_warnings=quality_warnings,
        ready_for_3d=not quality_warnings,
    )
    db.add(bundle)
    db.commit()
    db.refresh(bundle)
    return {"data": _bundle_response(bundle, db, settings)}


@router.get("/latest")
def latest_concept_image(db: Session = Depends(get_db)) -> dict:
    bundle = db.scalar(select(ConceptBundle).order_by(ConceptBundle.created_at.desc()).limit(1))
    if bundle is None:
        raise AppError("CONCEPT_NOT_FOUND", "还没有已保存的参考图", 404)
    return {"data": _bundle_response(bundle, db, get_settings())}


@router.get("/{bundle_id}")
def get_concept_image(bundle_id: str, db: Session = Depends(get_db)) -> dict:
    bundle = db.get(ConceptBundle, bundle_id)
    if bundle is None:
        raise AppError("CONCEPT_NOT_FOUND", "参考图记录不存在", 404)
    return {"data": _bundle_response(bundle, db, get_settings())}
