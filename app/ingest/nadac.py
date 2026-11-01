"""Real US drug prices from CMS NADAC (National Average Drug Acquisition Cost).

Public weekly data from data.medicaid.gov: what US pharmacies pay per unit
(tablet, capsule, mL, gram...) for ~25k drug products, in USD. It is an
acquisition cost, not a shelf price, and the app says so on the card."""
import csv
import io
import re
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from ..models import PricePoint
from .crawler import upsert_product

SOURCE = "medicaid.gov (NADAC)"
UNIT_WORD = {"EA": "unit", "ML": "mL", "GM": "g"}


def _key(k) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (k or "").strip().lower()).strip("_")


def _date(v: str):
    v = (v or "").strip()[:10]
    for f in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(v, f)
        except ValueError:
            pass
    return None


def _row(r: dict) -> dict | None:
    r = {_key(k): (v or "").strip() for k, v in r.items() if k}
    ndc, desc = r.get("ndc"), r.get("ndc_description")
    when = _date(r.get("effective_date"))
    try:
        price = Decimal(r.get("nadac_per_unit", "").replace("$", "").replace(",", "").replace("$", "").replace(",", ""))
    except InvalidOperation:
        return None
    if not (ndc and desc) or when is None or price <= 0:
        return None
    unit = r.get("pricing_unit", "")
    return {"ndc": ndc, "desc": desc, "price": price, "when": when,
            "unit": UNIT_WORD.get(unit.upper(), unit.lower() or "unit"), "otc": r.get("otc", "").upper() == "Y"}


def import_nadac(db: Session, lines, max_points_per_ndc: int = 12) -> dict:
    """lines: iterable of CSV text lines (streamed). Keeps every distinct price
    seen per NDC (for the history chart) and the latest as the current price."""
    seen: dict[str, dict] = {}
    hist: dict[str, dict] = {}
    rows = bad = 0
    sample = None
    sample = None
    for r in csv.DictReader(lines):
        rows += 1
        sample = sample or r
        x = _row(r)
        if x is None:
            bad += 1
            if sample is None:
                sample = dict(list(r.items())[:6])
            continue
        h = hist.setdefault(x["ndc"], {})
        h[x["when"]] = x["price"]
        if x["ndc"] not in seen or x["when"] > seen[x["ndc"]]["when"]:
            seen[x["ndc"]] = x
    if rows and not seen:
        raise ValueError(f"No usable rows. Columns seen: {list(sample)}; first row: {list(sample.values())}")
    saved = 0
    for ndc, x in seen.items():
        url = f"https://data.medicaid.gov/nadac#{ndc}"
        title = f"{x['desc'].title()} (price per {x['unit']})"
        p = upsert_product(db, url, SOURCE, {"title": title, "price": x["price"], "currency": "USD",
                                             "availability": "unknown", "image_url": None})
        if not (p.generic_en or p.title_en):
            p.title_en = x["desc"].title()[:300]
        points = sorted(hist[ndc].items())[-max_points_per_ndc:]
        have = {(pp.seen_at) for pp in db.query(PricePoint).filter(PricePoint.url == url)}
        for when, price in points:
            if when not in have:
                db.add(PricePoint(url=url, price=price, seen_at=when))
        saved += 1
        if saved % 500 == 0:
            db.commit()
    db.commit()
    out = {"products": saved, "rows_read": rows, "bad_rows": bad, "source": SOURCE}
    if saved == 0 and sample:
        out["first_bad_row"] = sample
    return out


def find_download_url(client) -> str:
    """Finds the newest NADAC CSV link anywhere in the data.medicaid.gov catalogue."""
    import re
    r = client.get("https://data.medicaid.gov/api/1/metastore/schemas/dataset/items?show-reference-ids=false", timeout=120)
    r.raise_for_status()
    urls = set(re.findall(r"https://[^\"\s\\]*nadac[^\"\s\\]*\.csv", r.text, flags=re.I))
    urls = {u for u in urls if "national-average" in u.lower() or "nadac-national" in u.lower()} or urls

    def when(u):
        m = re.search(r"(\d{2})-(\d{2})-(\d{4})", u)
        return (int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else (0, 0, 0)

    if not urls:
        raise RuntimeError("No NADAC CSV link found in the catalogue; pass --url or --file.")
    return max(urls, key=when)
