from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    seed_database_path: Path = Path("app/data/app.db")
    jwt_secret: SecretStr = SecretStr("")
    jwt_algorithm: str = "HS256"
    session_cookie_name: str = "locnet_session"
    session_max_age_seconds: int = 28_800
    session_cookie_secure: bool = False
    csrf_cookie_name: str = "locnet_csrf"
    map_tile_base_url: str = "https://api.maptiler.com"
    map_style_path: str = "/maps/hybrid-v4/style.json"
    maptiler_api_key: str | None = None
    map_tile_referer: str = "https://locnet.io"
    map_public_base_url: str = ""
    glo30_api_url: str = ""
    glo30_api_token: str = ""
    esawc_api_url: str = ""
    esawc_api_token: str = ""
    wpop_api_url: str = ""
    wpop_api_token: str = ""
    geospatial_api_timeout_seconds: float = 300
    geojson_cache_directory: str = "cache/geojson"
    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_sender: str = ""
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_starttls: bool = True


settings = Settings()
DATABASE_URL = settings.database_url
MAP_TILE_BASE_URL = settings.map_tile_base_url
MAP_STYLE_PATH = settings.map_style_path
MAPTILER_API_KEY = settings.maptiler_api_key
MAP_TILE_REFERER = settings.map_tile_referer
MAP_PUBLIC_BASE_URL = settings.map_public_base_url
GLO30_API_URL = settings.glo30_api_url
GLO30_API_TOKEN = settings.glo30_api_token
ESAWC_API_URL = settings.esawc_api_url
ESAWC_API_TOKEN = settings.esawc_api_token
WPOP_API_URL = settings.wpop_api_url
WPOP_API_TOKEN = settings.wpop_api_token
GEOSPATIAL_API_TIMEOUT_SECONDS = settings.geospatial_api_timeout_seconds
GEOJSON_CACHE_DIRECTORY = settings.geojson_cache_directory
