from __future__ import annotations

from dataclasses import dataclass
from binascii import Error as BinasciiError
from io import BytesIO
import base64
import re
import time
from urllib.parse import urlparse

import httpx
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings, get_settings
from app.core.errors import AppError


@dataclass(frozen=True)
class GeneratedConcept:
    contents: bytes
    mime_type: str
    suffix: str
    width: int
    height: int
    usage_tokens: int | None


class TokenHubConceptImageProvider:
    def __init__(self, settings: Settings | None = None, transport=None) -> None:
        self.settings = settings or get_settings()
        self.client = httpx.Client(
            timeout=self.settings.image_model_timeout_seconds,
            transport=transport,
        )

    @property
    def model_name(self) -> str:
        return self.settings.image_model_name or "seedream-image-v5.0-pro"

    def close(self) -> None:
        self.client.close()

    def _headers(self) -> dict[str, str]:
        if not self.settings.model_api_key:
            raise AppError("MODEL_API_KEY_MISSING", "未配置 TokenHub API Key", 503)
        return {
            "Authorization": f"Bearer {self.settings.model_api_key}",
            "Content-Type": "application/json",
        }

    def _provider_prompt(
        self,
        prompt: str,
        asset_type: str,
        *,
        view: str = "front",
        accessory_name: str | None = None,
        excluded_accessories: tuple[str, ...] = (),
    ) -> str:
        view_copy = {
            "front": "FRONT orthographic",
            "left": "left-side orthographic view, LEFT PROFILE (face and body point left)",
            "back": "BACK orthographic (face invisible)",
            "right": "RIGHT PROFILE orthographic (face and body point right)",
        }
        if accessory_name:
            framing = (
                f"Create one isolated 3D game accessory concept: {accessory_name}. Show only this accessory, "
                "never a person or body part. Center the complete object in a clear three-quarter view on a plain "
                "neutral background, even lighting, unobstructed silhouette, no text, no watermark. Match the "
                "character's art direction and colors."
            )
        if asset_type == "character":
            if not accessory_name:
                excluded = ", ".join(excluded_accessories) or "detachable props"
                framing = (
                    f"MANDATORY: exactly one intact full-body character, {view_copy.get(view, view_copy['front'])} view, "
                    "standard symmetric A-pose, head-to-feet visible. One view only; no collage. Arms away from torso; "
                    "limbs anatomically connected; no cropped limbs, split, duplicate, transparency or occlusion. "
                    f"NO weapons, held items, props, or detachable accessories ({excluded}). "
                    "Plain neutral background, even light, no perspective, text or watermark."
                )
        elif not accessory_name:
            framing = (
                "Create one production-ready 3D game asset concept image. Show a single complete object "
                "in a clear three-quarter front view, centered on a plain neutral studio background, "
                "with a readable silhouette, no extra props, no text, no watermark."
            )
        # Hard constraints must never be truncated. Remove phrases that conflict
        # with reconstruction inputs; accessories are generated separately.
        user_requirement = " ".join(prompt.strip().split())
        for accessory in excluded_accessories:
            user_requirement = user_requirement.replace(accessory, "")
        user_requirement = user_requirement.replace("剑修", "修仙者")
        user_requirement = re.sub(
            r"(轻微动态展示姿势|动态展示姿势|战斗姿势|动态姿势|自然站姿)",
            "标准A姿势",
            user_requirement,
        )
        available = max(0, 600 - len(framing) - len(" DESIGN: "))
        return f"{framing} DESIGN: {user_requirement[:available]}"

    def _request(self, payload: dict) -> dict:
        base_url = self.settings.model_api_base_url.rstrip("/")
        if not base_url.startswith("https://"):
            raise AppError("MODEL_PROVIDER_CONFIG_INVALID", "模型服务地址必须使用 HTTPS", 500)
        last_error: Exception | None = None
        for attempt in range(self.settings.image_model_max_retries + 1):
            try:
                response = self.client.post(
                    f"{base_url}/v1/wand/si-image/generation",
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
                            "TokenHub 未开启后付费且已无免费额度，请先在在线推理服务中开启后付费",
                            402,
                            details=details,
                        )
                    if response.status_code in {401, 403}:
                        raise AppError(
                            "MODEL_AUTH_FAILED",
                            "TokenHub 鉴权失败或当前 Key 无权调用该模型",
                            503,
                            details=details,
                        )
                    raise AppError(
                        "CONCEPT_REQUEST_INVALID",
                        "TokenHub 拒绝了概念图请求参数",
                        422,
                        details=details,
                    )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as error:
                last_error = error
                if attempt >= self.settings.image_model_max_retries:
                    break
                time.sleep(min(2**attempt, 4))
        raise AppError("CONCEPT_PROVIDER_UNAVAILABLE", "概念图生成服务暂时不可用", 502) from last_error

    def _download(self, url: str) -> bytes:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").casefold()
        allowed_host = any(
            hostname.endswith(suffix)
            for suffix in (
                "tencentcos.cn",
                "myqcloud.com",
                "volces.com",
                "byteimg.com",
            )
        )
        if parsed.scheme != "https" or not allowed_host:
            raise AppError("CONCEPT_IMAGE_URL_INVALID", "概念图下载地址不受信任", 502)

        max_bytes = self.settings.max_concept_image_mb * 1024 * 1024
        output = BytesIO()
        with self.client.stream("GET", url) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                if output.tell() + len(chunk) > max_bytes:
                    raise AppError("CONCEPT_IMAGE_TOO_LARGE", "概念图超过大小限制", 502)
                output.write(chunk)
        return output.getvalue()

    @staticmethod
    def _data_url(concept: GeneratedConcept) -> str:
        encoded = base64.b64encode(concept.contents).decode("ascii")
        return f"data:{concept.mime_type};base64,{encoded}"

    def generate(
        self,
        prompt: str,
        asset_type: str,
        *,
        view: str = "front",
        reference_images: list[GeneratedConcept] | None = None,
        accessory_name: str | None = None,
        excluded_accessories: tuple[str, ...] = (),
    ) -> GeneratedConcept:
        payload = {
            "model": self.model_name,
            "prompt": self._provider_prompt(
                prompt,
                asset_type,
                view=view,
                accessory_name=accessory_name,
                excluded_accessories=excluded_accessories,
            ),
            "size": "2K",
            "response_format": "b64_json",
            "watermark": False,
        }
        if reference_images:
            payload["images"] = [self._data_url(image) for image in reference_images]
        result = self._request(payload)
        data = result.get("data") or []
        if isinstance(data, dict):
            data = [data]
        first = data[0] if isinstance(data, list) and data else {}
        if not isinstance(first, dict):
            first = {}

        encoded = first.get("b64_json")
        url = first.get("url")
        try:
            if isinstance(encoded, str) and encoded:
                contents = base64.b64decode(encoded, validate=True)
            elif isinstance(url, str) and url:
                contents = self._download(url)
            else:
                raise AppError("CONCEPT_PROVIDER_RESPONSE_INVALID", "概念图结果缺少图片", 502)
        except (ValueError, BinasciiError) as error:
            raise AppError("CONCEPT_PROVIDER_RESPONSE_INVALID", "概念图数据无法解码", 502) from error

        max_bytes = self.settings.max_concept_image_mb * 1024 * 1024
        if not contents or len(contents) > max_bytes:
            raise AppError("CONCEPT_IMAGE_TOO_LARGE", "概念图为空或超过大小限制", 502)
        try:
            with Image.open(BytesIO(contents)) as image:
                image.load()
                image_format = image.format
                width, height = image.size
        except (UnidentifiedImageError, OSError) as error:
            raise AppError("CONCEPT_PROVIDER_RESPONSE_INVALID", "概念图结果不是有效图片", 502) from error

        formats = {
            "JPEG": ("image/jpeg", ".jpg"),
            "PNG": ("image/png", ".png"),
            "WEBP": ("image/webp", ".webp"),
        }
        if image_format not in formats:
            raise AppError("CONCEPT_IMAGE_FORMAT_UNSUPPORTED", "概念图格式不受支持", 502)
        mime_type, suffix = formats[image_format]
        usage = result.get("tokenhub_usage") or result.get("usage") or {}
        usage_tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
        return GeneratedConcept(
            contents=contents,
            mime_type=mime_type,
            suffix=suffix,
            width=width,
            height=height,
            usage_tokens=usage_tokens if isinstance(usage_tokens, int) else None,
        )
