from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Callable
import ipaddress
import time
from urllib.parse import urlparse

import httpx
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.services.tokenhub_generation import GeneratedAsset, process_tokenhub_task


class TripoGenerationProvider:
    """Official Tripo API adapter for text/image-to-3D generation."""

    def __init__(self, settings: Settings | None = None, transport=None) -> None:
        self.settings = settings or get_settings()
        self.client = httpx.Client(
            timeout=self.settings.model_timeout_seconds,
            transport=transport,
        )

    @property
    def model_name(self) -> str:
        return self.settings.tripo_model_version or "P1-20260311"

    @staticmethod
    def face_limit_for_quality(requested_budget: int, quality_tier: str) -> int:
        if quality_tier == "high":
            return 2_000_000
        return max(48, min(requested_budget, 20_000))

    def close(self) -> None:
        self.client.close()

    def _headers(self, *, json_content: bool = False) -> dict[str, str]:
        api_key = self.settings.tripo_api_key.strip()
        if not api_key:
            raise AppError("MODEL_API_KEY_MISSING", "未配置 Tripo 官方 API Key", 503)
        if not api_key.startswith("tsk_"):
            raise AppError(
                "MODEL_PROVIDER_CONFIG_INVALID",
                "Tripo 官方 API Key 格式无效，应使用 tsk_ 开头的独立密钥",
                500,
            )
        headers = {"Authorization": f"Bearer {api_key}"}
        if json_content:
            headers["Content-Type"] = "application/json"
        return headers

    def _base_url(self) -> str:
        base_url = self.settings.tripo_api_base_url.rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or parsed.hostname != "api.tripo3d.ai":
            raise AppError(
                "MODEL_PROVIDER_CONFIG_INVALID",
                "Tripo API 地址必须使用官方 HTTPS 域名",
                500,
            )
        return base_url

    @staticmethod
    def _error_details(result: dict, response: httpx.Response) -> list[dict]:
        provider_code = result.get("code")
        message = str(result.get("message") or result.get("error_msg") or "")[:300]
        suggestion = str(result.get("suggestion") or "")[:300]
        trace_id = str(response.headers.get("X-Tripo-Trace-ID") or "")[:120]
        return [
            item
            for item in (
                {"provider_code": str(provider_code)}
                if provider_code not in {None, 0, "0", ""}
                else None,
                {"provider_message": message} if message else None,
                {"provider_suggestion": suggestion} if suggestion else None,
                {"trace_id": trace_id} if trace_id else None,
            )
            if item
        ]

    def _raise_provider_error(
        self,
        response: httpx.Response,
        result: dict,
        *,
        operation: str,
    ) -> None:
        details = self._error_details(result, response)
        if response.status_code == 402:
            raise AppError(
                "MODEL_BILLING_NOT_ENABLED",
                "Tripo 额度不足或当前账号未启用 API 计费",
                402,
                details=details,
            )
        if response.status_code in {401, 403}:
            raise AppError(
                "MODEL_AUTH_FAILED",
                "Tripo 鉴权失败或当前 Key 无权调用该模型",
                503,
                details=details,
            )
        if response.status_code == 429 or str(result.get("code") or "") == "2000":
            raise AppError(
                "MODEL_RATE_LIMITED",
                "Tripo 当前请求过多，请稍后再试",
                429,
                details=details,
            )
        if operation == "query" and (
            response.status_code == 404 or str(result.get("code") or "") == "2001"
        ):
            raise AppError(
                "PROVIDER_TASK_NOT_FOUND",
                "Tripo 未找到对应生成任务",
                502,
                details=details,
            )
        raise AppError(
            "GENERATION_REQUEST_REJECTED",
            "Tripo 拒绝了 3D 生成请求",
            422,
            details=details,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
        files: dict | None = None,
        allow_retries: bool,
        operation: str,
    ) -> dict:
        max_retries = self.settings.model_max_retries if allow_retries else 0
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = self.client.request(
                    method,
                    f"{self._base_url()}{path}",
                    headers=self._headers(json_content=payload is not None),
                    json=payload,
                    files=files,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        "temporary Tripo provider error",
                        request=response.request,
                        response=response,
                    )
                try:
                    result = response.json()
                except ValueError as error:
                    raise AppError(
                        "PROVIDER_RESPONSE_INVALID",
                        "Tripo 返回了无法解析的响应",
                        502,
                    ) from error
                if not isinstance(result, dict):
                    raise AppError(
                        "PROVIDER_RESPONSE_INVALID",
                        "Tripo 返回的数据结构无效",
                        502,
                    )
                if response.status_code >= 400 or result.get("code") not in {None, 0, "0"}:
                    self._raise_provider_error(response, result, operation=operation)
                return result
            except AppError:
                raise
            except httpx.HTTPError as error:
                last_error = error
                if attempt >= max_retries:
                    break
                time.sleep(min(2**attempt, 4))
        raise AppError(
            "PROVIDER_UNAVAILABLE",
            "Tripo 生成服务暂时不可用",
            502,
        ) from last_error

    @staticmethod
    def _task_id(result: dict) -> str:
        data = result.get("data") or {}
        task_id = data.get("task_id") if isinstance(data, dict) else None
        if not isinstance(task_id, str) or not task_id:
            raise AppError(
                "PROVIDER_RESPONSE_INVALID",
                "Tripo 创建响应缺少任务 ID",
                502,
            )
        return task_id

    def submit_text(self, prompt: str, face_limit: int) -> tuple[str, str]:
        clean_prompt = prompt.strip()
        if not clean_prompt or len(clean_prompt) > 1_024:
            raise AppError(
                "GENERATION_REQUEST_INVALID",
                "Tripo 文生 3D 描述必须为 1 至 1024 个字符",
                422,
            )
        result = self._request_json(
            "POST",
            "/task",
            payload={
                "type": "text_to_model",
                "model_version": self.model_name,
                "prompt": clean_prompt,
                "face_limit": max(48, min(face_limit, 20_000)),
                "texture": True,
                "pbr": True,
                "texture_quality": "detailed",
                "auto_size": True,
            },
            allow_retries=False,
            operation="submit",
        )
        return self._task_id(result), self.model_name

    @staticmethod
    def _image_metadata(image_path: Path) -> tuple[str, str, bytes]:
        try:
            contents = image_path.read_bytes()
            with Image.open(BytesIO(contents)) as image:
                image.load()
                image_format = image.format
                width, height = image.size
        except (OSError, UnidentifiedImageError) as error:
            raise AppError("REFERENCE_FILE_UNAVAILABLE", "参考图文件无法读取", 422) from error

        formats = {
            "JPEG": ("jpg", "image/jpeg"),
            "PNG": ("png", "image/png"),
            "WEBP": ("webp", "image/webp"),
        }
        if image_format not in formats:
            raise AppError("REFERENCE_IMAGE_FORMAT_UNSUPPORTED", "参考图格式不受 Tripo 支持", 422)
        if width < 256 or height < 256:
            raise AppError("REFERENCE_IMAGE_TOO_SMALL", "Tripo 建议参考图单边不小于 256 像素", 422)
        if not contents or len(contents) > 20 * 1024 * 1024:
            raise AppError("REFERENCE_IMAGE_TOO_LARGE", "Tripo 要求参考图不超过 20MB", 422)
        file_type, mime_type = formats[image_format]
        return file_type, mime_type, contents

    def _upload_image(self, image_path: Path) -> tuple[str, str]:
        file_type, mime_type, contents = self._image_metadata(image_path)
        result = self._request_json(
            "POST",
            "/upload/sts",
            files={"file": (f"reference.{file_type}", contents, mime_type)},
            allow_retries=True,
            operation="upload",
        )
        data = result.get("data") or {}
        image_token = (
            data.get("image_token") or data.get("file_token")
            if isinstance(data, dict)
            else None
        )
        if not isinstance(image_token, str) or not image_token:
            raise AppError(
                "PROVIDER_RESPONSE_INVALID",
                "Tripo 图片上传响应缺少文件令牌",
                502,
            )
        return image_token, file_type

    def submit_image(self, image_path: Path, face_limit: int) -> tuple[str, str]:
        image_token, file_type = self._upload_image(image_path)
        result = self._request_json(
            "POST",
            "/task",
            payload={
                "type": "image_to_model",
                "model_version": self.model_name,
                "file": {"type": file_type, "file_token": image_token},
                "face_limit": max(48, min(face_limit, 20_000)),
                "texture": True,
                "pbr": True,
                "texture_quality": "detailed",
                "auto_size": True,
                "render_image": True,
            },
            allow_retries=False,
            operation="submit",
        )
        return self._task_id(result), self.model_name

    @staticmethod
    def _consumed_credit(data: dict) -> float:
        value = data.get("consumed_credit")
        return float(value) if isinstance(value, (int, float)) else 0.0

    def _wait_for_task_data(self, provider_task_id: str) -> dict:
        deadline = time.monotonic() + self.settings.model_timeout_seconds
        while time.monotonic() < deadline:
            result = self._request_json(
                "GET",
                f"/task/{provider_task_id}",
                allow_retries=True,
                operation="query",
            )
            data = result.get("data") or {}
            if not isinstance(data, dict):
                raise AppError("PROVIDER_RESPONSE_INVALID", "Tripo 任务响应结构无效", 502)
            status = str(data.get("status") or "").casefold()
            if status == "success":
                return data
            if status in {"failed", "cancelled", "unknown", "banned", "expired"}:
                details = [
                    {"provider_task_id": provider_task_id},
                    {"provider_status": status},
                ]
                error_code = data.get("error_code")
                error_message = str(data.get("error_msg") or "")[:300]
                if error_code not in {None, ""}:
                    details.append({"provider_code": str(error_code)})
                if error_message:
                    details.append({"provider_message": error_message})
                if status == "banned":
                    raise AppError(
                        "GENERATION_CONTENT_REJECTED",
                        "Tripo 内容审核未通过",
                        422,
                        details=details,
                    )
                raise AppError(
                    "GENERATION_FAILED",
                    "Tripo 生成任务失败",
                    502,
                    details=details,
                )
            time.sleep(3)
        raise AppError("PROVIDER_TIMEOUT", "Tripo 生成任务等待超时", 504)

    @staticmethod
    def _asset_urls(data: dict) -> tuple[str, str | None]:
        output = data.get("output") or {}
        if not isinstance(output, dict):
            output = {}
        model_url = output.get("pbr_model") or output.get("model") or output.get("base_model")
        preview_url = output.get("rendered_image") or output.get("generated_image")
        if not isinstance(model_url, str) or not model_url:
            raise AppError("PROVIDER_RESPONSE_INVALID", "Tripo 结果缺少模型文件", 502)
        return model_url, preview_url if isinstance(preview_url, str) else None

    def generate_from_images(
        self,
        image_paths: list[Path],
        face_limit: int,
        *,
        asset_type: str,
        quality_tier: str,
        stage_callback: Callable[[str, str], None] | None = None,
    ) -> GeneratedAsset:
        if not image_paths:
            raise AppError("GENERATION_INPUT_REQUIRED", "Tripo 缺少参考图", 422)
        if len(image_paths) not in {1, 4}:
            raise AppError("MULTIVIEW_INPUT_INVALID", "人物多视图必须包含正、左、后、右四张图", 422)

        notify = stage_callback or (lambda _stage, _task_id: None)
        uploaded = [self._upload_image(path) for path in image_paths]
        task_ids: dict[str, str] = {}
        consumed_credit = 0.0
        multiview_task_id: str | None = None

        if asset_type == "character" and len(uploaded) == 1:
            token, file_type = uploaded[0]
            result = self._request_json(
                "POST",
                "/task",
                payload={
                    "type": "generate_multiview_image",
                    "file": {"type": file_type, "file_token": token},
                },
                allow_retries=False,
                operation="submit",
            )
            multiview_task_id = self._task_id(result)
            task_ids["multiview_image"] = multiview_task_id
            notify("multiview_image", multiview_task_id)
            multiview_data = self._wait_for_task_data(multiview_task_id)
            consumed_credit += self._consumed_credit(multiview_data)

        is_high = quality_tier == "high"
        model_version = "v3.1-20260211" if is_high else self.model_name
        common = {
            "model_version": model_version,
            "face_limit": 2_000_000 if is_high else max(48, min(face_limit, 20_000)),
            "texture": True,
            "pbr": True,
            "texture_quality": "extreme" if is_high else "detailed",
            "auto_size": True,
            "render_image": True,
        }
        if is_high:
            common["geometry_quality"] = "detailed"

        if asset_type == "character":
            model_payload = {"type": "multiview_to_model", **common}
            if multiview_task_id:
                model_payload["original_task_id"] = multiview_task_id
            else:
                model_payload["files"] = [
                    {"type": file_type, "file_token": token}
                    for token, file_type in uploaded[:4]
                ]
        else:
            token, file_type = uploaded[0]
            model_payload = {
                "type": "image_to_model",
                "file": {"type": file_type, "file_token": token},
                **common,
            }

        model_result = self._request_json(
            "POST",
            "/task",
            payload=model_payload,
            allow_retries=False,
            operation="submit",
        )
        model_task_id = self._task_id(model_result)
        task_ids["detailed_model" if is_high else "model"] = model_task_id
        notify("detailed_model" if is_high else "model", model_task_id)
        model_data = self._wait_for_task_data(model_task_id)
        consumed_credit += self._consumed_credit(model_data)
        model_url, preview_url = self._asset_urls(model_data)

        return GeneratedAsset(
            provider_task_id=model_task_id,
            provider_task_ids=task_ids,
            model_url=model_url,
            preview_url=preview_url,
            consumed_credit=consumed_credit or None,
            model_name=model_version,
        )

    def wait_for_result(self, provider_task_id: str, model_name: str) -> GeneratedAsset:
        data = self._wait_for_task_data(provider_task_id)
        model_url, preview_url = self._asset_urls(data)
        return GeneratedAsset(
            provider_task_id=provider_task_id,
            model_url=model_url,
            preview_url=preview_url,
            consumed_credit=self._consumed_credit(data) or None,
            model_name=model_name,
        )

    @staticmethod
    def _validate_download_url(url: str) -> None:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").casefold()
        if (
            parsed.scheme != "https"
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or hostname == "localhost"
            or hostname.endswith(".localhost")
            or hostname.endswith(".local")
        ):
            raise AppError("PROVIDER_FILE_URL_INVALID", "Tripo 文件地址不受信任", 502)
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            return
        if not address.is_global:
            raise AppError("PROVIDER_FILE_URL_INVALID", "Tripo 文件地址不受信任", 502)

    def download(self, url: str, destination: Path, max_bytes: int) -> None:
        self._validate_download_url(url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        downloaded = 0
        try:
            with self.client.stream("GET", url) as response:
                response.raise_for_status()
                with temporary.open("wb") as output:
                    for chunk in response.iter_bytes():
                        downloaded += len(chunk)
                        if downloaded > max_bytes:
                            raise AppError("MODEL_FILE_TOO_LARGE", "模型文件超过大小限制", 502)
                        output.write(chunk)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise


def process_tripo_task(task_id: str, session_factory) -> None:
    provider = TripoGenerationProvider()
    try:
        # The persisted generation pipeline is provider-agnostic; the legacy
        # function name is kept to avoid changing already-tested TokenHub flow.
        process_tokenhub_task(task_id, session_factory, provider)
    finally:
        provider.close()
