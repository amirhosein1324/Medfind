"""How good is the data? Counts medicines (groups), how many have 2+ shops, the biggest ones,
and checks that common medicines can be found.

    docker compose exec api python -m scripts.coverage
"""
import collections

from app.database import Base, SessionLocal, engine
from app.ingest import service
from app.models import WebProduct

COMMON = ["پاراستامول", "استامینوفن", "ایبوپروفن", "ویتامین د", "ویتامین سی", "منیزیم", "زینک", "آهن", "کلسیم",
          "امگا 3", "مولتی ویتامین", "ملاتونین", "پروبیوتیک", "شربت سرفه", "قطره", "قرص سرماخوردگی",
          "آموکسی سیلین", "ال کارنیتین", "کوآنزیم", "بیوتین", "ژل", "کرم", "ضد آفتاب", "سرم", "ویتامین ب"]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        groups = collections.defaultdict(set)
        shops = collections.Counter()
        total = 0
        for r in db.query(WebProduct).yield_per(2000):
            total += 1
            shops[r.source_domain] += 1
            groups[service.group_key(r)].add(r.source_domain)
        multi = [k for k, v in groups.items() if len(v) >= 2]
        print(f"products: {total}   shops: {len(shops)}   distinct medicines/groups: {len(groups)}")
        print(f"groups in 2+ shops (real price comparison): {len(multi)} ({100 * len(multi) // max(1, len(groups))}%)")
        print(f"groups in 3+ shops: {sum(1 for v in groups.values() if len(v) >= 3)}")
        print("\nmost compared (shops):")
        for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:15]:
            print(f"  {len(v):2d}  {k}")
        print("\ncommon searches (groups found / of them in 2+ shops):")
        for q in COMMON:
            gs = service.search_groups(db, q, limit=200)
            print(f"  {q:20s} {len(gs):4d} / {sum(1 for g in gs if g['shops'] >= 2):4d}" + ("   <-- nothing" if not gs else ""))
    finally:
        db.close()


if __name__ == "__main__":
    main()
