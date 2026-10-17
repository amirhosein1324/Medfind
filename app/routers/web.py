import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..ingest import google, service
from ..ingest.crawler import crawl_source
from ..ingest.sources import get_sources
from ..models import CrawlSource, User, WebProduct
from ..schemas import CrawlSourceResponse, ProductPageResponse, WebProductResponse, WebSearchResponse
from ..security import require_role

router = APIRouter()
log = logging.getLogger("medfind.web")


@router.get("/search", response_model=WebSearchResponse)
def web_search(q: str, sort: str = "relevance", db: Session = Depends(get_db)):
    """Medicine products found on Iranian online pharmacies by the crawler,
    searchable in English or Persian. NOT confirmed by a MedFind pharmacy."""
    key = service.norm_query(q)
    total = db.query(func.count(WebProduct.product_id)).scalar() or 0
    enabled = total > 0 or google.enabled()
    if len(key) < 2 or not enabled:
        return WebSearchResponse(enabled=enabled, items=[])
    rows = service.search_local(db, key)
    if len(rows) < 3 and google.enabled() and not service.is_fresh(db, key):
        try:
            service.google_discover(db, key)
            rows = service.search_local(db, key)
        except httpx.HTTPError as e:
            log.warning("google discovery failed: %s", e)
    return WebSearchResponse(
        enabled=True,
        items=[WebProductResponse.model_validate(r) for r in rows],
        groups=service.search_groups(db, key, sort),
    )


@router.get("/product", response_model=ProductPageResponse)
def web_product(key: str, db: Session = Depends(get_db)):
    """One medicine with every shop's offer (cheapest first) and its price history."""
    g = service.get_group(db, key)
    if not g:
        raise HTTPException(status_code=404, detail="Product not found")
    g["history"] = service.price_history(db, [o["url"] for o in g["offers"]])
    return g


@router.get("/suggest")
def web_suggest(q: str, db: Session = Depends(get_db)):
    """Type-ahead names built from crawled products (English first)."""
    key = service.norm_query(q)
    if len(key) < 2:
        return []
    seen, out = set(), []
    for r in service.search_local(db, key, 200):
        name = r.title_en or r.title
        if name.lower() not in seen:
            seen.add(name.lower())
            out.append({"name": name, "generic_name": r.generic_en})
        if len(out) >= 8:
            break
    return out


@router.get("/sources", response_model=list[CrawlSourceResponse])
def list_sources(db: Session = Depends(get_db), _admin: User = Depends(require_role("admin"))):
    """Admin: every configured site and how its last crawl went."""
    known = {s.domain: s for s in db.query(CrawlSource).all()}
    out = []
    for d in get_sources():
        s = known.get(d)
        out.append(CrawlSourceResponse(
            domain=d, status=s.status if s else "pending", detail=s.detail if s else None,
            urls_found=s.urls_found if s else 0,
            products_total=db.query(WebProduct).filter(WebProduct.source_domain == d).count(),
            last_run=s.last_run if s else None))
    return out


def _crawl_in_background(domain: str, max_pages: int):
    db = SessionLocal()
    try:
        crawl_source(db, domain, max_pages)
    except Exception:
        log.exception("crawl failed for %s", domain)
    finally:
        db.close()


@router.post("/crawl/{domain}", status_code=202)
def crawl_now(domain: str, background: BackgroundTasks, _admin: User = Depends(require_role("admin"))):
    """Admin: start a crawl of one configured site in the background."""
    if domain not in get_sources():
        raise HTTPException(status_code=404, detail="Not a configured source")
    background.add_task(_crawl_in_background, domain, 150)
    return {"started": domain}
