import json
from urllib.robotparser import RobotFileParser

from app.ingest import crawler, extract, persian, service
from app.ingest.http import Fetcher, is_public_url
from tests.conftest import TestingSessionLocal


def ld(name, price, cur="IRR", avail="https://schema.org/InStock"):
    return '<script type="application/ld+json">%s</script>' % json.dumps({
        "@context": "https://schema.org", "@type": "Product", "name": name,
        "offers": {"@type": "Offer", "price": price, "priceCurrency": cur, "availability": avail}})


class FakeFetcher(Fetcher):
    def __init__(self, pages, robots="User-agent: *\nAllow: /\nSitemap: https://shop.ir/sm.xml"):
        super().__init__(delay=0)
        self.pages = pages
        self.rp = None if robots is None else RobotFileParser()
        if self.rp is not None:
            self.rp.parse(robots.splitlines())

    def robots(self, base):
        return self.rp

    def get(self, url, accept="text/html"):
        return self.pages.get(url)


SITEMAP = "<urlset><url><loc>https://shop.ir/product/1</loc></url><url><loc>https://shop.ir/product/2</loc></url><url><loc>https://shop.ir/about</loc></url></urlset>"
PAGES = {
    "https://shop.ir/sm.xml": SITEMAP,
    "https://shop.ir/product/1": ld("قرص پاراستامول ۵۰۰ میلی گرم", "۱۲٬۵۰۰۰", "IRR"),
    "https://shop.ir/product/2": '<meta name="product_name" content="Ibuprofen 400mg tablet"><meta name="product_price" content="85000"><meta name="availability" content="ناموجود">',
}


def test_persian_analysis_and_terms():
    a = persian.analyze_title("شربت آموکسی‌سیلین ۲۵۰ میلی‌گرم")
    assert a["name_en"] == "Amoxicillin 250mg Syrup"
    assert persian.normalize("۱۲٬۵۰۰") == "12,500"
    assert "پاراستامول" in persian.search_terms("Paracetamol") and "paracetamol" in persian.search_terms("پاراستامول")
    assert persian.to_toman(125000, "IRR") == (12500, "IRT")


def test_extract_iranian_markup():
    p = extract.extract_products(PAGES["https://shop.ir/product/2"])[0]
    assert float(p["price"]) == 85000 and p["availability"] == "out_of_stock"
    p = extract.extract_products(ld("X", "1,250,000", "IRR"))[0]
    assert float(p["price"]) == 1250000


def test_crawl_source_saves_and_converts():
    db = TestingSessionLocal()
    try:
        pages = dict(PAGES, **{"https://shop.ir/product/1": ld("قرص پاراستامول ۵۰۰ میلی گرم", "125000", "IRR")})
        r = crawler.crawl_source(db, "shop.ir", 10, FakeFetcher(pages))
        assert r["status"] == "ok" and r["saved"] == 2 and r["urls"] == 2  # /about filtered out
        rows = {x.generic_en: x for x in service.search_local(db, "paracetamol")}
        p = rows["Paracetamol"]
        assert p.title_en == "Paracetamol 500mg Tablet" and float(p.price) == 12500 and p.currency == "IRT"
        assert service.search_local(db, "پاراستامول")  # Persian finds it too
        assert service.search_local(db, "ibuprofen")[0].availability == "out_of_stock"
        crawler.crawl_source(db, "shop.ir", 10, FakeFetcher(pages))  # re-run updates, no duplicates
        assert len(service.search_local(db, "paracetamol")) == 1
    finally:
        db.close()


def test_crawl_respects_robots_and_reports_status():
    db = TestingSessionLocal()
    try:
        assert crawler.crawl_source(db, "closed.ir", 5, FakeFetcher({}, "User-agent: *\nDisallow: /"))["status"] == "blocked_by_robots"
        assert crawler.crawl_source(db, "down.ir", 5, FakeFetcher({}, None))["status"] == "unreachable"
        assert crawler.crawl_source(db, "nomap.ir", 5, FakeFetcher({}, "User-agent: *\nAllow: /"))["status"] == "no_sitemap"
        pages = {"https://bare.ir/sitemap.xml": "<urlset><url><loc>https://bare.ir/product/1</loc></url></urlset>", "https://bare.ir/product/1": "<html>no markup</html>"}
        assert crawler.crawl_source(db, "bare.ir", 5, FakeFetcher(pages, "User-agent: *\nAllow: /"))["status"] == "no_product_data"
    finally:
        db.close()


def test_private_urls_blocked():
    for u in ("http://127.0.0.1/x", "http://localhost/", "file:///etc/passwd", "http://169.254.169.254/"):
        assert not is_public_url(u)


def test_web_search_endpoint_and_admin_sources(client, monkeypatch):
    assert client.get("/api/web/search", params={"q": "paracetamol"}).json()["enabled"] is False
    db = TestingSessionLocal()
    crawler.crawl_source(db, "shop.ir", 10, FakeFetcher(PAGES)); db.close()
    r = client.get("/api/web/search", params={"q": "Paracetamol"}).json()
    assert r["enabled"] and r["items"][0]["source_domain"] == "shop.ir" and r["items"][0]["currency"] == "IRT"
    assert client.get("/api/web/search", params={"q": "پاراستامول"}).json()["items"]
    assert client.get("/api/web/sources").status_code == 401
