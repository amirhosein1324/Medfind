"""Querying the web product index, with optional live Google discovery."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ExternalQuery, WebProduct
from . import google
from .crawler import upsert_product
from .extract import extract_products
from .http import Fetcher
from .persian import normalize, search_terms

_RANK = {"available": 0, "limited_stock": 1, "unknown": 2, "out_of_stock": 3}


def norm_query(q: str) -> str:
    return normalize(q).lower()[:255]


def search_local(db: Session, q: str, limit: int = 80) -> list[WebProduct]:
    conds = []
    for t in search_terms(q):
        like = f"%{t}%"
        conds += [WebProduct.title.ilike(like), WebProduct.title_en.ilike(like), WebProduct.generic_en.ilike(like)]
    if not conds:
        return []
    rows = db.query(WebProduct).filter(or_(*conds)).limit(400).all()
    rows.sort(key=lambda r: (_RANK.get(r.availability, 9), r.price is None, r.price or 0))
    return rows[:limit]


def is_fresh(db: Session, q: str) -> bool:
    meta = db.get(ExternalQuery, q)
    return bool(meta and meta.fetched_at > datetime.utcnow() - timedelta(hours=settings.web_cache_hours))


def _process(url: str, f: Fetcher) -> list[tuple[str, str, dict]]:
    html = f.get(url)
    host = (urlparse(url).hostname or "").removeprefix("www.")
    return [(url, host, p) for p in extract_products(html or "")[:1]]


def google_discover(db: Session, raw_query: str) -> None:
    """Find extra pages for a query through Google and add them to the index."""
    q = norm_query(raw_query)
    urls = google.search_urls(q, settings.web_max_pages)[: settings.web_max_pages]
    f = Fetcher(delay=0.5)
    with ThreadPoolExecutor(max_workers=4) as pool:
        found = [x for res in pool.map(lambda u: _process(u, f), urls) for x in res]
    for url, host, p in found:
        upsert_product(db, url, host, p)
    meta = db.get(ExternalQuery, q) or ExternalQuery(query=q)
    meta.fetched_at, meta.result_count = datetime.utcnow(), len(found)
    db.add(meta)
    db.commit()
