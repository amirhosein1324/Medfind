"""Crawl Iranian online pharmacies and fill the web product index.

    python -m scripts.crawl                        # one pass over all sources
    python -m scripts.crawl --domain banidaroo.com --max-pages 50
    python -m scripts.crawl --loop --every 6       # keep running, every 6 hours (Docker `crawler` service)

Sources: CRAWL_SOURCES=a.com,b.com (default list in app/ingest/sources.py).
Each site is crawled only if its robots.txt allows it; results per site are
shown in Admin > Data sources.
"""
import argparse
import logging
import time

from app.database import Base, SessionLocal, engine
from app.ingest.crawler import crawl_source
from app.ingest.sources import get_sources


def run_once(domains, max_pages):
    for d in domains:
        db = SessionLocal()
        try:
            r = crawl_source(db, d, max_pages)
            print(f"{d}: {r['status']} (urls={r['urls']}, saved={r['saved']})", flush=True)
        except Exception as e:  # one bad site must not stop the rest
            db.rollback()
            print(f"{d}: error {e}", flush=True)
        finally:
            db.close()


def main():
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", action="append")
    ap.add_argument("--max-pages", type=int, default=300)
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--every", type=float, default=6, help="hours between passes with --loop")
    a = ap.parse_args()
    Base.metadata.create_all(bind=engine)
    domains = a.domain or get_sources()
    while True:
        run_once(domains, a.max_pages)
        if not a.loop:
            break
        time.sleep(a.every * 3600)


if __name__ == "__main__":
    main()
