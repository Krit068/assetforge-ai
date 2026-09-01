from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.files import ReferenceFileResponse


class ConceptImageCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=2_000)
    asset_type: Literal["prop", "character"] = "prop"
    locale: Literal["zh-CN", "en"] = "zh-CN"


class ConceptReferenceView(BaseModel):
    view: Literal["front", "left", "back", "right"]
    reference_file: ReferenceFileResponse


class ConceptAccessory(BaseModel):
    name: str
    reference_file: ReferenceFileResponse


class ConceptImageResponse(BaseModel):
    id: str
    reference_file: ReferenceFileResponse
    views: list[ConceptReferenceView] = Field(default_factory=list)
    accessories: list[ConceptAccessory] = Field(default_factory=list)
    model: str
    usage_tokens: int | None = None
    estimated_cost_cny: float
    ready_for_3d: bool = True
    quality_warnings: list[str] = Field(default_factory=list)
