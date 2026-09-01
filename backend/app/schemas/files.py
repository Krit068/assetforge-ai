from pydantic import BaseModel, ConfigDict


class ReferenceFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_name: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    preview_url: str
