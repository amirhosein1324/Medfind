"""Querying the web product index (products crawled from Iranian pharmacy websites)."""
from datetime import datetime, timedelta
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import PricePoint, WebProduct
from . import fuzzy
from .persian import analyze_title, fa_form, fa_generic, fa_strength, normalize, search_terms

_RANK = {"available": 0, "limited_stock": 1, "unknown": 2, "out_of_stock": 3}


def norm_query(q: str) -> str:
    return normalize(q).lower()[:255]


def search_local_ex(db: Session, q: str, limit: int = 80) -> tuple[list[WebProduct], bool]:
    """Returns (rows, fuzzy). Exact/substring matches first; if there are almost none,
    close spellings ('paracetmol') are added and fuzzy is True."""
    conds = []
    for t in search_terms(q):
        like = f"%{t}%"
        conds += [WebProduct.title.ilike(like), WebProduct.title_en.ilike(like), WebProduct.generic_en.ilike(like)]
    rows = db.query(WebProduct).filter(or_(*conds)).limit(400).all() if conds else []
    rows.sort(key=lambda r: (_RANK.get(r.availability, 9), r.price is None, r.price or 0))
    if len(rows) >= 3:
        return rows[:limit], False
    seen = {r.product_id for r in rows}
    extra = []
    for r in fuzzy.similar(db, WebProduct, ("title_en", "generic_en", "title"), norm_query(q)):
        if r.product_id not in seen:
            extra.append(r)
            seen.add(r.product_id)
    return (rows + extra)[:limit], bool(extra)


def search_local(db: Session, q: str, limit: int = 80) -> list[WebProduct]:
    return search_local_ex(db, q, limit)[0]


# ---------------------------------------------------------------- grouping
def _slug(t: str) -> str:
    return re.sub(r"[^\w]+", "-", normalize(t).lower(), flags=re.U).strip("-")[:90]


_NOISE = {"قیمت", "خرید", "عدد", "عددی", "بسته", "بسته‌ای", "مدل", "و", "با", "برای", "از", "در", "به", "اصل", "اورجینال",
          "جدید", "ارسال", "رایگان", "محصول", "برند", "نوع", "تایی", "تای", "حاوی", "مخصوص", "the", "of", "and", "for"}
_UNITS = [("میلی‌?\\s?گرم", "mg"), ("میکروگرم", "mcg"), ("میلی‌?\\s?لیتر", "ml"), ("گرم", "g"), ("کیلوگرم", "kg"), ("لیتر", "l")]


def title_key(title: str) -> str:
    """Fallback key for products whose ingredient is unknown: the same words in any order, digits and units unified,
    sales wording dropped. 'امگا ۳ ... ۶۰ عددی کپسول' and 'کپسول امگا 3 ... 60 عدد' get the same key."""
    t = normalize(title).lower()
    for pat, unit in _UNITS:
        t = re.sub(r"(\d)\s*" + pat, r"\1" + unit, t)
    toks = {w for w in re.split(r"[^\w]+", t, flags=re.U) if w and w not in _NOISE and not (len(w) == 1 and not w.isdigit())}
    if not toks:
        return _slug(title)
    first = max(toks, key=lambda w: (len(w), w))      # lookup word first (see get_group), the rest sorted
    return "-".join([first] + sorted(toks - {first}))[:120]


def group_key(r: WebProduct) -> str:
    """Same medicine, strength and form on different shops -> same key."""
    a = analyze_title(r.title)
    if a["generic"]:
        return _slug(" ".join(x for x in (a["generic"], a["strength"], a["form"]) if x))
    return title_key(r.title)


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
    a = analyze_title(first.title)
    generic_fa = fa_generic(next((r.generic_en for r in rows if r.generic_en), None))
    form_fa, strength_fa = fa_form(a["form"]), fa_strength(a["strength"])
    persian = [r.title for r in rows if re.search(r"[\u0600-\u06FF]", r.title)]
    # Persian display name, e.g. "قرص پاراستامول 500 میلی‌گرم"; otherwise the shortest shop title
    name = " ".join(x for x in (form_fa, generic_fa, strength_fa) if x) if generic_fa else (min(persian, key=len) if persian else first.title)
    return {
        "strength": strength_fa, "form": form_fa, "price_unit": None,
        "offer_count": len(offers), "cheapest_shop": offers[0]["shop"] if offers else None,
        "key": key, "name": name, "title_fa": None,
        "generic": generic_fa,
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
