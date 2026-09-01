from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: list[dict] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        self.diagnostic_id = f"diag_{uuid4().hex[:12]}"
        super().__init__(message)


def error_payload(error: AppError) -> dict:
    return {
        "error": {
            "code": error.code,
            "message": error.message,
            "diagnostic_id": error.diagnostic_id,
            "details": error.details,
        }
    }


async def app_error_handler(_: Request, error: AppError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content=error_payload(error))
