from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SpecProfile(BaseModel):
    template: Literal[
        "unity_urp_mobile",
        "unity_pc",
        "unreal_pc",
        "generic_low_poly",
    ] = "unity_urp_mobile"
    unit: Literal["meter", "centimeter"] = "meter"
    up_axis: Literal["Y", "Z"] = "Y"
    forward_axis: Literal["Z", "-Z", "X", "-X"] = "Z"
    triangle_budget: int = Field(default=10_000, ge=100, le=1_000_000)
    texture_resolution: Literal[512, 1024, 2048, 4096] = 2048
    pbr_channels: list[str] = [
        "base_color",
        "normal",
        "roughness",
        "metallic",
        "ao",
    ]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    engine: Literal["unity", "unreal", "godot", "roblox"] = "unity"
    platform: Literal["mobile", "pc", "generic_low_poly"] = "mobile"
    locale: Literal["zh-CN", "en"] = "zh-CN"
    spec_profile: SpecProfile = SpecProfile()


class ProjectResponse(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str

