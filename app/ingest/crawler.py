"""Sitemap-driven crawler: discover product pages -> fetch -> extract -> store."""
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..models import CrawlSource, PricePoint, WebProduct
from .extract import extract_products
from .http import Fetcher
from .persian import analyze_title, normalize, to_toman

log = logging.getLogger("medfind.crawler")
LOC = re.compile(r"<loc>\s*(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?\s*</loc>", re.I | re.S)
PRODUCT_HINT = re.compile(r"/(product|products|p|dkp|drug|medicine|shop|item|buy)([-/]|$)|دارو|%d8%af%d8%a7%d8%b1%d9%88", re.I)
SITEMAP_HINT = re.compile(r"product|drug|medicine|dkp|shop|item", re.I)
MAX_SITEMAPS = 40
MAX_URLS = 100_000


def _status(db: Session, domain: str) -> CrawlSource:
    row = db.get(CrawlSource, domain) or CrawlSource(domain=domain)
    db.add(row)
    return row


def discover_urls(f: Fetcher, base: str) -> list[str]:
    rp = f.robots(base)
    roots = list(rp.site_maps() or []) if rp else []
    roots = roots or [base + "/sitemap.xml", base + "/sitemap_index.xml"]
    queue, seen, urls = list(roots), set(), []
    while queue and len(seen) < MAX_SITEMAPS and len(urls) < MAX_URLS:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        body = f.get(sm, accept="application/xml,text/xml,*/*")
        if not body:
            continue
        locs = LOC.findall(body)
        if "<sitemapindex" in body[:2000].lower():
            locs.sort(key=lambda u: 0 if SITEMAP_HINT.search(u) else 1)
            queue = locs + queue
        else:
            urls.extend(locs)
    hinted = [u for u in urls if PRODUCT_HINT.search(u)]
    return hinted or urls


HREF = re.compile(r'href=["\']([^"\'#]+)["\']', re.I)
LISTING_HINT = re.compile(r"categor|/cat/|/c/|/shop|/store|/products?/?$|دسته|داروخانه", re.I)
SEEDS = ["/", "/store/", "/shop/", "/products/"]


def discover_by_links(f: Fetcher, base: str, max_listing_pages: int = 25) -> list[str]:
    """Fallback when the sitemap has no product pages: read the homepage and
    listing pages and follow links that look like products (same site only)."""
    from urllib.parse import urljoin, urlparse
    host = urlparse(base).netloc
    queue, seen, products = [base + p for p in SEEDS], set(), []
    while queue and len(seen) < max_listing_pages:
        page = queue.pop(0)
        if page in seen:
            continue
        seen.add(page)
        html = f.get(page)
        if not html:
            continue
        for href in HREF.findall(html):
            u = urljoin(page, href.strip()).split("#")[0]
            if urlparse(u).netloc != host:
                continue
            if PRODUCT_HINT.search(u) and not LISTING_HINT.search(u.rsplit("/", 1)[-1] or "x"):
                products.append(u)
            elif LISTING_HINT.search(u) and u not in seen and len(queue) < 100:
                queue.append(u)
    return list(dict.fromkeys(products))


def upsert_product(db: Session, url: str, domain: str, p: dict) -> WebProduct:
    a = analyze_title(p["title"])
    price, cur = to_toman(p["price"], p.get("currency"))
    row = db.query(WebProduct).filter(WebProduct.url == url[:1000]).first() or WebProduct(url=url[:1000])
    row.source_domain = domain[:255]
    row.title = normalize(p["title"])[:500]
    row.title_en = a["name_en"][:300] if a["name_en"] else None
    row.generic_en = a["generic"]
    row.price, row.currency = price, cur
    row.availability = p["availability"]
    row.image_url = p.get("image_url")
    row.fetched_at = datetime.utcnow()
    db.add(row)
    if price is not None:
        last = (db.query(PricePoint).filter(PricePoint.url == row.url)
                .order_by(PricePoint.seen_at.desc()).first())
        if last is None or float(last.price) != float(price) or last.seen_at < datetime.utcnow() - timedelta(hours=20):
            db.add(PricePoint(url=row.url, price=price))
    return row


def crawl_source(db: Session, domain: str, max_pages: int = 300, fetcher: Fetcher | None = None) -> dict:
    f = fetcher or Fetcher()
    base = f"https://{domain}"
    st = _status(db, domain)
    st.last_run = datetime.utcnow()
    result = {"domain": domain, "status": "ok", "urls": 0, "saved": 0}

    def finish(status, detail=None):
        st.status, st.detail = status, detail
        st.urls_found = result["urls"]
        st.products_total = db.query(WebProduct).filter(WebProduct.source_domain == domain).count()
        db.commit()
        result["status"] = status
        log.info("%s: %s %s", domain, status, detail or "")
        return result

    rp = f.robots(base)
    if rp is None:
        why = f.errors.get(base, "unknown error")
        return finish("unreachable", f"Could not read robots.txt: {why}")
    if not rp.can_fetch("MedFindBot", base + "/"):
        return finish("blocked_by_robots", "robots.txt does not allow crawling")

    urls = discover_urls(f, base)
    if not any(PRODUCT_HINT.search(u) for u in urls):
        urls = discover_by_links(f, base) or urls
    result["urls"] = len(urls)
    if not urls:
        return finish("no_sitemap", "No sitemap with URLs found")

    known = {u: t for u, t in db.query(WebProduct.url, WebProduct.fetched_at).filter(WebProduct.source_domain == domain)}
    # product-looking URLs first: sitemaps list blog posts and categories too
    urls = sorted(urls, key=lambda u: not PRODUCT_HINT.search(u))
    fresh = [u for u in urls if u[:1000] not in known]
    stale = sorted((u for u in urls if u[:1000] in known), key=lambda u: known[u[:1000]])
    for url in (fresh + stale)[:max_pages]:
        html = f.get(url)
        if not html:
            continue
        for p in extract_products(html)[:1]:
            if p["price"] is None and p["availability"] == "unknown":
                continue
            upsert_product(db, url, domain, p)
            result["saved"] += 1
        if result["saved"] % 25 == 0:
            db.commit()
    if result["saved"] == 0:
        return finish("no_product_data", f"{len(urls)} URLs found but no pages had price markup (JSON-LD Product or product_price meta)")
    return finish("ok", f"{result['saved']} products updated this run")
