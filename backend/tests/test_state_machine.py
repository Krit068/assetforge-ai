import pytest

from app.core.errors import AppError
from app.db.models import TaskState
from app.services.state_machine import transition


def test_valid_state_transition():
    assert transition(TaskState.DRAFT.value, TaskState.VALIDATING) == "VALIDATING"


def test_invalid_state_transition_is_rejected():
    with pytest.raises(AppError) as error:
        transition(TaskState.READY.value, TaskState.QUEUED)
    assert error.value.code == "INVALID_STATE_TRANSITION"

