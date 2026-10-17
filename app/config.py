"""
Central application settings, loaded from environment variables / .env.

Keeping this in one place means every module (database, security, routers)
reads config the same way instead of scattering os.getenv() calls around.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://medfind:medfind@localhost:5432/medfind"
    secret_key: str = "change-this-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Web discovery (Google Programmable Search API). Leave blank to disable.
    google_api_key: str = ""
    google_cse_id: str = ""
    web_cache_hours: int = 24      # re-use results for a query this long
    web_max_pages: int = 8         # pages fetched per uncached query

    # Site crawler (scripts/crawl.py): polite, sitemap-driven, robots.txt aware
    sources_file: str = "sources.json"
    crawl_delay_seconds: float = 1.0
    crawl_max_pages: int = 300      # pages per source per run
    crawl_recrawl_hours: int = 24   # don't re-read a page sooner than this
    crawl_interval_hours: int = 6   # used by scripts/crawl_loop.py
    allow_private_hosts: bool = False  # tests only


settings = Settings()
