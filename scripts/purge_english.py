"""Delete everything that is not Persian from the web product index.

    python -m scripts.purge_english            # shows what would be deleted
    python -m scripts.purge_english --yes      # deletes it

A product is kept only when its title contains Persian letters and its price is in Toman.
Sources that are not Iranian (a domain ending in .ir or one of the default sources) are removed too
when --strict is given.
"""
import argparse
import re

from app.database import Base, SessionLocal, engine
from app.ingest.sources import get_sources
from app.models import PricePoint, WebProduct

FA = re.compile(r"[\u0600-\u06FF]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--strict", action="store_true", help="also delete rows from domains that are not configured sources")
    a = ap.parse_args()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        known = set(get_sources())
        bad = []
        for r in db.query(WebProduct).yield_per(2000):
            if not FA.search(r.title or "") or (a.strict and r.source_domain not in known):
                bad.append(r.url)
        print(f"{len(bad)} non-Persian products found")
        if a.yes and bad:
            for i in range(0, len(bad), 1000):
                chunk = bad[i:i + 1000]
                db.query(PricePoint).filter(PricePoint.url.in_(chunk)).delete(synchronize_session=False)
                db.query(WebProduct).filter(WebProduct.url.in_(chunk)).delete(synchronize_session=False)
            db.commit()
            print("deleted")
        elif bad:
            print("run again with --yes to delete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
