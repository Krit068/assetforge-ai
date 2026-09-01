from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import base64
import time
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.models import CandidateState, GenerationTask, ReferenceFile, TaskCandidate, TaskState
from app.services.glb_inspector import inspect_glb
from app.services.state_machine import transition


@dataclass(frozen=True)
class GeneratedAsset:
    provider_task_id: str
    model_url: str
    preview_url: str | None
    provider_task_ids: dict[str, str] | None = None
    consumed_credit: float | None = None
    model_name: str | None = None


class TokenHubGenerationProvider:
    def __init__(self, settings: Settings | None = None, transport=None) -> None:
        self.settings = settings or get_settings()
        self.client = httpx.Client(
            timeout=self.settings.model_timeout_seconds,
            transport=transport,
        )

    @property
    def model_name(self) -> str:
        return self.settings.model_name or "tripo-3d-p1"

    @staticmethod
    def face_limit_for_quality(requested_budget: int, quality_tier: str) -> int:
        if quality_tier == "high":
            return 100_000
        return max(1_000, min(requested_budget, 20_000))

    def close(self) -> None:
        self.client.close()

    def _headers(self) -> dict[str, str]:
        if not self.settings.model_api_key:
            raise AppError("MODEL_API_KEY_MISSING", "未配置 TokenHub API Key", 503)
        return {
            "Authorization": f"Bearer {self.settings.model_api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, path: str, payload: dict, *, allow_retries: bool) -> dict:
        base_url = self.settings.model_api_base_url.rstrip("/")
        if not base_url.startswith("https://"):
            raise AppError("MODEL_PROVIDER_CONFIG_INVALID", "模型服务地址必须使用 HTTPS", 500)

        last_error: Exception | None = None
        max_retries = self.settings.model_max_retries if allow_retries else 0
        for attempt in range(max_retries + 1):
            try:
                response = self.client.post(
                    f"{base_url}{path}",
                    headers=self._headers(),
                    json=payload,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        "temporary provider error",
                        request=response.request,
                        response=response,
                    )
                if response.status_code in {400, 401, 402, 403}:
                    try:
                        provider_error = response.json()
                    except ValueError:
                        provider_error = {}
                    provider_code = str(
                        provider_error.get("code")
                        or (provider_error.get("error") or {}).get("code")
                        or ""
                    )
                    request_id = str(provider_error.get("request_id") or "")
                    details = [
                        item
                        for item in (
                            {"provider_code": provider_code} if provider_code else None,
                            {"request_id": request_id} if request_id else None,
                        )
                        if item
                    ]
                    if response.status_code == 402:
                        raise AppError(
                            "MODEL_BILLING_NOT_ENABLED",
                            "TokenHub 3D 生成不可用，请检查后付费与账户余额",
                            402,
                            details=details,
                        )
                    if response.status_code in {401, 403}:
                        raise AppError(
                            "MODEL_AUTH_FAILED",
                            "TokenHub 鉴权失败或当前 Key 无权调用该 3D 模型",
                            503,
                            details=details,
                        )
                    raise AppError(
                        "GENERATION_REQUEST_INVALID",
                        "TokenHub 拒绝了 3D 生成请求参数",
                        422,
                        details=details,
                    )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as error:
                last_error = error
                if attempt >= max_retries:
                    break
                time.sleep(min(2**attempt, 4))
        raise AppError(
            "PROVIDER_UNAVAILABLE",
            "TokenHub 生成服务暂时不可用",
            502,
        ) from last_error

    def _provider_task_id(self, result: dict) -> str:
        provider_task_id = result.get("id")
        status = str(result.get("status") or "").casefold()
        provider_error = result.get("error") or {}
        request_id = str(result.get("request_id") or "")
        provider_code = str(provider_error.get("code") or "") if isinstance(provider_error, dict) else ""
        provider_message = (
            str(provider_error.get("message") or "")[:300]
            if isinstance(provider_error, dict)
            else ""
        )
        details = [
            item
            for item in (
                {"provider_code": provider_code} if provider_code else None,
                {"provider_message": provider_message} if provider_message else None,
                {"request_id": request_id} if request_id else None,
            )
            if item
        ]
        if status in {"failed", "error", "cancelled"} or provider_task_id in {None, ""}:
            raise AppError(
                "GENERATION_REQUEST_REJECTED",
                "TokenHub 在创建 3D 任务时拒绝了请求",
                422,
                details=details,
            )
        if isinstance(provider_task_id, bool) or not isinstance(provider_task_id, (str, int)):
            raise AppError(
                "PROVIDER_RESPONSE_INVALID",
                "TokenHub 返回了无效的任务 ID",
                502,
                details=details,
            )
        return str(provider_task_id)

    def submit_text(self, prompt: str, face_limit: int) -> tuple[str, str]:
        model_name = self.model_name
        payload = {
            "model": model_name,
            "prompt": prompt,
            "negative_prompt": "blurry, low quality, broken mesh, disconnected geometry",
            "face_limit": max(50, min(face_limit, 20_000)),
            "texture": True,
            "pbr": True,
            "texture_quality": "standard",
            "auto_size": True,
        }
        # A timed-out submission may still have created a billable provider task.
        # Never retry this non-idempotent request automatically.
        result = self._request("/v1/api/3d/submit", payload, allow_retries=False)
        return self._provider_task_id(result), model_name

    def _encode_hy3d_image(self, image_path: Path) -> str:
        try:
            contents = image_path.read_bytes()
            with Image.open(BytesIO(contents)) as source:
                source.load()
                image_format = source.format
                image = ImageOps.exif_transpose(source).copy()
        except (OSError, UnidentifiedImageError) as error:
            raise AppError("REFERENCE_FILE_UNAVAILABLE", "参考图文件无法读取", 422) from error

        if image_format not in {"JPEG", "PNG", "WEBP"}:
            raise AppError("REFERENCE_IMAGE_FORMAT_UNSUPPORTED", "参考图格式不受 HY-3D 支持", 422)
        if min(image.size) < 128:
            raise AppError("REFERENCE_IMAGE_TOO_SMALL", "HY-3D 要求参考图单边不小于 128 像素", 422)

        max_encoded_bytes = 6 * 1024 * 1024
        encoded = base64.b64encode(contents)
        if max(image.size) <= 5_000 and len(encoded) <= max_encoded_bytes:
            return encoded.decode("ascii")

        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            rgba = image.convert("RGBA")
            flattened = Image.new("RGB", rgba.size, "white")
            flattened.paste(rgba, mask=rgba.getchannel("A"))
            image = flattened
        else:
            image = image.convert("RGB")

        for max_dimension in (4_096, 3_072, 2_048):
            resized = image.copy()
            resized.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            if min(resized.size) < 128:
                canvas = Image.new(
                    "RGB",
                    (max(128, resized.width), max(128, resized.height)),
                    "white",
                )
                canvas.paste(
                    resized,
                    (
                        (canvas.width - resized.width) // 2,
                        (canvas.height - resized.height) // 2,
                    ),
                )
                resized = canvas
            for quality in (90, 82, 74, 66):
                output = BytesIO()
                resized.save(output, format="JPEG", quality=quality, optimize=True)
                encoded = base64.b64encode(output.getvalue())
                if len(encoded) <= max_encoded_bytes:
                    return encoded.decode("ascii")

        raise AppError("REFERENCE_IMAGE_TOO_LARGE", "参考图无法压缩到 HY-3D 输入限制内", 422)

    def submit_image(self, image_path: Path, face_limit: int) -> tuple[str, str]:
        model_name = "hy-3d-3.1"
        payload = {
            "model": model_name,
            "image_base64": self._encode_hy3d_image(image_path),
            "enable_pbr": True,
            "face_count": max(1_000, min(face_limit, 100_000)),
            "generate_type": "normal",
        }
        # Image-to-3D submission is also billable and non-idempotent.
        result = self._request("/v1/api/3d/submit", payload, allow_retries=False)
        return self._provider_task_id(result), model_name

    def wait_for_result(self, provider_task_id: str, model_name: str) -> GeneratedAsset:
        deadline = time.monotonic() + self.settings.model_timeout_seconds
        while time.monotonic() < deadline:
            result = self._request(
                "/v1/api/3d/query",
                {"model": model_name, "id": provider_task_id},
                allow_retries=True,
            )
            status = str(result.get("status", "")).casefold()
            if status in {"completed", "success", "succeeded"}:
                output = result.get("output") or {}
                model_url = output.get("model_url")
                preview_url = output.get("rendered_image_url") or output.get("generated_image_url")
                if model_name == "hy-3d-3.1":
                    result_files = result.get("data") or []
                    glb_file = next(
                        (
                            item
                            for item in result_files
                            if isinstance(item, dict)
                            and str(item.get("type", "")).casefold() == "glb"
                        ),
                        None,
                    )
                    if glb_file:
                        model_url = glb_file.get("url")
                        preview_url = glb_file.get("preview_image_url") or preview_url
                    preview_url = result.get("preview_image_url") or preview_url
                if not isinstance(model_url, str) or not model_url:
                    raise AppError("PROVIDER_RESPONSE_INVALID", "生成结果缺少模型文件", 502)
                return GeneratedAsset(
                    provider_task_id=provider_task_id,
                    model_url=model_url,
                    preview_url=preview_url if isinstance(preview_url, str) else None,
                )
            if status in {"failed", "cancelled", "error"}:
                raise AppError("GENERATION_FAILED", "TokenHub 生成任务失败", 502)
            time.sleep(3)
        raise AppError("PROVIDER_TIMEOUT", "TokenHub 生成任务等待超时", 504)

    def download(self, url: str, destination: Path, max_bytes: int) -> None:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").casefold()
        allowed_host = hostname.endswith("tencentcos.cn") or hostname.endswith("myqcloud.com")
        if parsed.scheme != "https" or not allowed_host:
            raise AppError("PROVIDER_FILE_URL_INVALID", "模型文件地址不受信任", 502)

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        downloaded = 0
        with self.client.stream("GET", url) as response:
            response.raise_for_status()
            with temporary.open("wb") as output:
                for chunk in response.iter_bytes():
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        temporary.unlink(missing_ok=True)
                        raise AppError("MODEL_FILE_TOO_LARGE", "模型文件超过大小限制", 502)
                    output.write(chunk)
        temporary.replace(destination)


def _mark_task_failed(task_id: str, session_factory, error: AppError) -> None:
    with session_factory() as db:
        task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
        if task is None or task.state in {TaskState.CANCELLED.value, TaskState.READY.value}:
            return
        task.error_code = error.code
        task.error_message = error.message
        try:
            task.state = transition(task.state, TaskState.FAILED)
        except AppError:
            task.state = TaskState.FAILED.value
        task.finished_at = datetime.now(timezone.utc)
        db.commit()


def process_tokenhub_task(
    task_id: str,
    session_factory,
    provider: TokenHubGenerationProvider | None = None,
) -> None:
    active_provider = provider or TokenHubGenerationProvider()
    owns_provider = provider is None
    try:
        with session_factory() as db:
            task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
            if task is None or task.state == TaskState.CANCELLED.value:
                return
            task.state = transition(task.state, TaskState.PREPROCESSING)
            task.state = transition(task.state, TaskState.GEOMETRY)
            game_ready_budget = min(
                20_000,
                int(task.project.spec_profile.get("triangle_budget", 20_000)),
            )
            triangle_budget = active_provider.face_limit_for_quality(
                game_ready_budget,
                task.quality_tier,
            )
            reference_ids = task.reference_file_ids or (
                [task.reference_file_id] if task.reference_file_id else []
            )
            reference_files = [db.get(ReferenceFile, file_id) for file_id in reference_ids]
            if any(item is None for item in reference_files):
                raise AppError("REFERENCE_FILE_NOT_FOUND", "多视图参考图不完整", 404)
            reference_paths = [
                active_provider.settings.asset_storage_root / item.storage_path
                for item in reference_files
                if item is not None
            ]
            work_items = [
                {"role": "main", "name": None, "paths": reference_paths, "asset_type": task.asset_type}
                for _ in range(task.candidate_count)
            ]
            for accessory in task.accessory_references or []:
                file_record = db.get(ReferenceFile, accessory.get("file_id"))
                if file_record is None:
                    raise AppError("REFERENCE_FILE_NOT_FOUND", "独立配件参考图不存在", 404)
                work_items.append({
                    "role": "accessory",
                    "name": accessory.get("name") or "配件",
                    "paths": [active_provider.settings.asset_storage_root / file_record.storage_path],
                    "asset_type": "prop",
                })
            db.commit()

        successful = 0
        had_candidate_failure = False
        last_candidate_error: AppError | None = None
        budget_failed = False
        for position, work_item in enumerate(work_items, start=1):
            with session_factory() as db:
                current = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
                if current is None or current.state == TaskState.CANCELLED.value:
                    return
                candidate = TaskCandidate(
                    position=position,
                    state=CandidateState.RUNNING.value,
                    asset_role=work_item["role"],
                    asset_name=work_item["name"],
                )
                current.candidates.append(candidate)
                db.commit()
                candidate_id = candidate.id
                prompt = current.original_prompt

            try:
                def persist_stage(stage: str, stage_task_id: str) -> None:
                    with session_factory() as stage_db:
                        stage_candidate = stage_db.get(TaskCandidate, candidate_id)
                        if stage_candidate is None:
                            return
                        metrics = dict(stage_candidate.metrics or {})
                        task_ids = dict(metrics.get("provider_task_ids") or {})
                        task_ids[stage] = stage_task_id
                        metrics["provider_task_ids"] = task_ids
                        metrics["pipeline_stage"] = stage
                        stage_candidate.metrics = metrics
                        stage_db.commit()

                item_paths = work_item["paths"]
                if item_paths and hasattr(active_provider, "generate_from_images"):
                    result = active_provider.generate_from_images(
                        item_paths,
                        triangle_budget,
                        asset_type=work_item["asset_type"],
                        quality_tier=task.quality_tier,
                        stage_callback=persist_stage,
                    )
                    provider_task_id = result.provider_task_id
                    model_name = result.model_name or active_provider.model_name
                elif item_paths:
                    provider_task_id, model_name = active_provider.submit_image(
                        item_paths[0], triangle_budget
                    )
                    persist_stage("model", provider_task_id)
                    result = active_provider.wait_for_result(provider_task_id, model_name)
                else:
                    provider_task_id, model_name = active_provider.submit_text(prompt, triangle_budget)
                    persist_stage("model", provider_task_id)
                    result = active_provider.wait_for_result(provider_task_id, model_name)
                generated_dir = active_provider.settings.asset_storage_root / "generated" / task_id
                model_path = generated_dir / f"candidate-{position}.glb"
                active_provider.download(
                    result.model_url,
                    model_path,
                    active_provider.settings.max_model_file_mb * 1024 * 1024,
                )
                preview_path: Path | None = None
                if result.preview_url:
                    preview_suffix = Path(urlparse(result.preview_url).path).suffix.casefold()
                    if preview_suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
                        preview_suffix = ".png"
                    preview_path = generated_dir / f"candidate-{position}{preview_suffix}"
                    active_provider.download(result.preview_url, preview_path, 20 * 1024 * 1024)

                with session_factory() as db:
                    candidate = db.get(TaskCandidate, candidate_id)
                    if candidate is None:
                        continue
                    public_base = active_provider.settings.public_base_url.rstrip("/")
                    candidate.state = CandidateState.READY.value
                    candidate.model_url = f"{public_base}/assets/generated/{task_id}/{model_path.name}"
                    candidate.preview_url = (
                        f"{public_base}/assets/generated/{task_id}/{preview_path.name}"
                        if preview_path
                        else None
                    )
                    try:
                        inspected_metrics = inspect_glb(model_path)
                    except AppError as inspection_error:
                        inspected_metrics = {"inspection_error": inspection_error.code}
                    triangle_count = inspected_metrics.get("triangle_count")
                    triangle_budget_passed = not isinstance(triangle_count, int) or triangle_count <= triangle_budget
                    budget_failed = budget_failed or not triangle_budget_passed
                    candidate.metrics = {
                        "target_triangle_count": triangle_budget,
                        "triangle_budget_passed": triangle_budget_passed,
                        "pbr_requested": True,
                        "provider_task_id": provider_task_id,
                        "provider_task_ids": result.provider_task_ids or {"model": provider_task_id},
                        "model": model_name,
                        "quality_tier": task.quality_tier,
                        "reference_view_count": len(item_paths),
                        "consumed_credit": result.consumed_credit,
                        **inspected_metrics,
                    }
                    current_task = db.get(GenerationTask, task_id)
                    if current_task is not None:
                        current_task.model_version = model_name
                    db.commit()
                    successful += 1
            except AppError as error:
                had_candidate_failure = True
                last_candidate_error = error
                with session_factory() as db:
                    candidate = db.get(TaskCandidate, candidate_id)
                    if candidate is not None:
                        candidate.state = CandidateState.FAILED.value
                        candidate.error_code = error.code
                        metrics = dict(candidate.metrics or {})
                        metrics["error_details"] = error.details
                        candidate.metrics = metrics
                        db.commit()

        if successful == 0:
            raise last_candidate_error or AppError(
                "GENERATION_FAILED",
                "所有候选均生成失败",
                502,
            )

        with session_factory() as db:
            task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
            if task is None or task.state == TaskState.CANCELLED.value:
                return
            for state in (
                TaskState.TEXTURING,
                TaskState.POST_PROCESSING,
                TaskState.QA,
            ):
                task.state = transition(task.state, state)
            task.state = transition(
                task.state,
                TaskState.NEEDS_FIX if budget_failed or had_candidate_failure else TaskState.READY,
            )
            task.finished_at = datetime.now(timezone.utc)
            db.commit()
    except AppError as error:
        _mark_task_failed(task_id, session_factory, error)
    finally:
        if owns_provider:
            active_provider.close()
