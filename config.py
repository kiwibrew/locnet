import os
from dotenv import load_dotenv

# Load environment variables from a .env file (if present)
load_dotenv()

# Grist API Configuration
GRIST_SERVER = os.getenv("GRIST_SERVER")  # Default for local dev
GRIST_DOC_ID = os.getenv("GRIST_DOC_ID")
GRIST_API_KEY = os.getenv("GRIST_API_KEY")

# Map / MapLibre GL JS Configuration
# Base URL of the upstream map tile provider. This is proxied by the /api/tiles
# endpoint so the browser never talks to the provider directly. In the future this
# can be pointed at a self-hosted tile server by changing this single value.
MAP_TILE_BASE_URL = os.getenv("MAP_TILE_BASE_URL", "https://api.maptiler.com")
# Path (relative to MAP_TILE_BASE_URL) of the MapLibre style document to load.
MAP_STYLE_PATH = os.getenv("MAP_STYLE_PATH", "/maps/hybrid-v4/style.json")
# API key used when requesting tiles from the provider (MapTiler).
MAPTILER_API_KEY = os.getenv("MAPTILER_API_KEY")
# Origin/Referer value sent to the tile provider when requesting tiles.
MAP_TILE_REFERER = os.getenv("MAP_TILE_REFERER", "https://locnet.io")
# Public base URL of this application (scheme + host, no trailing slash), used to
# build ABSOLUTE tile-proxy URLs inside proxied style.json / TileJSON documents.
# MapLibre's Web Worker loads vector tiles, glyphs and the sprite and cannot
# resolve root-relative URLs, so absolute URLs are required.
# Normally leave this EMPTY: the proxy derives the public scheme/host from the
# incoming request, honouring the X-Forwarded-Proto / X-Forwarded-Host headers
# set by our Cloudflare Tunnel (cloudflared) on staging/production. This keeps the
# tile URLs on HTTPS there and on HTTP for plain local development, avoiding the
# browser's mixed-content blocker. Only set this if you need to hard-override the
# public origin (e.g. an unusual proxy that does not forward those headers).
MAP_PUBLIC_BASE_URL = os.getenv("MAP_PUBLIC_BASE_URL", "")

# Coverage and population services. Each service issues its own persistent
# bearer token, so deployments configure the credentials independently.
GLO30_API_URL = os.getenv("GLO30_API_URL", "")
GLO30_API_TOKEN = os.getenv("GLO30_API_TOKEN", "")
ESAWC_API_URL = os.getenv("ESAWC_API_URL", "")
ESAWC_API_TOKEN = os.getenv("ESAWC_API_TOKEN", "")
WPOP_API_URL = os.getenv("WPOP_API_URL", "")
WPOP_API_TOKEN = os.getenv("WPOP_API_TOKEN", "")
GEOSPATIAL_API_TIMEOUT_SECONDS = float(
    os.getenv("GEOSPATIAL_API_TIMEOUT_SECONDS", "300")
)
