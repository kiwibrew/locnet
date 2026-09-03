import asyncio
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from markdown import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from pydantic import BaseModel
from app.database import engine
from app.config import settings
from app.dependencies import (
    ActiveSessionUser,
    CurrentSessionUser,
    DataRepositoryDependency,
)
from app.error_handlers import user_service_error_handler
from app.routers import auth, database_admin, users
from app.security import require_api_csrf
from app.routers import lookups
from app.routers.builder import router as builder_router
from app.services.reference_data import (
    get_backhaul,
    get_countries,
    get_frequencies,
    get_midhaul,
    get_network_types,
    get_paf_facilities_charge,
    get_power,
    get_tech_data,
    get_technologies,
    get_text,
    get_tower_details,
    get_towers,
)
from app.services.users import UserServiceError
import logging


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIRECTORY = REPOSITORY_ROOT / "docs"
EXAMPLES_DIRECTORY = DOCUMENTS_DIRECTORY / "examples"


def list_example_filenames(directory: Path) -> list[str]:
    """Return JSON example filenames in display order."""
    return sorted(
        (path.name for path in directory.glob("*.json") if path.is_file()),
        key=str.casefold,
    )


def render_markdown_document(filename: str) -> str:
    """Read a local Markdown document and convert it to HTML for a template."""
    markdown_source = (DOCUMENTS_DIRECTORY / filename).read_text(encoding="utf-8")
    return markdown(markdown_source, extensions=["extra", "toc"])

class FaqAccordionTreeprocessor(Treeprocessor):
    """Group level-two headings and their content into FAQ disclosures."""

    def run(self, root: Element) -> None:
        children = list(root)
        for child in children:
            root.remove(child)

        answer = None
        for child in children:
            if child.tag == "h2":
                details = SubElement(
                    root, "details", {"class": "faq-item", "name": "faq"}
                )
                summary = SubElement(details, "summary")
                summary.append(child)
                answer = SubElement(details, "div", {"class": "faq-answer"})
            elif answer is None:
                root.append(child)
            else:
                answer.append(child)


class FaqAccordionExtension(Extension):
    def extendMarkdown(self, md) -> None:
        md.treeprocessors.register(
            FaqAccordionTreeprocessor(md), "faq_accordion", 1
        )


def render_faq_document(filename: str) -> str:
    """Render a Markdown FAQ with level-two headings as accordion items."""
    markdown_source = (DOCUMENTS_DIRECTORY / filename).read_text(encoding="utf-8")
    return markdown(
        markdown_source,
        extensions=["extra", "toc", FaqAccordionExtension()],
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.jwt_secret.get_secret_value():
        raise RuntimeError("JWT_SECRET must be configured")
    yield
    await engine.dispose()


ui_router = APIRouter()

# Set up Jinja2 templates
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")
spaTemplates = Jinja2Templates(directory=REPOSITORY_ROOT / "spa/dist")

@ui_router.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def get_spa(
    request: Request,
    repository: DataRepositoryDependency,
    current_user: CurrentSessionUser,
    lang: str = 'en',
    ajax: bool = Query(False),
):
    if current_user is None:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    try:
        # Get the countries data
        country_data = await get_countries(repository)
        # Get the UI text for the selected language
        text_data = await get_text(repository)
        selected_text = {item['element']: item[lang] for item in text_data}
        frequencies = await get_frequencies(repository)
        technologies = await get_technologies(repository)
        midhaul_data = await get_midhaul(repository)
        backhaul_data = await get_backhaul(repository)
        tower_data = await get_towers(repository)
        tower_details = await get_tower_details(repository)
        all_net_types = await get_network_types(repository)
        tech_data = await get_tech_data(repository)
        paf_facilities_charge = await get_paf_facilities_charge(repository)
        power_types = await get_power(repository)

        if ajax:
            # Return only the text data as JSON for AJAX requests
            return JSONResponse({"text": selected_text, "selected_language": lang})

        example_filenames = list_example_filenames(EXAMPLES_DIRECTORY)

        return spaTemplates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "countries": country_data,
                "text": text_data,
                "selected_language": lang,
                "example_filenames": example_filenames,
                "frequencies": frequencies,
                "technologies": technologies,
                "network_types": all_net_types,
                "power_types": power_types,
                "midhaul_data": midhaul_data,
                "backhaul_data": backhaul_data,
                "tower_data": tower_data,
                "tower_details": tower_details,
                "tech_data": tech_data,
                "paf_facilities_charge": paf_facilities_charge,
                "current_user": {
                    "email": current_user.email,
                    "is_admin": current_user.is_admin,
                    "api_access_enabled": current_user.api_access_enabled,
                },
                "csrf_token": request.cookies.get(settings.csrf_cookie_name, ""),
            },
        )
    except Exception:
        logging.exception("Failed to load application data")
        raise HTTPException(status_code=500, detail="Failed to load application data")

class ModelQuery(BaseModel):
    iso_3: str
    lang: str

@ui_router.post(
    "/spa-query",
    include_in_schema=False,
    dependencies=[Depends(require_api_csrf)],
)
async def spa_post_handler(
    model_query: ModelQuery,
    _current_user: ActiveSessionUser,
):
    return JSONResponse({"done": True})


@ui_router.get("/documentation", response_class=HTMLResponse, include_in_schema=False)
async def documentation_page(
    request: Request,
    repository: DataRepositoryDependency,
    current_user: CurrentSessionUser,
    lang: str = 'en',
    embedded: bool = Query(False),
):
    try:
        # Get the UI text for the selected language
        text_data = await get_text(repository)
        selected_text = {item['element']: item[lang] for item in text_data}

        documentation_content = await asyncio.to_thread(
            render_markdown_document,
            "documentation.md",
        )

        return templates.TemplateResponse(
            request=request,
            name="documentation.html",
            context={
                "text": selected_text,
                "selected_language": lang,
                "embedded": embedded,
                "back_href": "/app" if current_user else "/",
                "documentation_content": documentation_content,
            },
        )
    except Exception:
        logging.exception("Failed to load documentation")
        raise HTTPException(status_code=500, detail="Failed to load documentation")


@ui_router.get("/qsg", response_class=HTMLResponse, include_in_schema=False)
async def qsg_page(
    request: Request,
    repository: DataRepositoryDependency,
    current_user: CurrentSessionUser,
    lang: str = 'en',
    embedded: bool = Query(False),
):
    try:
        # Get the UI text for the selected language
        text_data = await get_text(repository)
        selected_text = {item['element']: item[lang] for item in text_data}

        qsg_content = await asyncio.to_thread(render_markdown_document, "qsg.md")

        return templates.TemplateResponse(
            request=request,
            name="qsg.html",
            context={
                "text": selected_text,
                "selected_language": lang,
                "embedded": embedded,
                "back_href": "/app" if current_user else "/",
                "qsg_content": qsg_content,
            },
        )
    except Exception:
        logging.exception("Failed to load Quick Start Guide")
        raise HTTPException(status_code=500, detail="Failed to load Quick Start Guide")


@ui_router.get("/faq", response_class=HTMLResponse, include_in_schema=False)
async def faq_page(
    request: Request,
    repository: DataRepositoryDependency,
    current_user: CurrentSessionUser,
    lang: str = 'en',
    embedded: bool = Query(False),
):
    try:
        # Get the UI text for the selected language
        text_data = await get_text(repository)
        selected_text = {item['element']: item[lang] for item in text_data}

        faq_content = await asyncio.to_thread(render_faq_document, "faq.md")

        return templates.TemplateResponse(
            request=request,
            name="faq.html",
            context={
                "text": selected_text,
                "selected_language": lang,
                "embedded": embedded,
                "back_href": "/app" if current_user else "/",
                "faq_content": faq_content,
            },
        )
    except Exception:
        logging.exception("Failed to load FAQ")
        raise HTTPException(status_code=500, detail="Failed to load FAQ")


@ui_router.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}


@ui_router.get("/docs", include_in_schema=False)
async def api_documentation(request: Request, current_user: CurrentSessionUser):
    if current_user is None:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    if current_user.is_admin or not current_user.api_access_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    swagger = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Community Network Builder API",
    )
    csrf_token = escape(request.cookies.get(settings.csrf_cookie_name, ""))
    email = escape(current_user.email)
    navigation = (
        '<nav style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;'
        'background:#eee;color:#222;font-family:sans-serif">'
        '<a href="/app" style="color:#222;text-decoration:none;font-size:1.25rem">'
        "Community Network Builder</a>"
        '<a href="/manage-users" style="color:#000;background:#fff;border:1px solid #ccc;'
        'border-radius:4px;padding:.5em .75em;text-decoration:none">Manage users</a>'
        f'<span style="margin-left:auto">{email}</span>'
        '<form method="post" action="/logout" style="margin:0">'
        f'<input type="hidden" name="csrf_token" value="{csrf_token}">'
        '<button type="submit" style="background:#fff;border:1px solid #ccc;border-radius:4px;'
        'padding:.5em .75em;cursor:pointer">Sign out</button></form></nav>'
    )
    body = swagger.body.decode("utf-8").replace("<body>", f"<body>{navigation}", 1)
    return HTMLResponse(body, headers={"Cache-Control": "no-store"})


@ui_router.get("/openapi.json", include_in_schema=False)
async def protected_openapi(request: Request, current_user: CurrentSessionUser):
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if current_user.is_admin or not current_user.api_access_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return JSONResponse(request.app.openapi())


def create_app() -> FastAPI:
    application = FastAPI(
        title="Community Network Modeler",
        description="An application to model simple community networks",
        version="2.1",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.mount(
        "/static",
        StaticFiles(directory=REPOSITORY_ROOT / "static"),
        name="static",
    )
    application.mount(
        "/assets",
        StaticFiles(directory=REPOSITORY_ROOT / "spa/dist/assets"),
        name="assets",
    )
    application.mount(
        "/documentation-assets",
        StaticFiles(directory=DOCUMENTS_DIRECTORY),
        name="documentation-assets",
    )
    application.include_router(lookups.router)
    application.include_router(builder_router)
    application.include_router(auth.router)
    application.include_router(users.router)
    application.include_router(database_admin.router)
    application.include_router(ui_router)
    application.add_exception_handler(UserServiceError, user_service_error_handler)
    return application


app = create_app()
