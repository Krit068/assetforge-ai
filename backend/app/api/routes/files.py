from io import BytesIO
from pathlib import Path
from uuid import uuid4
import warnings

from fastapi import APIRouter, Depends, File, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.database import get_db
from app.db.models import ReferenceFile
from app.schemas.files import ReferenceFileResponse


router = APIRouter(prefix="/files", tags=["files"])

IMAGE_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}


def _response(record: ReferenceFile) -> ReferenceFileResponse:
    public_base = get_settings().public_base_url.rstrip("/")
    return ReferenceFileResponse(
        id=record.id,
        original_name=record.original_name,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        width=record.width,
        height=record.height,
        preview_url=f"{public_base}/assets/{record.storage_path}",
    )


@router.post("/reference-images", status_code=201)
async def upload_reference_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    settings = get_settings()
    max_bytes = settings.max_reference_image_mb * 1024 * 1024
    contents = await file.read(max_bytes + 1)
    await file.close()
    if not contents:
        raise AppError("REFERENCE_IMAGE_EMPTY", "参考图为空", 422)
    if len(contents) > max_bytes:
        raise AppError(
            "REFERENCE_IMAGE_TOO_LARGE",
            f"参考图不能超过 {settings.max_reference_image_mb} MB",
            413,
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(contents)) as image:
                image_format = image.format
                width, height = image.size
                is_animated = bool(getattr(image, "is_animated", False))
                image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AppError("REFERENCE_IMAGE_INVALID", "文件不是有效的 PNG、JPG 或 WebP 图片", 422)

    if image_format not in IMAGE_FORMATS:
        raise AppError("REFERENCE_IMAGE_FORMAT_UNSUPPORTED", "仅支持 PNG、JPG 和 WebP", 415)
    if is_animated:
        raise AppError("REFERENCE_IMAGE_ANIMATED", "暂不支持动图，请上传单帧图片", 422)
    if min(width, height) < 128 or max(width, height) > settings.max_reference_image_dimension:
        raise AppError(
            "REFERENCE_IMAGE_DIMENSIONS_INVALID",
            f"图片边长需在 128–{settings.max_reference_image_dimension} 像素之间",
            422,
        )

    mime_type, suffix = IMAGE_FORMATS[image_format]
    file_id = str(uuid4())
    relative_path = Path("uploads") / f"{file_id}{suffix}"
    destination = settings.asset_storage_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(contents)
    temporary.replace(destination)

    original_name = Path(file.filename or "reference-image").name[:255]
    record = ReferenceFile(
        id=file_id,
        original_name=original_name,
        mime_type=mime_type,
        storage_path=relative_path.as_posix(),
        size_bytes=len(contents),
        width=width,
        height=height,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"data": _response(record)}


@router.delete("/reference-images/{file_id}")
def delete_reference_image(file_id: str, db: Session = Depends(get_db)) -> dict:
    record = db.get(ReferenceFile, file_id)
    if record is None:
        raise AppError("REFERENCE_FILE_NOT_FOUND", "参考图不存在或已被移除", 404)

    settings = get_settings()
    storage_root = settings.asset_storage_root.resolve()
    destination = (storage_root / record.storage_path).resolve()
    if destination.is_relative_to(storage_root):
        destination.unlink(missing_ok=True)
    db.delete(record)
    db.commit()
    return {"data": {"id": file_id, "deleted": True}}
