import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

def error_response(
    status_code: int,
    code: str,
    message: str,
    details=None,):
    error = {
        "code": code,
        "message": message,
    }

    if details is not None:
        error["details"] = details

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": error,
        },
    )


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ):
        return error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ):
        # Preserve an existing domain code when one is provided.
        if isinstance(exc.detail, dict):
            code = exc.detail.get("code")
            message = exc.detail.get("message", "Request failed")
        else:
            code = None
            message = str(exc.detail)

        if not code:
            default_codes = {
                400: "BAD_REQUEST",
                401: "UNAUTHORIZED",
                403: "FORBIDDEN",
                404: "NOT_FOUND",
                409: "CONFLICT",
                422: "VALIDATION_ERROR",
            }
            code = default_codes.get(
                exc.status_code,
                "HTTP_ERROR",
            )

        return error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        # Do not return rejected input values; they may contain
        # sensitive information.
        details = [
            {
                "field": ".".join(
                    str(part) for part in error["loc"]
                ),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]

        return error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="The request contains invalid data.",
            details=details,
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.exception(
            "Unhandled API error for %s %s",
            request.method,
            request.url.path,
        )

        return error_response(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
        )