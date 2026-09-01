from io import BytesIO

from PIL import Image

from app.core.config import get_settings


def make_png(width: int = 256, height: int = 256) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), (40, 210, 70)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_reference_image_upload_preview_and_delete(client, tmp_path):
    settings = get_settings()
    previous_root = settings.asset_storage_root
    settings.asset_storage_root = tmp_path
    try:
        uploaded = client.post(
            "/api/v1/files/reference-images",
            files={"file": ("character.png", make_png(), "image/png")},
        )
        assert uploaded.status_code == 201
        reference = uploaded.json()["data"]
        assert reference["original_name"] == "character.png"
        assert reference["mime_type"] == "image/png"
        assert reference["width"] == 256
        assert reference["height"] == 256
        assert reference["preview_url"].endswith(f"/assets/uploads/{reference['id']}.png")
        assert (tmp_path / "uploads" / f"{reference['id']}.png").exists()

        deleted = client.delete(f"/api/v1/files/reference-images/{reference['id']}")
        assert deleted.status_code == 200
        assert deleted.json()["data"]["deleted"] is True
        assert not (tmp_path / "uploads" / f"{reference['id']}.png").exists()
    finally:
        settings.asset_storage_root = previous_root


def test_reference_image_rejects_fake_image(client):
    response = client.post(
        "/api/v1/files/reference-images",
        files={"file": ("fake.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REFERENCE_IMAGE_INVALID"
