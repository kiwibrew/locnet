from contextlib import asynccontextmanager
from turtle import done
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement

from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from markdown import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from pydantic import BaseModel
from app.dependencies import DataRepositoryDependency
from app.database import engine
from routers import lookups
from routers.builder import router as builder_router
from library.helpers import *
import logging


DOCUMENTS_DIRECTORY = Path(__file__).resolve().parent / "docs"
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
    yield
    await engine.dispose()


app = FastAPI(title='Community Network Modeler',
              description='An application to model simple community networks',
              version='2.1',
              lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="spa/dist/assets"), name="assets")
app.mount("/documentation-assets", StaticFiles(directory=DOCUMENTS_DIRECTORY), name="documentation-assets")

app.include_router(lookups.router)
app.include_router(builder_router)

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")
spaTemplates = Jinja2Templates(directory="spa/dist")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def get_spa(
    request: Request,
    repository: DataRepositoryDependency,
    lang: str = 'en',
    ajax: bool = Query(False),
):
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

        return spaTemplates.TemplateResponse("index.html",
                                          {"request": request,
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
                                          } )
    except Exception as e:
        logging.error(f"Failed to load countries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load country data: {str(e)}")

class ModelQuery(BaseModel):
    iso_3: str
    lang: str

@app.post("/spa-query", include_in_schema=False,)
async def spa_post_handler(model_query: ModelQuery):
    return JSONResponse({ done: True })


@app.get("/documentation", response_class=HTMLResponse, include_in_schema=False)
async def documentation_page(
    request: Request,
    repository: DataRepositoryDependency,
    lang: str = 'en',
    embedded: bool = Query(False),
):
    try:
        # Get the UI text for the selected language
        text_data = await get_text(repository)
        selected_text = {item['element']: item[lang] for item in text_data}
        
        documentation_content = render_markdown_document("documentation.md")
        
        return templates.TemplateResponse("documentation.html",
                                         {"request": request,
                                          "text": selected_text,
                                          "selected_language": lang,
                                          "embedded": embedded,
                                          "documentation_content": documentation_content}
                                         )
    except Exception as e:
        logging.error(f"Failed to load documentation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load documentation: {str(e)}")


@app.get("/qsg", response_class=HTMLResponse, include_in_schema=False)
async def qsg_page(
    request: Request,
    repository: DataRepositoryDependency,
    lang: str = 'en',
    embedded: bool = Query(False),
):
    try:
        # Get the UI text for the selected language
        text_data = await get_text(repository)
        selected_text = {item['element']: item[lang] for item in text_data}
        
        qsg_content = render_markdown_document("qsg.md")
        
        return templates.TemplateResponse("qsg.html",
                                         {"request": request,
                                          "text": selected_text,
                                          "selected_language": lang,
                                          "embedded": embedded,
                                          "qsg_content": qsg_content}
                                         )
    except Exception as e:
        logging.error(f"Failed to load Quick Start Guide: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load Quick Start Guide: {str(e)}")


@app.get("/faq", response_class=HTMLResponse, include_in_schema=False)
async def faq_page(
    request: Request,
    repository: DataRepositoryDependency,
    lang: str = 'en',
    embedded: bool = Query(False),
):
    try:
        # Get the UI text for the selected language
        text_data = await get_text(repository)
        selected_text = {item['element']: item[lang] for item in text_data}

        faq_content = render_faq_document("faq.md")

        return templates.TemplateResponse("faq.html",
                                          {"request": request,
                                           "text": selected_text,
                                           "selected_language": lang,
                                           "embedded": embedded,
                                           "faq_content": faq_content}
                                          )
    except Exception as e:
        logging.error(f"Failed to load FAQ: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load FAQ: {str(e)}")
