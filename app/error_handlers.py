import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.services.users import (
    ApiAccessAlreadyEnabled,
    ApiAccessNotEnabled,
    ApiAccessProhibited,
    EmailAlreadyExists,
    InvalidCredentials,
    InvalidResetCode,
    LifecycleOperationProhibited,
    UserNotFound,
    UserServiceError,
)


async def user_service_error_handler(
    request: Request,
    error: UserServiceError,
) -> JSONResponse:
    if isinstance(error, UserNotFound):
        return JSONResponse({"detail": "User not found"}, status.HTTP_404_NOT_FOUND)
    if isinstance(error, EmailAlreadyExists):
        return JSONResponse({"detail": "Email already exists"}, status.HTTP_409_CONFLICT)
    if isinstance(error, InvalidCredentials):
        return JSONResponse(
            {"detail": "Invalid credentials"},
            status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if isinstance(error, InvalidResetCode):
        return JSONResponse(
            {"detail": "The reset code is invalid or expired"},
            status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(
        error,
        (
            ApiAccessAlreadyEnabled,
            ApiAccessNotEnabled,
            ApiAccessProhibited,
            LifecycleOperationProhibited,
        ),
    ):
        return JSONResponse(
            {"detail": "The requested lifecycle operation is prohibited"},
            status.HTTP_400_BAD_REQUEST,
        )
    logging.error("Unmapped user service error: %s", type(error).__name__)
    return JSONResponse(
        {"detail": "Internal server error"},
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
