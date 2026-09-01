from typing import Literal

from pydantic import BaseModel, Field


class PromptAnalysisRequest(BaseModel):
    prompt: str = Field(default="", max_length=2_000)
    locale: Literal["zh-CN", "en"] = "zh-CN"
    asset_type: Literal["auto", "prop", "character"] = "auto"
    has_reference_image: bool = False


class ClarificationOption(BaseModel):
    value: str
    label: str
    description: str


class ClarificationQuestion(BaseModel):
    id: Literal["subject", "style", "material", "features", "appearance", "pose"]
    question: str
    answer_hint: str
    options: list[ClarificationOption]
    required: bool = True


class PromptAnalysisResponse(BaseModel):
    ready_to_generate: bool
    clarity_score: int = Field(ge=0, le=100)
    detected_asset_type: Literal["prop", "character"]
    clarifying_questions: list[ClarificationQuestion]
    detected_accessories: list[str] = Field(default_factory=list)
    concept_image_count: int = Field(default=1, ge=1, le=7)
