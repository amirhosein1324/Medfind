"""Fill the medicine catalogue from a CSV file.

    python -m scripts.import_catalog --csv drug_list.csv

CSV columns: name, generic_name, brand_name, dosage, form, barcode, manufacturer,
prescription_required (yes/no), aliases (separate with |). Only `name` is required.
Re-running is safe: existing medicines are matched by barcode or name.
"""
import argparse

from app.database import Base, SessionLocal, engine
from app.ingest import catalog


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    a = ap.parse_args()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("CSV:", catalog.from_csv(db, open(a.csv, "rb").read()))
    finally:
        db.close()


if __name__ == "__main__":
    main()
