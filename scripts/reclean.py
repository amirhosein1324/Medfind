"""Re-apply title cleaning and drug-name detection to products already in the database.

    docker compose exec api python -m scripts.reclean
"""
from app.database import SessionLocal
from app.ingest.persian import analyze_title, clean_title
from app.models import WebProduct


def main():
    db = SessionLocal()
    changed = n = 0
    try:
        for r in db.query(WebProduct).yield_per(500):
            n += 1
            title = clean_title(r.title)[:500]
            a = analyze_title(title)
            new = (title, a["name_en"][:300] if a["name_en"] else None, a["generic"])
            if new != (r.title, r.title_en, r.generic_en):
                r.title, r.title_en, r.generic_en = new
                changed += 1
            if n % 1000 == 0:
                db.commit()
        db.commit()
    finally:
        db.close()
    print({"checked": n, "changed": changed})


if __name__ == "__main__":
    main()
