"""Tells you WHY a site can't be crawled from this machine.

    docker compose exec crawler python -m scripts.check_sites
    docker compose exec crawler python -m scripts.check_sites banidaroo.com darooboom.com

For each site it tries robots.txt and the home page twice: as MedFindBot (what the
crawler uses) and as a normal browser, so you can tell a network problem
(DNS/TLS/timeout) from a site that blocks bots (403/connection reset)."""
import socket
import sys

import httpx

from app.ingest.http import USER_AGENT
from app.ingest.sources import get_sources

BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def probe(url: str, ua: str) -> str:
    try:
        r = httpx.get(url, timeout=12, headers={"User-Agent": ua}, follow_redirects=True)
        return f"HTTP {r.status_code} ({len(r.content)} bytes)"
    except httpx.HTTPError as e:
        return f"{type(e).__name__}: {str(e)[:100]}"


def main():
    for d in sys.argv[1:] or get_sources():
        try:
            ip = socket.gethostbyname(d)
        except OSError as e:
            print(f"{d}: DNS FAILED ({e})\n")
            continue
        print(f"{d}  (ip {ip})")
        for label, ua in (("bot    ", USER_AGENT), ("browser", BROWSER)):
            print(f"   {label} robots.txt -> {probe(f'https://{d}/robots.txt', ua)}")
            print(f"   {label} home       -> {probe(f'https://{d}/', ua)}")
        print()


if __name__ == "__main__":
    main()
