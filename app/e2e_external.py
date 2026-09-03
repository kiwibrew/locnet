from fastapi import FastAPI


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/viewsheds")
async def viewshed():
    return {
        "type": "Feature",
        "properties": {"visible_area_sq_km": 7.5},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [120.5, -10.2],
                    [120.7, -10.2],
                    [120.7, -10.0],
                    [120.5, -10.2],
                ]
            ],
        },
    }


@app.post("/api/land-cover-geojson")
async def land_cover():
    return {"10": 0.2, "95": 0.05}


@app.post("/api/pop-shape")
async def population():
    return {"pop": 456.5}


@app.get("/maps/hybrid-v4/style.json")
async def map_style():
    return {
        "version": 8,
        "name": "E2E map style",
        "sources": {},
        "layers": [
            {
                "id": "background",
                "type": "background",
                "paint": {"background-color": "#eef2f5"},
            }
        ],
    }
