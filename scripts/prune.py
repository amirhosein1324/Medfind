"""Remove old or sold-out products from the database for good (searches already hide them).

    python -m scripts.prune --days 30                 # show what would go
    python -m scripts.prune --days 30 --unavailable --yes
        --days N        products not re-confirmed by the crawler for N days
        --unavailable   products the shop marks as out of stock
        --yes           really delete (their price history goes too)
"""
import argparse
from datetime import datetime, timedelta

from app.database import Base, SessionLocal, engine
from app.models import PricePoint, WebProduct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=0)
    ap.add_argument("--unavailable", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    if not a.days and not a.unavailable:
        ap.error("give --days N and/or --unavailable")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        conds = []
        if a.days:
            conds.append(WebProduct.fetched_at < datetime.utcnow() - timedelta(days=a.days))
        if a.unavailable:
            conds.append(WebProduct.availability == "out_of_stock")
        from sqlalchemy import or_
        urls = [u for (u,) in db.query(WebProduct.url).filter(or_(*conds)).all()]
        total = db.query(WebProduct).count()
        print(f"{len(urls)} of {total} products match")
        if a.yes and urls:
            for i in range(0, len(urls), 1000):
                chunk = urls[i:i + 1000]
                db.query(PricePoint).filter(PricePoint.url.in_(chunk)).delete(synchronize_session=False)
                db.query(WebProduct).filter(WebProduct.url.in_(chunk)).delete(synchronize_session=False)
            db.commit()
            print("deleted")
        elif urls:
            print("run again with --yes to delete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
