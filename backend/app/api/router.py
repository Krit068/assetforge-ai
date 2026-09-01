from fastapi import APIRouter

from app.api.routes import concepts, files, health, projects, prompts, tasks


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(concepts.router)
api_router.include_router(files.router)
api_router.include_router(projects.router)
api_router.include_router(prompts.router)
api_router.include_router(tasks.router)
