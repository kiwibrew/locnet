from pathlib import Path

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr

from app.config import settings
from app.dependencies import (
    CurrentAdminUser,
    CurrentSessionUser,
    UserServiceDependency,
)
from app.security import new_csrf_token, set_csrf_cookie, verify_csrf_token
from app.services.users import (
    ApiAccessAlreadyEnabled,
    ApiAccessNotEnabled,
    ApiAccessProhibited,
    EmailAlreadyExists,
    LifecycleOperationProhibited,
    UserNotFound,
)


router = APIRouter()
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parents[1] / "templates"
)


async def _management_response(
    request: Request,
    current_user,
    service,
    *,
    error: str | None = None,
) -> HTMLResponse:
    csrf_token = request.cookies.get(settings.csrf_cookie_name) or new_csrf_token()
    response = templates.TemplateResponse(
        request=request,
        name="manage_users.html",
        context={
            "current_user": current_user,
            "users": await service.visible_users(current_user),
            "csrf_token": csrf_token,
            "error": error,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.get("/manage-users", response_class=HTMLResponse, include_in_schema=False)
async def manage_users(
    request: Request,
    current_user: CurrentSessionUser,
    service: UserServiceDependency,
):
    if current_user is None:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return await _management_response(request, current_user, service)


@router.post("/users/create", include_in_schema=False)
async def create_user(
    request: Request,
    current_admin: CurrentAdminUser,
    service: UserServiceDependency,
    email: EmailStr = Form(),
    password: str = Form(min_length=8, max_length=128),
    is_admin: bool = Form(False),
    csrf_token: str = Form(),
):
    verify_csrf_token(request, csrf_token)
    try:
        await service.create_user(str(email), password, is_admin=is_admin)
    except EmailAlreadyExists:
        return await _management_response(
            request,
            current_admin,
            service,
            error="A user with that email already exists.",
        )
    return RedirectResponse("/manage-users", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/users/{user_id}/enable-api", include_in_schema=False)
async def enable_api_access(
    user_id: int,
    request: Request,
    current_admin: CurrentAdminUser,
    service: UserServiceDependency,
    csrf_token: str = Form(),
):
    verify_csrf_token(request, csrf_token)
    try:
        issued = await service.enable_api_access(user_id)
    except (ApiAccessAlreadyEnabled, ApiAccessProhibited, UserNotFound):
        return await _management_response(
            request,
            current_admin,
            service,
            error="API access cannot be enabled for that user.",
        )
    return _credential_response(request, current_admin, issued.user, issued.token)


@router.post("/users/{user_id}/disable-api", include_in_schema=False)
async def disable_api_access(
    user_id: int,
    request: Request,
    current_admin: CurrentAdminUser,
    service: UserServiceDependency,
    csrf_token: str = Form(),
):
    verify_csrf_token(request, csrf_token)
    try:
        await service.disable_api_access(user_id)
    except UserNotFound:
        return await _management_response(
            request,
            current_admin,
            service,
            error="API access cannot be disabled for that user.",
        )
    return RedirectResponse("/manage-users", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/users/{user_id}/regen-token", include_in_schema=False)
async def regenerate_api_token(
    user_id: int,
    request: Request,
    current_admin: CurrentAdminUser,
    service: UserServiceDependency,
    csrf_token: str = Form(),
):
    verify_csrf_token(request, csrf_token)
    try:
        issued = await service.regenerate_api_token(user_id)
    except (ApiAccessNotEnabled, ApiAccessProhibited, UserNotFound):
        return await _management_response(
            request,
            current_admin,
            service,
            error="The API token cannot be regenerated for that user.",
        )
    return _credential_response(request, current_admin, issued.user, issued.token)


@router.post("/users/{user_id}/toggle-active", include_in_schema=False)
async def toggle_active(
    user_id: int,
    request: Request,
    current_admin: CurrentAdminUser,
    service: UserServiceDependency,
    csrf_token: str = Form(),
):
    verify_csrf_token(request, csrf_token)
    try:
        target = await service.get_user(user_id)
        await service.set_active(
            user_id,
            not target.is_active,
            actor_user_id=current_admin.id,
        )
    except (LifecycleOperationProhibited, UserNotFound):
        return await _management_response(
            request,
            current_admin,
            service,
            error="That account status cannot be changed.",
        )
    return RedirectResponse("/manage-users", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/users/{user_id}/toggle-admin", include_in_schema=False)
async def toggle_admin(
    user_id: int,
    request: Request,
    current_admin: CurrentAdminUser,
    service: UserServiceDependency,
    csrf_token: str = Form(),
):
    verify_csrf_token(request, csrf_token)
    try:
        target = await service.get_user(user_id)
        await service.set_admin(
            user_id,
            not target.is_admin,
            actor_user_id=current_admin.id,
        )
    except (LifecycleOperationProhibited, UserNotFound):
        return await _management_response(
            request,
            current_admin,
            service,
            error="That account role cannot be changed.",
        )
    return RedirectResponse("/manage-users", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/users/{user_id}/delete", include_in_schema=False)
async def delete_user(
    user_id: int,
    request: Request,
    current_admin: CurrentAdminUser,
    service: UserServiceDependency,
    csrf_token: str = Form(),
):
    verify_csrf_token(request, csrf_token)
    try:
        await service.delete_user(user_id, actor_user_id=current_admin.id)
    except (LifecycleOperationProhibited, UserNotFound):
        return await _management_response(
            request,
            current_admin,
            service,
            error="That user cannot be deleted.",
        )
    return RedirectResponse("/manage-users", status_code=status.HTTP_303_SEE_OTHER)


def _credential_response(request, current_user, user, token) -> HTMLResponse:
    csrf_token = request.cookies.get(settings.csrf_cookie_name) or new_csrf_token()
    response = templates.TemplateResponse(
        request=request,
        name="api_token.html",
        context={
            "current_user": current_user,
            "user": user,
            "token": token,
            "csrf_token": csrf_token,
        },
        headers={"Cache-Control": "no-store"},
    )
    set_csrf_cookie(response, csrf_token)
    return response
