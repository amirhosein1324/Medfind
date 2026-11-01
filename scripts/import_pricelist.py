"""Import a published price list (CSV/XLSX, English or Persian headers).

    python -m scripts.import_pricelist list.xlsx --source fda.gov.ir
    docker compose cp list.xlsx api:/tmp/list.xlsx
    docker compose exec api python -m scripts.import_pricelist /tmp/list.xlsx --source fda.gov.ir

Columns: a name column (name / نام دارو / نام تجاری), optional generic (نام ژنریک),
and a price column (price / قیمت). Rial vs Toman is read from the header
(قیمت (تومان)); default is Rial, override with --currency IRT."""
import argparse

from app.database import Base, SessionLocal, engine
from app.ingest.pricelist import import_pricelist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--source", required=True, help="site or organisation name shown to users")
    ap.add_argument("--currency", choices=["IRR", "IRT"])
    a = ap.parse_args()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print(import_pricelist(db, a.file, open(a.file, "rb").read(), a.source, a.currency))
    finally:
        db.close()


if __name__ == "__main__":
    main()
