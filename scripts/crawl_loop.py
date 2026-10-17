"""Runs the crawler forever, every CRAWL_INTERVAL_HOURS (default 6). Used by the compose `crawler` service."""
import time
import traceback

from app.config import settings
from scripts import crawl

while True:
    try:
        crawl.main.__wrapped__() if hasattr(crawl.main, "__wrapped__") else None
        import argparse, sys
        sys.argv = ["crawl"]
        crawl.main()
    except Exception:
        traceback.print_exc()
    time.sleep(settings.crawl_interval_hours * 3600)
