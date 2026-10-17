"""Pulls product name, price and stock out of a web page using schema.org
structured data (JSON-LD), falling back to Open Graph product meta tags.
Pure functions, no network, so they are easy to test."""
import json
import re
from decimal import Decimal, InvalidOperation

from .persian import normalize

from . import fa

LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
META_RE = re.compile(r'<meta[^>]+>', re.I)
ATTR_RE = re.compile(r'(\w[\w:.-]*)\s*=\s*["\']([^"\']*)["\']')


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _types(node) -> set[str]:
    t = node.get("@type")
    t = t if isinstance(t, list) else [t]
    return {str(x).rsplit("/", 1)[-1].lower() for x in t if x}


def map_availability(value) -> str:
    raw = normalize(value)
    if "ناموجود" in raw.replace(" ", "") or "تمام شد" in raw:
        return "out_of_stock"
    if "موجود" in raw:
        return "available"
    v = raw.rsplit("/", 1)[-1].lower()
    if v in ("instock", "onlineonly", "instoreonly"):
        return "available"
    if v in ("limitedavailability", "presale"):
        return "limited_stock"
    if v in ("outofstock", "soldout", "discontinued"):
        return "out_of_stock"
    return "unknown"


def _price(v):
    if v is None or v == "":
        return None
    v = normalize(fa.digits(str(v)))
    if re.fullmatch(r"[\d,]+", v) and "," in v:  # thousands separators: 1,250,000
        v = v.replace(",", "")
    try:
        d = Decimal(re.sub(r"[^\d.]", "", v.replace(",", ".")) or "x")
        return d if d >= 0 else None
    except InvalidOperation:
        return None


def _first_offer(offers):
    for o in (offers if isinstance(offers, list) else [offers]):
        if isinstance(o, dict):
            return o
    return None


def _image(v):
    if isinstance(v, list):
        v = v[0] if v else None
    if isinstance(v, dict):
        v = v.get("url")
    return v if isinstance(v, str) and v.startswith("http") else None


def extract_products(html: str) -> list[dict]:
    out = []
    for block in LD_RE.findall(html or ""):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for node in _walk(data):
            if "product" not in _types(node) or not node.get("name"):
                continue
            offer = _first_offer(node.get("offers"))
            price = cur = avail = None
            if offer:
                price = _price(offer.get("price", offer.get("lowPrice")))
                cur = offer.get("priceCurrency")
                avail = map_availability(offer.get("availability"))
            out.append({
                "title": str(node["name"]).strip()[:500],
                "price": price,
                "currency": str(cur)[:10] if cur else None,
                "availability": avail or "unknown",
                "image_url": _image(node.get("image")),
            })
    if out:
        return out

    # Fallback: Open Graph product tags
    meta = {}
    for tag in META_RE.findall(html or ""):
        a = dict(ATTR_RE.findall(tag))
        key = a.get("property") or a.get("name")
        if key and "content" in a:
            meta[key.lower()] = a["content"]
    # Torob/Emalls-style tags many Iranian shops publish
    if meta.get("product_name") and meta.get("product_price"):
        return [{
            "title": meta["product_name"].strip()[:500],
            "price": _price(meta["product_price"]),
            "currency": meta.get("product_currency") or None,
            "availability": map_availability(meta.get("availability")),
            "image_url": None,
        }]
    price = _price(meta.get("product:price:amount") or meta.get("og:price:amount"))
    if meta.get("og:title") and price is not None:
        return [{
            "title": meta["og:title"].strip()[:500],
            "price": price,
            "currency": (meta.get("product:price:currency") or meta.get("og:price:currency") or "")[:10] or None,
            "availability": map_availability(meta.get("product:availability") or meta.get("og:availability")),
            "image_url": meta.get("og:image") if str(meta.get("og:image", "")).startswith("http") else None,
        }]
    return []
