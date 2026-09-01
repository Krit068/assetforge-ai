from __future__ import annotations

import json
import struct
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.core.errors import AppError


def inspect_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise AppError("MODEL_FILE_INVALID", "下载结果不是有效的 GLB 文件", 502)
    _magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if version != 2 or total_length != len(data):
        raise AppError("MODEL_FILE_INVALID", "GLB 文件头或长度无效", 502)

    offset = 12
    document: dict | None = None
    binary = b""
    while offset + 8 <= len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            document = json.loads(chunk.rstrip(b" \x00"))
        elif chunk_type == 0x004E4942:
            binary = chunk
    if document is None:
        raise AppError("MODEL_FILE_INVALID", "GLB 缺少 JSON 数据", 502)

    accessors = document.get("accessors", [])
    triangles = 0
    vertices = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                continue
            index_id = primitive.get("indices")
            position_id = (primitive.get("attributes") or {}).get("POSITION")
            count = accessors[index_id].get("count", 0) if isinstance(index_id, int) else (
                accessors[position_id].get("count", 0) if isinstance(position_id, int) else 0
            )
            triangles += int(count) // 3
            if isinstance(position_id, int):
                vertices += int(accessors[position_id].get("count", 0))

    resolutions: list[int] = []
    buffer_views = document.get("bufferViews", [])
    for image in document.get("images", []):
        view_id = image.get("bufferView")
        if not isinstance(view_id, int) or view_id >= len(buffer_views):
            continue
        view = buffer_views[view_id]
        start = int(view.get("byteOffset", 0))
        end = start + int(view.get("byteLength", 0))
        try:
            with Image.open(BytesIO(binary[start:end])) as texture:
                resolutions.append(max(texture.size))
        except Exception:
            continue

    return {
        "triangle_count": triangles,
        "vertex_count": vertices,
        "mesh_count": len(document.get("meshes", [])),
        "material_count": len(document.get("materials", [])),
        "texture_count": len(document.get("textures", [])),
        "texture_resolution": max(resolutions) if resolutions else None,
        "animation_count": len(document.get("animations", [])),
        "skin_count": len(document.get("skins", [])),
        "file_size_bytes": len(data),
    }
