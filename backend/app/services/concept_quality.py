from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageChops, ImageStat


def _normalized_image(contents: bytes) -> Image.Image:
    with Image.open(BytesIO(contents)) as image:
        return image.convert("RGB").resize((128, 128))


def assess_character_views(view_concepts: list[tuple[str, object]]) -> list[str]:
    """Reject obvious duplicate/invalid turntable inputs without another paid call."""
    warnings: list[str] = []
    if [view for view, _ in view_concepts] != ["front", "left", "back", "right"]:
        return ["人物建模需要正、左、后、右四张参考图"]

    dimensions = {(item.width, item.height) for _, item in view_concepts}
    if len(dimensions) != 1:
        warnings.append("四视图尺寸不一致")

    front = _normalized_image(view_concepts[0][1].contents)
    labels = {"left": "左侧", "back": "背面", "right": "右侧"}
    for view, concept in view_concepts[1:]:
        candidate = _normalized_image(concept.contents)
        difference = ImageStat.Stat(ImageChops.difference(front, candidate)).mean
        mean_difference = sum(difference) / len(difference)
        if mean_difference < 9.0:
            warnings.append(f"{labels[view]}图与正面图过于相似，可能不是有效的{labels[view]}视图")
    return warnings
