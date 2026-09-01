import base64
from io import BytesIO

import httpx
import pytest
from PIL import Image

from app.core.config import Settings
from app.core.errors import AppError
from app.services.tokenhub_generation import TokenHubGenerationProvider


def test_tokenhub_submit_query_and_download_without_forwarding_key(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/api/3d/submit":
            assert request.headers["Authorization"] == "Bearer test-key"
            return httpx.Response(200, json={"id": "provider-task-1", "status": "queued"})
        if request.url.path == "/v1/api/3d/query":
            assert request.headers["Authorization"] == "Bearer test-key"
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "output": {
                        "model_url": "https://assets.tencentcos.cn/output/model.glb",
                        "rendered_image_url": "https://assets.tencentcos.cn/output/preview.png",
                    },
                },
            )
        if request.url.host == "assets.tencentcos.cn":
            assert "Authorization" not in request.headers
            return httpx.Response(200, content=b"glTF-test")
        raise AssertionError(f"unexpected request: {request.url}")

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        model_name="tripo-3d-p1",
        model_timeout_seconds=5,
        model_max_retries=0,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubGenerationProvider(settings, httpx.MockTransport(handler))

    provider_task_id, model_name = provider.submit_text("低多边形青铜宝箱", 10_000)
    result = provider.wait_for_result(provider_task_id, model_name)
    destination = tmp_path / "generated" / "candidate.glb"
    provider.download(result.model_url, destination, 1024)
    provider.close()

    assert destination.read_bytes() == b"glTF-test"


def test_tokenhub_image_submit_uses_hy3d_base64(tmp_path):
    image_path = tmp_path / "reference.png"
    Image.new("RGB", (256, 256), "green").save(image_path)
    expected_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        if request.url.path == "/v1/api/3d/submit":
            assert payload["model"] == "hy-3d-3.1"
            assert payload["image_base64"] == expected_base64
            assert "prompt" not in payload
            return httpx.Response(200, json={"id": "image-task-1"})
        if request.url.path == "/v1/api/3d/query":
            assert payload == {"model": "hy-3d-3.1", "id": "image-task-1"}
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": [
                        {
                            "type": "glb",
                            "url": "https://assets.tencentcos.cn/model.glb",
                            "preview_image_url": "https://assets.tencentcos.cn/preview.jpg",
                        }
                    ],
                },
            )
        raise AssertionError(f"unexpected request: {request.url}")

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        model_timeout_seconds=5,
        model_max_retries=0,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubGenerationProvider(settings, httpx.MockTransport(handler))

    provider_task_id, model_name = provider.submit_image(image_path, 10_000)
    result = provider.wait_for_result(provider_task_id, model_name)
    provider.close()

    assert result.model_url.endswith("model.glb")
    assert result.preview_url.endswith("preview.jpg")


def test_hy3d_image_is_resized_to_provider_limits(tmp_path):
    image_path = tmp_path / "wide-reference.png"
    Image.new("RGB", (5_200, 160), "purple").save(image_path)
    submitted_payload: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        submitted_payload.update(__import__("json").loads(request.content))
        return httpx.Response(200, json={"id": "resized-image-task"})

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        model_timeout_seconds=5,
        model_max_retries=0,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubGenerationProvider(settings, httpx.MockTransport(handler))

    provider.submit_image(image_path, 10_000)
    provider.close()

    encoded = submitted_payload["image_base64"]
    assert len(encoded) <= 6 * 1024 * 1024
    with Image.open(BytesIO(base64.b64decode(encoded))) as resized:
        assert max(resized.size) <= 5_000
        assert min(resized.size) >= 128


def test_billable_submit_is_never_retried_after_provider_error(tmp_path):
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(500, json={"code": "temporary_error"})

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        model_name="tripo-3d-p1",
        model_timeout_seconds=5,
        model_max_retries=2,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubGenerationProvider(settings, httpx.MockTransport(handler))

    with pytest.raises(AppError) as raised:
        provider.submit_text("低多边形青铜宝箱", 10_000)
    provider.close()

    assert raised.value.code == "PROVIDER_UNAVAILABLE"
    assert call_count == 1


def test_tokenhub_3d_billing_error_is_actionable(tmp_path):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={"code": "401007", "request_id": "request-3d-1"},
        )

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        model_name="tripo-3d-p1",
        model_timeout_seconds=5,
        model_max_retries=2,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubGenerationProvider(settings, httpx.MockTransport(handler))

    with pytest.raises(AppError) as raised:
        provider.submit_text("低多边形青铜宝箱", 10_000)
    provider.close()

    assert raised.value.code == "MODEL_BILLING_NOT_ENABLED"
    assert raised.value.status_code == 402
    assert {"provider_code": "401007"} in raised.value.details
    assert {"request_id": "request-3d-1"} in raised.value.details


def test_failed_submit_preserves_provider_diagnostics(tmp_path):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "",
                "request_id": "request-rejected-1",
                "status": "failed",
                "error": {
                    "code": "InvalidParameter.InvalidParameter",
                    "message": "invalid input",
                },
            },
        )

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        model_name="tripo-3d-p1",
        model_timeout_seconds=5,
        model_max_retries=2,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubGenerationProvider(settings, httpx.MockTransport(handler))

    with pytest.raises(AppError) as raised:
        provider.submit_text("低多边形青铜宝箱", 10_000)
    provider.close()

    assert raised.value.code == "GENERATION_REQUEST_REJECTED"
    assert {"provider_code": "InvalidParameter.InvalidParameter"} in raised.value.details
    assert {"provider_message": "invalid input"} in raised.value.details
    assert {"request_id": "request-rejected-1"} in raised.value.details


def test_numeric_provider_task_id_is_normalized(tmp_path):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": 123456789, "status": "queued"})

    settings = Settings(
        model_api_base_url="https://tokenhub.tencentmaas.com",
        model_api_key="test-key",
        model_name="tripo-3d-p1",
        model_timeout_seconds=5,
        model_max_retries=0,
        asset_storage_root=tmp_path,
    )
    provider = TokenHubGenerationProvider(settings, httpx.MockTransport(handler))

    provider_task_id, _ = provider.submit_text("低多边形青铜宝箱", 10_000)
    provider.close()

    assert provider_task_id == "123456789"
