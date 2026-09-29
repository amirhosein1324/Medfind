"""
Central application settings, loaded from environment variables / .env.

Keeping this in one place means every module (database, security, routers)
reads config the same way instead of scattering os.getenv() calls around.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


<<<<<<< HEAD
=======
DEFAULT_SECRET_KEY = "change-this-to-a-long-random-string"


>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://medfind:medfind@localhost:5432/medfind"
<<<<<<< HEAD
    secret_key: str = "change-this-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


settings = Settings()
=======
    secret_key: str = DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    # Comma-separated list of allowed browser origins, e.g.
    # "https://medfind.app,https://admin.medfind.app". "*" for local dev only.
    cors_allowed_origins: str = "*"
    debug: bool = True


settings = Settings()

if not settings.debug and settings.secret_key == DEFAULT_SECRET_KEY:
    raise RuntimeError(
        "Refusing to start with DEBUG=false and the default SECRET_KEY. "
        "Set a strong, random SECRET_KEY in your environment/.env."
    )


def get_cors_origins() -> list[str]:
    raw = settings.cors_allowed_origins.strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
