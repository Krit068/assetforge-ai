from contextlib import asynccontextmanager
import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.db.database import Base, engine
from app.db import models  # noqa: F401


settings = get_settings()
mimetypes.add_type("model/gltf-binary", ".glb")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.asset_storage_root.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AssetForge Alpha API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_exception_handler(AppError, app_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)
app.mount(
    "/assets",
    StaticFiles(directory=settings.asset_storage_root, check_dir=False),
    name="assets",
)
