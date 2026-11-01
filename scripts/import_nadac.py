"""Load real US drug prices (CMS NADAC, public data) and, optionally, the openFDA catalogue.

    python -m scripts.import_nadac                 # downloads the newest file
    python -m scripts.import_nadac --file nadac.csv
    docker compose exec api python -m scripts.import_nadac
"""
import argparse

import httpx
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.ingest.nadac import find_download_url, import_nadac


def widen_price_columns():
    """Per-unit prices like $0.0234 need 4 decimals (old tables had 2)."""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as c:
        for t, col in (("web_products", "price"), ("price_points", "price")):
            c.execute(text(f"ALTER TABLE {t} ALTER COLUMN {col} TYPE NUMERIC(14,4)"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--url")
    a = ap.parse_args()
    Base.metadata.create_all(bind=engine)
    widen_price_columns()
    db = SessionLocal()
    try:
        if a.file:
            with open(a.file, encoding="utf-8-sig", newline="") as f:
                print(import_nadac(db, f))
            return
        with httpx.Client(follow_redirects=True, headers={"User-Agent": "MedFindBot/1.0"}) as c:
            url = a.url or find_download_url(c)
            print("Downloading", url)
            with c.stream("GET", url, timeout=600) as r:
                r.raise_for_status()
                print(import_nadac(db, r.iter_lines()))
    finally:
        db.close()


if __name__ == "__main__":
    main()
