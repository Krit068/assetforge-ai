from io import BytesIO
from uuid import uuid4

from PIL import Image

from app.core.config import Settings
from app.schemas.tasks import GenerationTaskCreate


def create_project(client):
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "青铜遗迹",
            "engine": "unity",
            "platform": "mobile",
            "locale": "zh-CN",
            "spec_profile": {"template": "unity_urp_mobile"},
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_generation_task_defaults_to_high_poly_source():
    payload = GenerationTaskCreate(project_id="project-alpha", prompt="科幻医疗无人机")
    assert payload.quality_tier == "high"


def test_mock_generation_flow_is_persisted_and_idempotent(client):
    project = create_project(client)
    request = {
        "project_id": project["id"],
        "asset_type": "prop",
        "prompt": "低多边形青铜宝箱，氧化青铜材质，兽首锁扣",
        "candidate_count": 4,
        "quality_tier": "standard",
    }
    key = f"test-{uuid4()}"

    created = client.post(
        "/api/v1/generation-tasks",
        headers={"Idempotency-Key": key},
        json=request,
    )
    assert created.status_code == 202
    task_id = created.json()["data"]["id"]

    completed = client.get(f"/api/v1/generation-tasks/{task_id}")
    assert completed.status_code == 200
    assert completed.json()["data"]["state"] == "READY"
    assert len(completed.json()["data"]["candidates"]) == 4

    duplicate = client.post(
        "/api/v1/generation-tasks",
        headers={"Idempotency-Key": key},
        json=request,
    )
    assert duplicate.status_code == 202
    assert duplicate.json()["data"]["id"] == task_id

    task_list = client.get("/api/v1/generation-tasks?limit=20")
    assert task_list.status_code == 200
    assert task_list.json()["data"][0]["id"] == task_id


def test_ready_candidate_glb_can_be_downloaded_without_provider_call(
    client, monkeypatch, tmp_path
):
    from app.api.routes import tasks as task_routes
    from app.db.database import SessionLocal
    from app.db.models import TaskCandidate

    project = create_project(client)
    created = client.post(
        "/api/v1/generation-tasks",
        headers={"Idempotency-Key": "download-ready-candidate"},
        json={
            "project_id": project["id"],
            "asset_type": "prop",
            "prompt": "低多边形青铜宝箱，氧化青铜材质，兽首锁扣",
            "candidate_count": 2,
        },
    )
    assert created.status_code == 202
    task = client.get(
        f"/api/v1/generation-tasks/{created.json()['data']['id']}"
    ).json()["data"]

    model_path = tmp_path / "generated" / task["id"] / "candidate-1.glb"
    model_path.parent.mkdir(parents=True)
    model_contents = b"glTF-test-candidate"
    model_path.write_bytes(model_contents)

    with SessionLocal() as db:
        candidate = db.get(TaskCandidate, task["candidates"][0]["id"])
        candidate.model_url = (
            f"http://localhost:8010/assets/generated/{task['id']}/candidate-1.glb"
        )
        db.commit()

    monkeypatch.setattr(
        task_routes,
        "get_settings",
        lambda: Settings(asset_storage_root=tmp_path),
    )

    downloaded = client.get(
        f"/api/v1/generation-tasks/{task['id']}/candidates/1/download"
    )
    assert downloaded.status_code == 200
    assert downloaded.content == model_contents
    assert downloaded.headers["content-type"] == "model/gltf-binary"
    assert "attachment" in downloaded.headers["content-disposition"]
    assert "candidate-1.glb" in downloaded.headers["content-disposition"]
    assert downloaded.headers["cache-control"] == "private, no-store"

    unavailable = client.get(
        f"/api/v1/generation-tasks/{task['id']}/candidates/2/download"
    )
    assert unavailable.status_code == 404
    assert unavailable.json()["error"]["code"] == "MODEL_FILE_UNAVAILABLE"


def test_generation_requires_prompt_or_reference(client):
    project = create_project(client)
    response = client.post(
        "/api/v1/generation-tasks",
        headers={"Idempotency-Key": "missing-input"},
        json={"project_id": project["id"], "prompt": ""},
    )
    assert response.status_code == 422


def test_generation_rejects_ambiguous_prompt_before_queueing(client):
    project = create_project(client)
    response = client.post(
        "/api/v1/generation-tasks",
        headers={"Idempotency-Key": "ambiguous-prompt"},
        json={"project_id": project["id"], "prompt": "做一个东西"},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "PROMPT_NEEDS_CLARIFICATION"
    assert len(error["details"]) == 1
    assert error["details"][0]["id"] == "subject"
    assert len(error["details"][0]["options"]) == 4


def test_capabilities_hide_commercial_features(client):
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    assert response.json()["data"]["commercial_features"] is False
    assert response.json()["data"]["locales"] == ["zh-CN", "en"]
    assert response.json()["data"]["asset_types"] == ["prop", "character"]
    profiles = response.json()["data"]["quality_profiles"]
    assert profiles[0] == {
        "id": "high",
        "label": "high_poly_source",
        "face_limit": 100_000,
        "default": True,
    }
    assert profiles[1]["face_limit"] == 20_000


def test_seedream_concept_route_is_independent_from_tripo_3d_provider(
    client, monkeypatch, tmp_path
):
    from app.api.routes import concepts as concept_routes
    from app.services.concept_image import GeneratedConcept

    image_buffer = BytesIO()
    Image.new("RGB", (1024, 1024), (82, 93, 104)).save(image_buffer, format="PNG")

    class FakeConceptProvider:
        model_name = "seedream-image-v5.0-pro"

        def __init__(self, _settings):
            pass

        def generate(self, prompt, asset_type, **_kwargs):
            assert prompt == "低多边形青铜宝箱"
            assert asset_type == "prop"
            return GeneratedConcept(
                contents=image_buffer.getvalue(),
                mime_type="image/png",
                suffix=".png",
                width=1024,
                height=1024,
                usage_tokens=30_000,
            )

        def close(self):
            pass

    settings = Settings(
        model_provider="tripo_official",
        model_api_base_url="https://tokenhub.example.com",
        model_api_key="test-tokenhub-key",
        asset_storage_root=tmp_path,
    )
    monkeypatch.setattr(concept_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(concept_routes, "TokenHubConceptImageProvider", FakeConceptProvider)

    response = client.post(
        "/api/v1/concept-images",
        json={
            "prompt": "低多边形青铜宝箱",
            "asset_type": "prop",
            "locale": "zh-CN",
        },
    )

    assert response.status_code == 201
    concept = response.json()["data"]
    assert concept["model"] == "seedream-image-v5.0-pro"
    assert concept["reference_file"]["mime_type"] == "image/png"


def test_character_concept_route_persists_four_views_and_separate_accessory(
    client, monkeypatch, tmp_path
):
    from app.api.routes import concepts as concept_routes
    from app.services.concept_image import GeneratedConcept

    image_buffer = BytesIO()
    Image.new("RGB", (1024, 1024), (90, 70, 110)).save(image_buffer, format="PNG")
    calls: list[dict] = []

    class FakeConceptProvider:
        model_name = "seedream-image-v5.0-pro"

        def __init__(self, _settings):
            pass

        def generate(self, _prompt, _asset_type, **kwargs):
            calls.append(kwargs)
            return GeneratedConcept(
                contents=image_buffer.getvalue(),
                mime_type="image/png",
                suffix=".png",
                width=1024,
                height=1024,
                usage_tokens=30_000,
            )

        def close(self):
            pass

    settings = Settings(
        model_provider="tripo_official",
        model_api_base_url="https://tokenhub.example.com",
        model_api_key="test-tokenhub-key",
        asset_storage_root=tmp_path,
    )
    monkeypatch.setattr(concept_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(concept_routes, "TokenHubConceptImageProvider", FakeConceptProvider)

    response = client.post(
        "/api/v1/concept-images",
        json={
            "prompt": "仙侠剑修少女，佩剑",
            "asset_type": "character",
            "locale": "zh-CN",
        },
    )

    assert response.status_code == 201
    concept = response.json()["data"]
    assert [item["view"] for item in concept["views"]] == ["front", "left", "back", "right"]
    assert concept["accessories"][0]["name"] == "长剑"
    assert concept["estimated_cost_cny"] == 1.5
    assert concept["usage_tokens"] == 150_000
    assert len(calls) == 5
    assert calls[1]["reference_images"]
    assert calls[-1]["accessory_name"] == "长剑"


def test_tripo_requires_reference_then_routes_image_without_starting_real_provider(
    client, monkeypatch, tmp_path
):
    from app.api.routes import files as file_routes
    from app.api.routes import tasks as task_routes

    project = create_project(client)
    settings = Settings(
        model_provider="tripo_official",
        tripo_model_version="P1-20260311",
        asset_storage_root=tmp_path,
    )
    monkeypatch.setattr(
        task_routes,
        "get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(file_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(task_routes, "process_tripo_task", lambda *_: None)

    text_only = client.post(
        "/api/v1/generation-tasks",
        headers={"Idempotency-Key": "tripo-text-route-test"},
        json={
            "project_id": project["id"],
            "asset_type": "prop",
            "prompt": "低多边形青铜宝箱，氧化青铜材质，兽首锁扣",
            "candidate_count": 1,
        },
    )
    assert text_only.status_code == 422
    assert text_only.json()["error"]["code"] == "CONCEPT_IMAGE_REQUIRED"

    image_buffer = BytesIO()
    Image.new("RGB", (512, 512), (63, 74, 85)).save(image_buffer, format="PNG")
    uploaded = client.post(
        "/api/v1/files/reference-images",
        files={"file": ("concept.png", image_buffer.getvalue(), "image/png")},
    )
    assert uploaded.status_code == 201
    reference_file_id = uploaded.json()["data"]["id"]

    response = client.post(
        "/api/v1/generation-tasks",
        headers={"Idempotency-Key": "tripo-image-route-test"},
        json={
            "project_id": project["id"],
            "asset_type": "prop",
            "prompt": "低多边形青铜宝箱，氧化青铜材质，兽首锁扣",
            "reference_file_id": reference_file_id,
            "candidate_count": 1,
        },
    )

    assert response.status_code == 202
    task = response.json()["data"]
    assert task["provider"] == "tripo_official"
    assert task["model_version"] == "P1-20260311"
    assert task["state"] == "QUEUED"
    assert task["input_mode"] == "image"


def test_tripo_idempotency_schedules_only_one_paid_provider_task(
    client, monkeypatch, tmp_path
):
    from app.api.routes import files as file_routes
    from app.api.routes import tasks as task_routes

    project = create_project(client)
    settings = Settings(
        model_provider="tripo_official",
        tripo_model_version="P1-20260311",
        asset_storage_root=tmp_path,
    )
    monkeypatch.setattr(task_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(file_routes, "get_settings", lambda: settings)
    scheduled: list[str] = []
    monkeypatch.setattr(
        task_routes,
        "process_tripo_task",
        lambda task_id, _session_factory: scheduled.append(task_id),
    )

    image_buffer = BytesIO()
    Image.new("RGB", (512, 512), (32, 64, 96)).save(image_buffer, format="PNG")
    uploaded = client.post(
        "/api/v1/files/reference-images",
        files={"file": ("concept.png", image_buffer.getvalue(), "image/png")},
    )
    reference_file_id = uploaded.json()["data"]["id"]
    request = {
        "project_id": project["id"],
        "asset_type": "prop",
        "prompt": "低多边形青铜宝箱，氧化青铜材质，兽首锁扣",
        "reference_file_id": reference_file_id,
        "candidate_count": 1,
    }
    headers = {"Idempotency-Key": "same-paid-request-retry"}

    first = client.post("/api/v1/generation-tasks", headers=headers, json=request)
    retry = client.post("/api/v1/generation-tasks", headers=headers, json=request)

    assert first.status_code == 202
    assert retry.status_code == 202
    assert retry.json()["data"]["id"] == first.json()["data"]["id"]
    assert scheduled == [first.json()["data"]["id"]]


def test_task_persists_separate_accessory_references(client, monkeypatch, tmp_path):
    from app.api.routes import files as file_routes
    from app.api.routes import tasks as task_routes

    project = create_project(client)
    settings = Settings(
        model_provider="tripo_official",
        tripo_model_version="P1-20260311",
        asset_storage_root=tmp_path,
    )
    monkeypatch.setattr(task_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(file_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(task_routes, "process_tripo_task", lambda *_: None)

    def upload(name: str, color: tuple[int, int, int]) -> str:
        image_buffer = BytesIO()
        Image.new("RGB", (512, 512), color).save(image_buffer, format="PNG")
        response = client.post(
            "/api/v1/files/reference-images",
            files={"file": (name, image_buffer.getvalue(), "image/png")},
        )
        return response.json()["data"]["id"]

    body_id = upload("character.png", (10, 20, 30))
    sword_id = upload("sword.png", (80, 90, 100))
    response = client.post(
        "/api/v1/generation-tasks",
        headers={"Idempotency-Key": "separate-accessory-test"},
        json={
            "project_id": project["id"],
            "asset_type": "character",
            "prompt": "写实仙侠少女，华贵服装，标准A姿势",
            "reference_file_ids": [body_id],
            "accessory_references": [{"name": "长剑", "file_id": sword_id}],
            "candidate_count": 1,
        },
    )
    assert response.status_code == 202
    task = response.json()["data"]
    assert task["accessory_references"] == [{"name": "长剑", "file_id": sword_id}]
    assert task["accessory_reference_files"][0]["reference_file"]["id"] == sword_id
