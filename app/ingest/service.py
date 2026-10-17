"""Querying the web product index, with optional live Google discovery."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from urllib.parse import urlparse

import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ExternalQuery, PricePoint, WebProduct
from . import google
from .crawler import upsert_product
from .extract import extract_products
from .http import Fetcher
from .persian import analyze_title, normalize, search_terms

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


# ---------------------------------------------------------------- grouping
def _slug(t: str) -> str:
    return re.sub(r"[^\w]+", "-", normalize(t).lower(), flags=re.U).strip("-")[:90]


def group_key(r: WebProduct) -> str:
    """Same medicine, strength and form on different shops -> same key."""
    a = analyze_title(r.title)
    if a["generic"]:
        return _slug(" ".join(x for x in (a["generic"], a["strength"], a["form"]) if x))
    return _slug(r.title_en or r.title)


def _offer(r: WebProduct) -> dict:
    return {"shop": r.source_domain, "title": r.title, "price": r.price, "currency": r.currency,
            "availability": r.availability, "url": r.url, "fetched_at": r.fetched_at}


def _offer_sort(o):
    return (o["availability"] == "out_of_stock", o["price"] is None, o["price"] or 0)


def build_group(key: str, rows: list[WebProduct]) -> dict:
    offers = sorted((_offer(r) for r in rows), key=_offer_sort)
    priced = [o["price"] for o in offers if o["price"] is not None and o["availability"] != "out_of_stock"] or \
             [o["price"] for o in offers if o["price"] is not None]
    first = rows[0]
    name = next((r.title_en for r in rows if r.title_en), None) or first.title
    fa = next((r.title for r in rows if re.search(r"[\u0600-\u06FF]", r.title)), None)
    return {
        "key": key, "name": name, "title_fa": fa if fa and fa != name else None,
        "generic": next((r.generic_en for r in rows if r.generic_en), None),
        "image_url": next((r.image_url for r in rows if r.image_url), None),
        "min_price": min(priced) if priced else None, "max_price": max(priced) if priced else None,
        "currency": next((r.currency for r in rows if r.currency), None),
        "shops": len({r.source_domain for r in rows}),
        "available": sum(1 for r in rows if r.availability in ("available", "limited_stock")),
        "offers": offers,
    }


def search_groups(db: Session, q: str, sort: str = "relevance", limit: int = 40) -> list[dict]:
    buckets: dict[str, list[WebProduct]] = {}
    for r in search_local(db, q, 400):
        buckets.setdefault(group_key(r), []).append(r)
    groups = [build_group(k, v) for k, v in buckets.items() if k]
    if sort == "price":
        groups.sort(key=lambda g: (g["min_price"] is None, g["min_price"] or 0))
    else:
        groups.sort(key=lambda g: (-g["available"], -g["shops"], g["min_price"] is None, g["min_price"] or 0))
    return groups[:limit]


def get_group(db: Session, key: str) -> dict | None:
    first = (key.split("-")[0] if key else "")
    if len(first) < 2:
        return None
    rows = [r for r in search_local(db, first, 400) if group_key(r) == key]
    return build_group(key, rows) if rows else None


def price_history(db: Session, urls: list[str], days: int = 90) -> list[dict]:
    """Lowest observed price per day across the offers of one product."""
    since = datetime.utcnow() - timedelta(days=days)
    pts = db.query(PricePoint).filter(PricePoint.url.in_(urls), PricePoint.seen_at >= since).all()
    by_day: dict[str, float] = {}
    for p in pts:
        d = p.seen_at.date().isoformat()
        by_day[d] = min(by_day.get(d, float("inf")), float(p.price))
    return [{"date": d, "min_price": v} for d, v in sorted(by_day.items())]
