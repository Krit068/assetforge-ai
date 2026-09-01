from io import BytesIO
import base64
import json

import httpx
from PIL import Image
import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.services.concept_image import TokenHubConceptImageProvider


def png_base64() -> str:
    buffer = BytesIO()
    Image.new("RGB", (1024, 1024), (45, 67, 80)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_seedream_concept_generation_uses_single_2k_image_request(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/wand/si-image/generation"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "seedream-image-v5.0-pro"
        assert payload["size"] == "2K"
        assert "three-quarter front view" in payload["prompt"]
        assert "青铜宝箱" in payload["prompt"]
        assert "images" not in payload
        return httpx.Response(
            200,
            json={
                "data": [{"output_format": "png", "b64_json": png_base64()}],
                "tokenhub_usage": {"total_tokens": 30_000},
            },
        )

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        image_model_name="seedream-image-v5.0-pro",
        model_max_retries=0,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubConceptImageProvider(settings, httpx.MockTransport(handler))

    result = provider.generate("低多边形青铜宝箱", "prop")
    provider.close()

    assert result.mime_type == "image/png"
    assert result.suffix == ".png"
    assert result.width == 1024
    assert result.height == 1024
    assert result.usage_tokens == 30_000


def test_character_concept_prompt_requires_full_body(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert "full-body" in payload["prompt"]
        assert "no cropped limbs" in payload["prompt"]
        return httpx.Response(200, json={"data": [{"b64_json": png_base64()}]})

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        model_max_retries=0,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubConceptImageProvider(settings, httpx.MockTransport(handler))
    result = provider.generate("奇幻女战士", "character")
    provider.close()

    assert result.width == 1024


def test_character_side_view_reuses_front_and_never_splits_body(tmp_path):
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        return httpx.Response(200, json={"data": [{"b64_json": png_base64()}]})

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        image_model_max_retries=0,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubConceptImageProvider(settings, httpx.MockTransport(handler))
    front = provider.generate(
        "仙侠少女，手持长剑",
        "character",
        excluded_accessories=("长剑",),
    )
    provider.generate(
        "仙侠少女，手持长剑",
        "character",
        view="left",
        reference_images=[front],
        excluded_accessories=("长剑",),
    )
    provider.generate(
        "仙侠少女，手持长剑",
        "character",
        reference_images=[front],
        accessory_name="长剑",
    )
    provider.close()

    assert "images" not in requests[0]
    assert requests[1]["images"][0].startswith("data:image/png;base64,")
    assert "left-side orthographic view" in requests[1]["prompt"]
    assert "anatomically connected" in requests[1]["prompt"]
    assert "Show only this accessory" in requests[2]["prompt"]
    assert "never a person or body part" in requests[2]["prompt"]
    assert all(len(payload["prompt"]) <= 600 for payload in requests)


def test_seedream_reports_billing_not_enabled_without_retry(tmp_path):
    request_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            402,
            json={
                "code": "401007",
                "message": "postpaid billing is not enabled",
                "request_id": "request-safe-id",
            },
        )

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        image_model_max_retries=0,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubConceptImageProvider(settings, httpx.MockTransport(handler))

    with pytest.raises(AppError) as captured:
        provider.generate("青铜宝箱", "prop")
    provider.close()

    assert captured.value.code == "MODEL_BILLING_NOT_ENABLED"
    assert request_count == 1
