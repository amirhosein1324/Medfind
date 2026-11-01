"""Discovery through the official Google Programmable Search JSON API.
(Scraping google.com itself is blocked and against its terms.)"""
import httpx

from ..config import settings

ENDPOINT = "https://www.googleapis.com/customsearch/v1"


def enabled() -> bool:
    return bool(settings.google_api_key and settings.google_cse_id)


def search_urls(query: str, limit: int = 10) -> list[str]:
    """Return up to `limit` result URLs (Google returns max 10 per call)."""
    r = httpx.get(
        ENDPOINT,
        params={
            "key": settings.google_api_key,
            "cx": settings.google_cse_id,
            "q": f"{query} buy price pharmacy",
            "num": min(limit, 10),
        },
        timeout=8,
    )
    r.raise_for_status()
    return [i["link"] for i in r.json().get("items", []) if i.get("link")]
