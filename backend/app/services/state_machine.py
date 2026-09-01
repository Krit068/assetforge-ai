from app.core.errors import AppError
from app.db.models import TaskState


ALLOWED_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.DRAFT: {TaskState.VALIDATING, TaskState.CANCELLED},
    TaskState.VALIDATING: {TaskState.QUEUED, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.QUEUED: {TaskState.PREPROCESSING, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.PREPROCESSING: {TaskState.GEOMETRY, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.GEOMETRY: {TaskState.TEXTURING, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.TEXTURING: {TaskState.POST_PROCESSING, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.POST_PROCESSING: {TaskState.QA, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.QA: {
        TaskState.READY,
        TaskState.NEEDS_FIX,
        TaskState.CANCELLED,
        TaskState.FAILED,
    },
    TaskState.READY: set(),
    TaskState.NEEDS_FIX: set(),
    TaskState.FAILED: set(),
    TaskState.CANCELLED: set(),
}


def transition(current: str, target: TaskState) -> str:
    current_state = TaskState(current)
    if target not in ALLOWED_TRANSITIONS[current_state]:
        raise AppError(
            code="INVALID_STATE_TRANSITION",
            message=f"任务不能从 {current_state.value} 转换到 {target.value}",
            status_code=409,
        )
    return target.value

