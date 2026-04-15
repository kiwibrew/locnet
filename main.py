from turtle import done

from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from routers import lookups
from routers.builder import router as builder_router
from library.helpers import *
from library.confluence import get_documentation_content, get_qsg_content
import logging

app = FastAPI(title='Community Network Modeler',
              description='An application to model simple community networks',
              version='2.1')

app.mount("/cache", StaticFiles(directory="cache"), name="cache")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="spa/dist/assets"), name="assets")

app.include_router(lookups.router)
app.include_router(builder_router)

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")
spaTemplates = Jinja2Templates(directory="spa/dist")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def get_spa(request: Request, lang: str = 'en', ajax: bool = Query(False)):
    try:
        # Get the countries data
        country_data = get_countries()
        # Get the UI text for the selected language
        text_data = get_text()
        selected_text = {item['element']: item[lang] for item in text_data}
        frequencies = get_frequencies()
        terrain = get_terrain()
        vegetation = get_vegetation()
        technologies = get_technologies()
        midhaul_data = get_midhaul()
        backhaul_data = get_backhaul()
        tower_data = get_towers()
        all_net_types = get_network_types()
        tech_data = get_tech_data()
        paf_facilities_charge = get_paf_facilities_charge()
        power_types = get_power()

        if ajax:
            # Return only the text data as JSON for AJAX requests
            return JSONResponse({"text": selected_text, "selected_language": lang})

        return spaTemplates.TemplateResponse("index.html",
                                          {"request": request,
                                           "countries": country_data,
                                           "text": text_data,
                                           "selected_language": lang,
                                           "frequencies": frequencies,
                                           "terrain": terrain,
                                           "vegetation": vegetation,
                                           "technologies": technologies,
                                           "network_types": all_net_types,
                                           "power_types": power_types,
                                           "midhaul_data": midhaul_data,
                                           "backhaul_data": backhaul_data,
                                           "tower_data": tower_data,
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
async def documentation_page(request: Request, lang: str = 'en'):
    try:
        # Get the UI text for the selected language
        text_data = get_text()
        selected_text = {item['element']: item[lang] for item in text_data}
        
        # Get documentation content from Confluence
        documentation_content = get_documentation_content()
        
        return templates.TemplateResponse("documentation.html",
                                         {"request": request,
                                          "text": selected_text,
                                          "selected_language": lang,
                                          "documentation_content": documentation_content}
                                         )
    except Exception as e:
        logging.error(f"Failed to load documentation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load documentation: {str(e)}")


@app.get("/qsg", response_class=HTMLResponse, include_in_schema=False)
async def qsg_page(request: Request, lang: str = 'en'):
    try:
        # Get the UI text for the selected language
        text_data = get_text()
        selected_text = {item['element']: item[lang] for item in text_data}
        
        # Get Quick Start Guide content from Confluence
        qsg_content = get_qsg_content()
        
        return templates.TemplateResponse("qsg.html",
                                         {"request": request,
                                          "text": selected_text,
                                          "selected_language": lang,
                                          "qsg_content": qsg_content}
                                         )
    except Exception as e:
        logging.error(f"Failed to load Quick Start Guide: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load Quick Start Guide: {str(e)}")
