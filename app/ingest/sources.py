"""Which websites the crawler visits. Override with CRAWL_SOURCES=a.com,b.com.
Every source is an Iranian online pharmacy. The first group was confirmed to be
crawlable; the second group was found by search and is NOT verified: run
`python -m scripts.check_sites` to see which ones work from your connection."""
import os

DEFAULT_SOURCES = [
    # confirmed (robots.txt allows crawling, products have price markup)
    "darukade.com",
    "darookhaneonline.com",
    "digidaroo.org",
    "darooboom.com",
    "banidaroo.com",
    "daroogram.com",
    "betadarou.com",
    # candidates, not verified
    "mosbatesabz.com",
    "daroohome.com",
    "daroohelp.com",
    "daroodrug.com",
    "zeevash.com",
    "mcdarou.com",
    "darushahr.com",
    "ezdaroo.com",
    "snapp.doctor",
    "pharmacy.digikala.com",
    # found by search on 2026-11-13, not verified
    "zardaroo.com",
    "darukar.com",
    "darokhanechi.com",
    "multidaru.com",
    "pharmado.ir",
    "mokamelshop.com",
    "darutamin.com",
    "darmankade.com",
]


def get_sources() -> list[str]:
    env = os.environ.get("CRAWL_SOURCES", "").strip()
    items = [x.strip().lower().removeprefix("https://").removeprefix("http://").strip("/") for x in env.split(",")] if env else DEFAULT_SOURCES
    return [x for x in items if x]
