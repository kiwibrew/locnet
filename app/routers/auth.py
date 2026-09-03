from pathlib import Path

from fastapi import APIRouter, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr

from app.dependencies import (
    CurrentSessionUser,
    DataRepositoryDependency,
    PasswordResetSenderDependency,
    UserServiceDependency,
    build_session_token_service,
)
from app.repositories import DataRepository
from app.security import (
    clear_authentication_cookies,
    new_csrf_token,
    set_csrf_cookie,
    set_session_cookie,
    verify_csrf_token,
)
from app.services.reference_data import get_site_text_by_language
from app.services.users import InvalidCredentials, InvalidResetCode


router = APIRouter()
templates = Jinja2Templates(
    directory=Path(__file__).resolve().parents[1] / "templates"
)
LANDING_LANGUAGES = {"en": "English", "es": "Español"}


def _template_context(request: Request, **values):
    return {"request": request, **values}


def _landing_language(lang: str) -> str:
    normalized = lang.strip().lower()
    return normalized if normalized in LANDING_LANGUAGES else "en"


async def _landing_response(
    request: Request,
    repository: DataRepository,
    *,
    csrf_token: str,
    lang: str,
    error: str | None = None,
    reset_complete: bool = False,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    selected_language = _landing_language(lang)
    text = await get_site_text_by_language(repository, selected_language)
    response = templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_template_context(
            request,
            csrf_token=csrf_token,
            error=error,
            reset_complete=reset_complete,
            text=text,
            languages=LANDING_LANGUAGES,
            selected_language=selected_language,
        ),
        status_code=status_code,
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def sign_in_page(
    request: Request,
    current_user: CurrentSessionUser,
    repository: DataRepositoryDependency,
    lang: str = Query("en"),
):
    if current_user is not None:
        return RedirectResponse("/app", status_code=status.HTTP_303_SEE_OTHER)
    csrf_token = new_csrf_token()
    return await _landing_response(
        request,
        repository,
        csrf_token=csrf_token,
        lang=lang,
        reset_complete=request.query_params.get("reset") == "complete",
    )


@router.post("/login", response_class=HTMLResponse, include_in_schema=False)
async def sign_in(
    request: Request,
    service: UserServiceDependency,
    repository: DataRepositoryDependency,
    email: EmailStr = Form(),
    password: str = Form(min_length=8, max_length=128),
    csrf_token: str = Form(),
    lang: str = Form("en"),
):
    verify_csrf_token(request, csrf_token)
    try:
        user = await service.authenticate_password(str(email), password)
    except InvalidCredentials:
        replacement_csrf_token = new_csrf_token()
        return await _landing_response(
            request,
            repository,
            csrf_token=replacement_csrf_token,
            lang=lang,
            error="Invalid email, password, or account status.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    session_token = build_session_token_service().create(user.email)
    response = RedirectResponse("/app", status_code=status.HTTP_303_SEE_OTHER)
    set_session_cookie(response, session_token)
    set_csrf_cookie(response, new_csrf_token())
    return response


@router.post("/logout", include_in_schema=False)
async def sign_out(
    request: Request,
    current_user: CurrentSessionUser,
    csrf_token: str = Form(),
):
    if current_user is None:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    verify_csrf_token(request, csrf_token)
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    clear_authentication_cookies(response)
    return response


@router.get("/forgot-password", response_class=HTMLResponse, include_in_schema=False)
async def forgot_password_page(request: Request):
    csrf_token = new_csrf_token()
    response = templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context=_template_context(request, csrf_token=csrf_token, acknowledged=False),
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/forgot-password", response_class=HTMLResponse, include_in_schema=False)
async def request_password_reset(
    request: Request,
    service: UserServiceDependency,
    sender: PasswordResetSenderDependency,
    email: EmailStr = Form(),
    csrf_token: str = Form(),
):
    verify_csrf_token(request, csrf_token)
    await service.request_password_reset(str(email), sender)
    replacement_csrf_token = new_csrf_token()
    response = templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context=_template_context(
            request,
            csrf_token=replacement_csrf_token,
            acknowledged=True,
        ),
    )
    set_csrf_cookie(response, replacement_csrf_token)
    return response


@router.get("/reset-password", response_class=HTMLResponse, include_in_schema=False)
async def reset_password_page(request: Request):
    csrf_token = new_csrf_token()
    response = templates.TemplateResponse(
        request=request,
        name="reset_password.html",
        context=_template_context(request, csrf_token=csrf_token),
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/reset-password", response_class=HTMLResponse, include_in_schema=False)
async def reset_password(
    request: Request,
    service: UserServiceDependency,
    code: str = Form(),
    password: str = Form(min_length=8, max_length=128),
    csrf_token: str = Form(),
):
    verify_csrf_token(request, csrf_token)
    try:
        await service.reset_password(code, password)
    except (InvalidResetCode, ValueError):
        replacement_csrf_token = new_csrf_token()
        response = templates.TemplateResponse(
            request=request,
            name="reset_password.html",
            context=_template_context(
                request,
                csrf_token=replacement_csrf_token,
                error="The reset code is invalid or expired.",
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
        set_csrf_cookie(response, replacement_csrf_token)
        return response
    return RedirectResponse("/?reset=complete", status_code=status.HTTP_303_SEE_OTHER)
