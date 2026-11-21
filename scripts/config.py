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

    # Which crawled products are shown. Old or sold-out products are hidden (not deleted: see scripts/prune.py).
    web_max_age_days: int = 14           # hide products not re-confirmed by the crawler for this many days (0 = never hide)
    web_hide_unavailable: bool = True    # hide products the shop marks as out of stock
    log_searches: bool = False     # privacy by design: search text can reveal health conditions

    # Site crawler (scripts/crawl.py): polite, sitemap-driven, robots.txt aware
    sources_file: str = "sources.json"
    crawl_delay_seconds: float = 1.0
    crawl_max_pages: int = 300      # pages per source per run
    crawl_recrawl_hours: int = 24   # don't re-read a page sooner than this
    crawl_interval_hours: int = 6   # used by scripts/crawl_loop.py
    allow_private_hosts: bool = False  # tests only


settings = Settings()
