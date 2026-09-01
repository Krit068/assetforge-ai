from fastapi import APIRouter

from app.schemas.prompts import PromptAnalysisRequest
from app.services.prompt_clarity import analyze_prompt


router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("/analyze")
def analyze(payload: PromptAnalysisRequest) -> dict:
    return {
        "data": analyze_prompt(
            payload.prompt,
            payload.locale,
            payload.asset_type,
            payload.has_reference_image,
        )
    }
