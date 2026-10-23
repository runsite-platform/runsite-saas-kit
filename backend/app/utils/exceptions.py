from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class BusinessError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def not_found(entity: str = "Resource") -> BusinessError:
    return BusinessError("not_found", f"{entity} not found", status_code=404)


async def business_error_handler(request: Request, error: BusinessError) -> JSONResponse:
    error_body: dict[str, Any] = {"code": error.code, "message": error.message}
    if error.details is not None:
        error_body["details"] = error.details
    return JSONResponse(status_code=error.status_code, content={"error": error_body})


def forbidden(message: str = "You do not have permission to perform this action") -> BusinessError:
    return BusinessError("forbidden", message, status_code=403)
