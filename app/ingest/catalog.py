"""Imports medicines into the catalogue from a CSV file (for example a regulator or published drug list)."""
import csv
import io
import json
import time

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Medicine, MedicineAlias


def upsert_medicine(db: Session, *, name, generic=None, brand=None, dosage=None, form=None,
                    barcode=None, rx=False, manufacturer=None, aliases=()):
    """Create the medicine unless one with the same barcode or name exists.
    Returns (medicine, created)."""
    name = (name or "").strip()[:200]
    if not name:
        return None, False
    m = None
    if barcode:
        m = db.query(Medicine).filter(Medicine.barcode == barcode).first()
    if m is None:
        m = db.query(Medicine).filter(func.lower(Medicine.name) == name.lower()).first()
    created = m is None
    if created:
        m = Medicine(name=name, generic_name=generic, brand_name=brand, dosage=dosage, form=form,
                     barcode=barcode or None, manufacturer=manufacturer, prescription_required=bool(rx))
        db.add(m)
        db.flush()
    have = {a.alias_name.lower() for a in m.aliases} | {m.name.lower()}
    for a in aliases:
        a = (a or "").strip()[:200]
        if a and a.lower() not in have:
            db.add(MedicineAlias(medicine_id=m.medicine_id, alias_name=a, alias_type="import"))
            have.add(a.lower())
    return m, created


def _truthy(v) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "y", "rx", "prescription")


def from_csv(db: Session, data: bytes) -> dict:
    """Columns (any order, extras ignored): name, generic_name, brand_name, dosage, form,
    barcode, manufacturer, prescription_required, aliases (separated by | )."""
    text = data.decode("utf-8-sig", errors="replace")
    stats = {"created": 0, "existing": 0, "skipped": 0}
    for r in csv.DictReader(io.StringIO(text)):
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        m, created = upsert_medicine(
            db, name=r.get("name"), generic=r.get("generic_name") or None, brand=r.get("brand_name") or None,
            dosage=r.get("dosage") or None, form=r.get("form") or None, barcode=r.get("barcode") or None,
            manufacturer=r.get("manufacturer") or None, rx=_truthy(r.get("prescription_required")),
            aliases=[a for a in r.get("aliases", "").split("|") if a])
        stats["skipped" if m is None else "created" if created else "existing"] += 1
    db.commit()
    return stats
