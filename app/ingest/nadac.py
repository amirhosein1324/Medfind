"""Real US drug prices from CMS NADAC (National Average Drug Acquisition Cost).

Public weekly data from data.medicaid.gov: what US pharmacies pay per unit
(tablet, capsule, mL, gram...) for ~25k drug products, in USD. It is an
acquisition cost, not a shelf price, and the app says so on the card."""
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from ..models import PricePoint
from .crawler import upsert_product

SOURCE = "medicaid.gov (NADAC)"
UNIT_WORD = {"EA": "unit", "ML": "mL", "GM": "g"}


def _row(r: dict) -> dict | None:
    r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
    ndc, desc = r.get("ndc"), r.get("ndc description")
    try:
        price = Decimal(r.get("nadac_per_unit", ""))
        when = datetime.strptime((r.get("effective_date") or "")[:10], "%m/%d/%Y")
    except (InvalidOperation, ValueError):
        try:
            when = datetime.strptime((r.get("effective_date") or "")[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if not (ndc and desc) or price <= 0:
        return None
    return {"ndc": ndc, "desc": desc, "price": price, "when": when,
            "unit": UNIT_WORD.get(r.get("pricing_unit", "").upper(), r.get("pricing_unit", "").lower() or "unit"),
            "otc": r.get("otc", "").upper() == "Y"}


def import_nadac(db: Session, lines, max_points_per_ndc: int = 12) -> dict:
    """lines: iterable of CSV text lines (streamed). Keeps every distinct price
    seen per NDC (for the history chart) and the latest as the current price."""
    seen: dict[str, dict] = {}
    hist: dict[str, dict] = {}
    rows = bad = 0
    for r in csv.DictReader(lines):
        rows += 1
        x = _row(r)
        if x is None:
            bad += 1
            continue
        h = hist.setdefault(x["ndc"], {})
        h[x["when"]] = x["price"]
        if x["ndc"] not in seen or x["when"] > seen[x["ndc"]]["when"]:
            seen[x["ndc"]] = x
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
    return {"products": saved, "rows_read": rows, "bad_rows": bad, "source": SOURCE}


def find_download_url(client) -> str:
    """Looks up the newest NADAC CSV link in the data.medicaid.gov catalogue."""
    r = client.get("https://data.medicaid.gov/api/1/metastore/schemas/dataset/items?show-reference-ids=false", timeout=60)
    r.raise_for_status()
    best = None
    for d in r.json():
        if "nadac" in (d.get("title") or "").lower() and "national average" in (d.get("title") or "").lower():
            for dist in d.get("distribution", []):
                u = dist.get("downloadURL")
                if u and u.endswith(".csv") and (best is None or d.get("title") > best[0]):
                    best = (d["title"], u)
    if not best:
        raise RuntimeError("No NADAC CSV found in the catalogue; download it from data.medicaid.gov and use --file.")
    return best[1]
