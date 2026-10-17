"""Which websites the crawler visits. Override with CRAWL_SOURCES=a.com,b.com.
These Iranian online pharmacies were found by search but NOT verified:
whether each can be crawled (robots.txt, markup) is reported per site in
Admin > Data sources after the first run."""
import os

DEFAULT_SOURCES = [
    "pharmacy.digikala.com",
    "snapp.doctor",
    "digidaroo.org",
    "banidaroo.com",
    "betadarou.com",
    "darookhaneonline.com",
    "pezeshkbook.com",
    "darooboom.com",
    "daroogram.com",
    "darukade.com",
]


def get_sources() -> list[str]:
    env = os.environ.get("CRAWL_SOURCES", "").strip()
    items = [x.strip().lower().removeprefix("https://").removeprefix("http://").strip("/") for x in env.split(",")] if env else DEFAULT_SOURCES
    return [x for x in items if x]
