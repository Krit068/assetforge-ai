from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"data": {"status": "ok"}}


@router.get("/capabilities")
def capabilities() -> dict:
    settings = get_settings()
    high_face_limit = 2_000_000 if settings.model_provider == "tripo_official" else 100_000
    return {
        "data": {
            "provider": settings.model_provider,
            "locales": settings.locales,
            "asset_types": ["prop", "character"],
            "experimental_asset_types": ["character"],
            "candidate_counts": [1, 2, 4],
            "templates": [
                "unity_urp_mobile",
                "unity_pc",
                "unreal_pc",
                "generic_low_poly",
            ],
            "formats": ["glb"],
            "quality_profiles": [
                {
                    "id": "high",
                    "label": "high_poly_source",
                    "face_limit": high_face_limit,
                    "default": True,
                },
                {
                    "id": "standard",
                    "label": "game_ready",
                    "face_limit": 20_000,
                    "default": False,
                },
            ],
            "commercial_features": False,
        }
    }
