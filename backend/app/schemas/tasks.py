from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.files import ReferenceFileResponse


class AccessoryReference(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    file_id: str


class GenerationTaskCreate(BaseModel):
    project_id: str
    asset_type: Literal["prop", "character"] = "prop"
    prompt: str = Field(default="", max_length=2_000)
    reference_file_id: str | None = None
    reference_file_ids: list[str] = Field(default_factory=list, max_length=4)
    concept_bundle_id: str | None = None
    accessory_references: list[AccessoryReference] = Field(default_factory=list, max_length=8)
    candidate_count: Literal[1, 2, 4] = 4
    quality_tier: Literal["draft", "standard", "high"] = "high"

    @model_validator(mode="after")
    def validate_input(self) -> "GenerationTaskCreate":
        if not self.prompt.strip() and not self.reference_file_id and not self.reference_file_ids:
            raise ValueError("prompt 和参考图至少提供一个")
        if self.reference_file_id and self.reference_file_ids:
            if self.reference_file_id != self.reference_file_ids[0]:
                raise ValueError("reference_file_id 必须与 reference_file_ids 的首项一致")
        if len(set(self.reference_file_ids)) != len(self.reference_file_ids):
            raise ValueError("reference_file_ids 不能包含重复项")
        return self


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    position: int
    asset_role: str = "main"
    asset_name: str | None = None
    state: str
    model_url: str | None
    preview_url: str | None
    metrics: dict
    error_code: str | None


class GenerationTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    state: str
    input_mode: str
    original_prompt: str
    reference_file_ids: list[str] = Field(default_factory=list)
    concept_bundle_id: str | None = None
    accessory_references: list[dict] = Field(default_factory=list)
    reference_files: list[ReferenceFileResponse] = Field(default_factory=list)
    accessory_reference_files: list[dict] = Field(default_factory=list)
    asset_type: str
    candidate_count: int
    quality_tier: str
    provider: str
    model_version: str
    attempt: int
    diagnostic_id: str
    error_code: str | None
    error_message: str | None
    candidates: list[CandidateResponse] = Field(default_factory=list)
