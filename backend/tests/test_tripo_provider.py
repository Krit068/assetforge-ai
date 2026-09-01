import json

import httpx
import pytest
from PIL import Image

from app.core.config import Settings
from app.core.errors import AppError
from app.services.tripo_generation import TripoGenerationProvider


def tripo_settings(tmp_path, **overrides) -> Settings:
    values = {
        "tripo_api_base_url": "https://api.tripo3d.ai/v2/openapi",
        "tripo_api_key": "tsk_test-key",
        "tripo_model_version": "P1-20260311",
        "model_timeout_seconds": 5,
        "model_max_retries": 0,
        "asset_storage_root": tmp_path,
    }
    values.update(overrides)
    return Settings(**values)


def test_tripo_text_submit_query_and_download_without_forwarding_key(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v2/openapi/task":
            assert request.headers["Authorization"] == "Bearer tsk_test-key"
            assert request.headers["Content-Type"] == "application/json"
            payload = json.loads(request.content)
            assert payload == {
                "type": "text_to_model",
                "model_version": "P1-20260311",
                "prompt": "低多边形青铜宝箱",
                "face_limit": 10_000,
                "texture": True,
                "pbr": True,
                "texture_quality": "detailed",
                "auto_size": True,
            }
            return httpx.Response(
                200,
                json={"code": 0, "data": {"task_id": "tripo-task-1"}},
                headers={"X-Tripo-Trace-ID": "trace-create-1"},
            )
        if request.method == "GET" and request.url.path == "/v2/openapi/task/tripo-task-1":
            assert request.headers["Authorization"] == "Bearer tsk_test-key"
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "task_id": "tripo-task-1",
                        "status": "success",
                        "output": {
                            "pbr_model": "https://assets.tripo3d.ai/model.glb",
                            "rendered_image": "https://assets.tripo3d.ai/preview.png",
                        },
                    },
                },
            )
        if request.url.host == "assets.tripo3d.ai":
            assert "Authorization" not in request.headers
            return httpx.Response(200, content=b"glTF-tripo-test")
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = TripoGenerationProvider(
        tripo_settings(tmp_path),
        httpx.MockTransport(handler),
    )

    provider_task_id, model_name = provider.submit_text("低多边形青铜宝箱", 10_000)
    result = provider.wait_for_result(provider_task_id, model_name)
    destination = tmp_path / "generated" / "candidate.glb"
    provider.download(result.model_url, destination, 1024)
    provider.close()

    assert model_name == "P1-20260311"
    assert result.preview_url == "https://assets.tripo3d.ai/preview.png"
    assert destination.read_bytes() == b"glTF-tripo-test"


def test_tripo_image_upload_uses_file_token_instead_of_base64(tmp_path):
    image_path = tmp_path / "reference.jpg"
    Image.new("RGB", (512, 512), "green").save(image_path)
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/v2/openapi/upload/sts":
            assert request.headers["Authorization"] == "Bearer tsk_test-key"
            assert request.headers["Content-Type"].startswith("multipart/form-data;")
            assert b"reference.jpg" in request.content
            assert image_path.read_bytes() in request.content
            return httpx.Response(
                200,
                json={"code": 0, "data": {"image_token": "uploaded-image-1"}},
            )
        if request.url.path == "/v2/openapi/task":
            payload = json.loads(request.content)
            assert payload == {
                "type": "image_to_model",
                "model_version": "P1-20260311",
                "file": {"type": "jpg", "file_token": "uploaded-image-1"},
                "face_limit": 5_000,
                "texture": True,
                "pbr": True,
                "texture_quality": "detailed",
                "auto_size": True,
                "render_image": True,
            }
            assert "image_base64" not in payload
            return httpx.Response(
                200,
                json={"code": 0, "data": {"task_id": "tripo-image-task-1"}},
            )
        raise AssertionError(f"unexpected request: {request.url}")

    provider = TripoGenerationProvider(
        tripo_settings(tmp_path),
        httpx.MockTransport(handler),
    )

    provider_task_id, model_name = provider.submit_image(image_path, 5_000)
    provider.close()

    assert provider_task_id == "tripo-image-task-1"
    assert model_name == "P1-20260311"
    assert calls == ["/v2/openapi/upload/sts", "/v2/openapi/task"]


def test_character_four_views_keep_two_million_face_v31_ultra_source(tmp_path):
    paths = []
    for index in range(4):
        path = tmp_path / f"view-{index}.png"
        Image.new("RGB", (512, 512), (30 + index, 40, 50)).save(path)
        paths.append(path)
    uploads = 0
    submitted: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal uploads
        if request.method == "POST" and request.url.path == "/v2/openapi/upload/sts":
            uploads += 1
            return httpx.Response(
                200,
                json={"code": 0, "data": {"image_token": f"view-token-{uploads}"}},
            )
        if request.method == "POST" and request.url.path == "/v2/openapi/task":
            payload = json.loads(request.content)
            submitted.append(payload)
            return httpx.Response(200, json={"code": 0, "data": {"task_id": "detailed-model"}})
        if request.method == "GET" and request.url.path.endswith("/detailed-model"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "status": "success",
                        "consumed_credit": 120,
                        "output": {
                            "pbr_model": "https://assets.tripo3d.ai/high.glb",
                            "rendered_image": "https://assets.tripo3d.ai/high.png",
                        },
                    },
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    stages: list[tuple[str, str]] = []
    provider = TripoGenerationProvider(tripo_settings(tmp_path), httpx.MockTransport(handler))
    result = provider.generate_from_images(
        paths,
        20_000,
        asset_type="character",
        quality_tier="high",
        stage_callback=lambda stage, task_id: stages.append((stage, task_id)),
    )
    provider.close()

    assert len(submitted) == 1
    detailed = submitted[0]
    assert detailed["type"] == "multiview_to_model"
    assert detailed["model_version"] == "v3.1-20260211"
    assert detailed["geometry_quality"] == "detailed"
    assert detailed["texture_quality"] == "extreme"
    assert detailed["face_limit"] == 2_000_000
    assert [item["file_token"] for item in detailed["files"]] == [
        "view-token-1", "view-token-2", "view-token-3", "view-token-4"
    ]
    assert stages == [("detailed_model", "detailed-model")]
    assert result.model_url == "https://assets.tripo3d.ai/high.glb"
    assert result.preview_url == "https://assets.tripo3d.ai/high.png"
    assert result.consumed_credit == 120
    assert result.provider_task_ids == {"detailed_model": "detailed-model"}
    assert result.model_name == "v3.1-20260211"


def test_single_character_image_generates_multiview_before_p1_model(tmp_path):
    image_path = tmp_path / "character.png"
    Image.new("RGB", (512, 512), "purple").save(image_path)
    submitted: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/openapi/upload/sts":
            return httpx.Response(200, json={"code": 0, "data": {"image_token": "character-token"}})
        if request.method == "POST" and request.url.path == "/v2/openapi/task":
            payload = json.loads(request.content)
            submitted.append(payload)
            task_id = "multiview-image" if payload["type"] == "generate_multiview_image" else "p1-model"
            return httpx.Response(200, json={"code": 0, "data": {"task_id": task_id}})
        if request.method == "GET" and request.url.path.endswith("/multiview-image"):
            return httpx.Response(200, json={"code": 0, "data": {"status": "success", "output": {}}})
        if request.method == "GET" and request.url.path.endswith("/p1-model"):
            return httpx.Response(
                200,
                json={"code": 0, "data": {"status": "success", "output": {"pbr_model": "https://assets.tripo3d.ai/model.glb"}}},
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = TripoGenerationProvider(tripo_settings(tmp_path), httpx.MockTransport(handler))
    result = provider.generate_from_images(
        [image_path], 20_000, asset_type="character", quality_tier="standard"
    )
    provider.close()

    assert submitted[0]["type"] == "generate_multiview_image"
    assert submitted[1]["type"] == "multiview_to_model"
    assert submitted[1]["original_task_id"] == "multiview-image"
    assert submitted[1]["model_version"] == "P1-20260311"
    assert submitted[1]["face_limit"] == 20_000
    assert submitted[1]["texture_quality"] == "detailed"
    assert result.provider_task_ids == {
        "multiview_image": "multiview-image",
        "model": "p1-model",
    }


def test_tripo_billable_submit_is_never_retried(tmp_path):
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(500, json={"code": 5000, "message": "temporary"})

    provider = TripoGenerationProvider(
        tripo_settings(tmp_path, model_max_retries=2),
        httpx.MockTransport(handler),
    )

    with pytest.raises(AppError) as raised:
        provider.submit_text("低多边形青铜宝箱", 10_000)
    provider.close()

    assert raised.value.code == "PROVIDER_UNAVAILABLE"
    assert call_count == 1


def test_tripo_error_preserves_safe_provider_diagnostics(tmp_path):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "code": 2003,
                "message": "The input file is empty",
                "suggestion": "Check the uploaded file",
            },
            headers={"X-Tripo-Trace-ID": "trace-error-1"},
        )

    provider = TripoGenerationProvider(
        tripo_settings(tmp_path),
        httpx.MockTransport(handler),
    )

    with pytest.raises(AppError) as raised:
        provider.submit_text("低多边形青铜宝箱", 10_000)
    provider.close()

    assert raised.value.code == "GENERATION_REQUEST_REJECTED"
    assert {"provider_code": "2003"} in raised.value.details
    assert {"provider_message": "The input file is empty"} in raised.value.details
    assert {"provider_suggestion": "Check the uploaded file"} in raised.value.details
    assert {"trace_id": "trace-error-1"} in raised.value.details


def test_tripo_failed_task_preserves_task_diagnostics(tmp_path):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "task_id": "tripo-task-failed",
                    "status": "failed",
                    "output": {},
                    "error_code": 3001,
                    "error_msg": "generation failed",
                },
            },
        )

    provider = TripoGenerationProvider(
        tripo_settings(tmp_path),
        httpx.MockTransport(handler),
    )

    with pytest.raises(AppError) as raised:
        provider.wait_for_result("tripo-task-failed", "P1-20260311")
    provider.close()

    assert raised.value.code == "GENERATION_FAILED"
    assert {"provider_task_id": "tripo-task-failed"} in raised.value.details
    assert {"provider_status": "failed"} in raised.value.details
    assert {"provider_code": "3001"} in raised.value.details
    assert {"provider_message": "generation failed"} in raised.value.details


@pytest.mark.parametrize(
    "url",
    [
        "http://assets.tripo3d.ai/model.glb",
        "https://localhost/model.glb",
        "https://127.0.0.1/model.glb",
        "https://169.254.169.254/latest/meta-data",
    ],
)
def test_tripo_download_rejects_untrusted_urls(tmp_path, url):
    provider = TripoGenerationProvider(tripo_settings(tmp_path), httpx.MockTransport(lambda _: None))

    with pytest.raises(AppError) as raised:
        provider.download(url, tmp_path / "model.glb", 1024)
    provider.close()

    assert raised.value.code == "PROVIDER_FILE_URL_INVALID"
