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


def test_grouping_product_page_and_history(client):
    db = TestingSessionLocal()
    for dom, price in (("shop-a.ir", "125000"), ("shop-b.ir", "110000")):
        pages = {f"https://{dom}/sm.xml": f"<urlset><url><loc>https://{dom}/product/1</loc></url></urlset>",
                 f"https://{dom}/product/1": ld("قرص پاراستامول ۵۰۰ میلی گرم", price, "IRR")}
        crawler.crawl_source(db, dom, 5, FakeFetcher(pages, f"User-agent: *\nAllow: /\nSitemap: https://{dom}/sm.xml"))
    db.close()
    r = client.get("/api/web/search", params={"q": "paracetamol"}).json()
    g = next(x for x in r["groups"] if x["generic"] == "Paracetamol")
    assert g["shops"] == 2 and float(g["min_price"]) == 11000 and g["offers"][0]["shop"] == "shop-b.ir"
    page = client.get("/api/web/product", params={"key": g["key"]}).json()
    assert len(page["offers"]) == 2 and page["history"] and page["history"][-1]["min_price"] == 11000
    assert client.get("/api/web/product", params={"key": "nothing-here"}).status_code == 404


def test_link_discovery_when_sitemap_has_no_products():
    db = TestingSessionLocal()
    try:
        home = '<a href="/store/">Store</a><a href="/product/77/para">p</a><a href="https://other.ir/product/1">x</a>'
        pages = {"https://links.ir/sitemap.xml": "<urlset><url><loc>https://links.ir/blog/x</loc></url></urlset>",
                 "https://links.ir/": home, "https://links.ir/store/": '<a href="/product/78/ibu">q</a>',
                 "https://links.ir/product/77/para": ld("قرص پاراستامول ۵۰۰ میلی گرم", "100000", "IRR"),
                 "https://links.ir/product/78/ibu": ld("قرص ایبوپروفن ۴۰۰ میلی گرم", "90000", "IRR")}
        r = crawler.crawl_source(db, "links.ir", 10, FakeFetcher(pages, "User-agent: *\nAllow: /\nSitemap: https://links.ir/sitemap.xml"))
        assert r["status"] == "ok" and r["saved"] == 2
    finally:
        db.close()


def test_unreachable_reports_reason():
    db = TestingSessionLocal()
    try:
        f = FakeFetcher({}, None)
        f.errors["https://x.ir"] = "ConnectError: boom"
        r = crawler.crawl_source(db, "x.ir", 5, f)
        assert r["status"] == "unreachable"
        from app.models import CrawlSource
        assert "ConnectError" in db.get(CrawlSource, "x.ir").detail
    finally:
        db.close()


def test_pricelist_import_persian_headers(client):
    from app.ingest.pricelist import import_pricelist
    csv_ = "نام دارو,نام ژنریک,قیمت (ریال)\nقرص ۵۰۰ میلی گرم,پاراستامول,\"۱۲۵,۰۰۰\"\nخالی,,\n".encode("utf-8-sig")
    db = TestingSessionLocal()
    try:
        r = import_pricelist(db, "list.csv", csv_, "fda.example")
        assert r["saved"] == 1 and r["skipped"] == 1 and r["currency"] == "IRR"
    finally:
        db.close()
    g = next(x for x in client.get("/api/web/search", params={"q": "paracetamol"}).json()["groups"] if x["generic"] == "Paracetamol")
    assert float(g["min_price"]) == 12500 and g["offers"][0]["availability"] == "unknown"


def test_admin_import_endpoint_requires_admin(client):
    assert client.post("/api/web/import", files={"file": ("a.csv", b"x")}, data={"source": "s"}).status_code == 401


def test_nadac_import_real_format(client):
    from app.ingest.nadac import import_nadac
    lines = [
        "NDC Description,NDC,NADAC_Per_Unit,Effective_Date,Pricing_Unit,Pharmacy_Type_Indicator,OTC,Explanation_Code,Classification_for_Rate_Setting,Corresponding_Generic_Drug_NADAC_Per_Unit,Corresponding_Generic_Drug_Effective_Date,As_of_Date",
        "ATORVASTATIN 10 MG TABLET,00093505698,0.02345,01/01/2026,EA,C/I,N,1,G,,,01/07/2026",
        "ATORVASTATIN 10 MG TABLET,00093505698,0.02100,01/08/2026,EA,C/I,N,1,G,,,01/14/2026",
        "BAD ROW,,x,notadate,EA,C/I,N,1,G,,,",
    ]
    db = TestingSessionLocal()
    try:
        r = import_nadac(db, lines)
        assert r["products"] == 1 and r["bad_rows"] == 1
    finally:
        db.close()
    g = next(x for x in client.get("/api/web/search", params={"q": "atorvastatin"}).json()["groups"] if x["offers"])
    assert float(g["min_price"]) == 0.021 and g["currency"] == "USD"
