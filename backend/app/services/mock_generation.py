from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateState, GenerationTask, TaskCandidate, TaskState
from app.services.state_machine import transition


def process_mock_task(task_id: str, session_factory) -> None:
    with session_factory() as db:
        task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id))
        if task is None or task.state == TaskState.CANCELLED.value:
            return

        for state in (
            TaskState.PREPROCESSING,
            TaskState.GEOMETRY,
            TaskState.TEXTURING,
            TaskState.POST_PROCESSING,
            TaskState.QA,
        ):
            task.state = transition(task.state, state)
            db.commit()

        for position in range(1, task.candidate_count + 1):
            task.candidates.append(
                TaskCandidate(
                    position=position,
                    state=CandidateState.READY.value,
                    model_url=f"/mock-assets/candidate-{position}.glb",
                    preview_url=f"/mock-assets/candidate-{position}.png",
                    metrics={
                        "triangle_count": 7_600 + position * 410,
                        "material_count": 2,
                        "texture_resolution": 2048,
                        "qa_score": 88 + position,
                    },
                )
            )

        task.state = transition(task.state, TaskState.READY)
        task.finished_at = datetime.now(timezone.utc)
        db.commit()

