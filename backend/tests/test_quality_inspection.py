import json
import struct
from io import BytesIO

from PIL import Image

from app.services.concept_image import GeneratedConcept, TokenHubConceptImageProvider
from app.services.concept_quality import assess_character_views
from app.services.glb_inspector import inspect_glb


def concept(color: tuple[int, int, int]) -> GeneratedConcept:
    output = BytesIO()
    Image.new("RGB", (256, 256), color).save(output, format="PNG")
    return GeneratedConcept(output.getvalue(), "image/png", ".png", 256, 256, None)


def test_multiview_gate_rejects_duplicate_side_view():
    views = [
        ("front", concept((20, 30, 40))),
        ("left", concept((20, 30, 40))),
        ("back", concept((180, 30, 40))),
        ("right", concept((20, 180, 40))),
    ]
    warnings = assess_character_views(views)
    assert any("左侧图与正面图过于相似" in item for item in warnings)


def test_character_prompt_keeps_constraints_before_user_text():
    provider = object.__new__(TokenHubConceptImageProvider)
    prompt = provider._provider_prompt(
        "仙侠剑修少女，手持长剑，轻微动态展示姿势，华贵仙子外观" * 20,
        "character",
        view="back",
        excluded_accessories=("长剑",),
    )
    assert len(prompt) <= 600
    assert "BACK orthographic" in prompt
    assert "NO weapons" in prompt
    assert "standard symmetric A-pose" in prompt
    assert "长剑" not in prompt.split(" DESIGN: ", 1)[1]
    assert "动态展示姿势" not in prompt


def test_glb_inspector_reports_actual_triangles(tmp_path):
    document = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": 0}],
        "accessors": [{"count": 6}, {"count": 4}],
        "meshes": [{"primitives": [{"indices": 0, "attributes": {"POSITION": 1}}]}],
        "materials": [{}],
    }
    json_chunk = json.dumps(document).encode()
    json_chunk += b" " * ((4 - len(json_chunk) % 4) % 4)
    total = 12 + 8 + len(json_chunk)
    glb = struct.pack("<4sII", b"glTF", 2, total)
    glb += struct.pack("<II", len(json_chunk), 0x4E4F534A) + json_chunk
    path = tmp_path / "model.glb"
    path.write_bytes(glb)

    metrics = inspect_glb(path)
    assert metrics["triangle_count"] == 2
    assert metrics["vertex_count"] == 4
    assert metrics["material_count"] == 1
