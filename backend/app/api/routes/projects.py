from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.database import get_db
from app.db.models import Project
from app.schemas.projects import ProjectCreate, ProjectResponse


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> dict:
    project = Project(**payload.model_dump(mode="json"))
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"data": ProjectResponse.model_validate(project)}


@router.get("")
def list_projects(db: Session = Depends(get_db)) -> dict:
    projects = db.scalars(select(Project).order_by(Project.created_at.desc())).all()
    return {"data": [ProjectResponse.model_validate(project) for project in projects]}


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)) -> dict:
    project = db.get(Project, project_id)
    if project is None:
        raise AppError("PROJECT_NOT_FOUND", "项目不存在", 404)
    return {"data": ProjectResponse.model_validate(project)}

