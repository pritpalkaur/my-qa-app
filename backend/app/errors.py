import logging

import pyodbc
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("pain_api")

_LOCATION_PREFIXES = {"body", "query", "path", "header"}

_HTTP_CODES = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    415: "UNSUPPORTED_MEDIA_TYPE",
}


class AppError(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


def error_response(status_code: int, code: str, message: str, details: list[dict] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {"code": code, "message": message, "details": details or []},
        },
    )


def _validation_details(exc: RequestValidationError) -> list[dict]:
    details = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", ())]
        if loc and loc[0] in _LOCATION_PREFIXES:
            loc = loc[1:]
        message = err.get("msg", "Invalid value").removeprefix("Value error, ")
        details.append({"field": ".".join(loc) or None, "message": message})
    return details


async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


async def _validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VALIDATION_ERROR",
        "Request validation failed",
        _validation_details(exc),
    )


async def _http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
    return error_response(exc.status_code, code, str(exc.detail))


async def _db_unavailable_handler(_: Request, exc: pyodbc.Error) -> JSONResponse:
    logger.error("Database connection failed: %s", exc)
    return error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "DATABASE_UNAVAILABLE",
        "The database is unavailable. Check that SQL Server is running and the .env credentials are correct.",
    )


async def _db_error_handler(_: Request, exc: pyodbc.Error) -> JSONResponse:
    logger.exception("Database error", exc_info=exc)
    return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "DATABASE_ERROR", "A database error occurred.")


async def _unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "An unexpected error occurred.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    # Login failures surface as InterfaceError, timeouts / unreachable server as OperationalError.
    app.add_exception_handler(pyodbc.InterfaceError, _db_unavailable_handler)
    app.add_exception_handler(pyodbc.OperationalError, _db_unavailable_handler)
    app.add_exception_handler(pyodbc.Error, _db_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
