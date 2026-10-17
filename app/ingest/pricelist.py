"""Imports an official/published price list (CSV or XLSX) as web products.

Works with English or Persian column headers, e.g. the consumer price lists
that drug regulators publish. Rows become products of a named source site so
they appear in search next to crawled shop prices."""
import re
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from .crawler import upsert_product
from .persian import normalize
from .sheet import SheetError, _read_table

NAME = {"name", "drug", "medicine", "product", "title", "نام", "نام دارو", "نام تجاری", "نام کالا", "نام فرآورده", "شرح دارو", "شرح کالا", "دارو"}
GENERIC = {"generic", "generic name", "نام ژنریک", "نام ژنریک دارو", "نام ژنریک فرآورده", "ژنریک"}
PRICE = {"price", "consumer price", "قیمت", "قیمت مصرف کننده", "قیمت مصرفی", "قیمت (ریال)", "قیمت (تومان)", "قیمت ریال", "قیمت تومان"}


def _h(x) -> str:
    return re.sub(r"\s+", " ", normalize(x).lower()).strip()


def _num(v):
    s = re.sub(r"[^\d.]", "", normalize(v).replace(",", "").replace("٬", ""))
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    return d if d > 0 else None


def import_pricelist(db: Session, filename: str, data: bytes, source: str, currency: str | None = None) -> dict:
    """source: a site/organisation name like 'fda.gov.ir'. Returns counts."""
    table = [r for r in _read_table(filename, data) if any(str(c or "").strip() for c in r)]
    if not table:
        raise SheetError("The file is empty.")
    head = [_h(c) for c in table[0]]
    find = lambda names: next((i for i, h in enumerate(head) if h in {_h(n) for n in names}), None)
    ci_name, ci_gen, ci_price = find(NAME), find(GENERIC), find(PRICE)
    if ci_name is None and ci_gen is None:
        raise SheetError("Couldn't find a medicine name column (try 'name' or 'نام دارو').")
    if ci_price is None:
        raise SheetError("Couldn't find a price column (try 'price' or 'قیمت').")
    cur = (currency or "").upper() or ("IRT" if re.search("تومان|toman", head[ci_price]) else "IRR")
    host = source.strip().lower().removeprefix("https://").removeprefix("http://").strip("/") or "price-list"
    saved = skipped = 0
    for raw in table[1:]:
        cell = lambda i: str(raw[i]).strip() if i is not None and i < len(raw) and raw[i] is not None else ""
        name, generic = cell(ci_name), cell(ci_gen)
        price = _num(cell(ci_price))
        title = " ".join(x for x in (generic, name) if x and x.lower() not in (generic.lower() if x is name else "",)) or name or generic
        if not title or price is None:
            skipped += 1
            continue
        slug = re.sub(r"[^\w]+", "-", normalize(title).lower(), flags=re.U).strip("-")[:120]
        upsert_product(db, f"https://{host}/#{slug}", host,
                       {"title": title, "price": price, "currency": cur, "availability": "unknown", "image_url": None})
        saved += 1
        if saved % 200 == 0:
            db.commit()
    db.commit()
    return {"saved": saved, "skipped": skipped, "currency": cur, "source": host}
