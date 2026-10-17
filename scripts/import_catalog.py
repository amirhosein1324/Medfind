"""Fill the medicine catalogue with real data.

    python -m scripts.import_catalog --csv regulator_list.csv      # any country's list
    python -m scripts.import_catalog --openfda --limit 5000        # US FDA NDC directory
    docker compose exec api python -m scripts.import_catalog --openfda

CSV columns: name, generic_name, brand_name, dosage, form, barcode, manufacturer,
prescription_required (yes/no), aliases (separate with |). Only `name` is required.
Re-running is safe: existing medicines are matched by barcode or name.
"""
import argparse

from app.database import Base, SessionLocal, engine
from app.ingest import catalog


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--openfda", action="store_true")
    ap.add_argument("--limit", type=int, default=5000)
    a = ap.parse_args()
    if not (a.csv or a.openfda):
        ap.error("choose --csv FILE and/or --openfda")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if a.csv:
            print("CSV:", catalog.from_csv(db, open(a.csv, "rb").read()))
        if a.openfda:
            print("openFDA:", catalog.from_openfda(db, a.limit))
    finally:
        db.close()


if __name__ == "__main__":
    main()
