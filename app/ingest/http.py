"""Polite, safe HTTP fetching: robots.txt (cached per site), SSRF guard,
size/time limits, per-site delay, gzip sitemaps."""
import gzip
import ipaddress
import socket
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "MedFindBot/1.0 (medicine price search; honours robots.txt)"
MAX_BYTES = 3_000_000


def is_public_url(url: str) -> bool:
    try:
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            return False
        return all(ipaddress.ip_address(i[4][0]).is_global for i in socket.getaddrinfo(u.hostname, None))
    except (OSError, ValueError):
        return False


class Fetcher:
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self._robots: dict[str, RobotFileParser | None] = {}
        self.errors: dict[str, str] = {}
        self._last: dict[str, float] = {}

    def robots(self, base: str) -> RobotFileParser | None:
        """None = robots.txt unreachable (treated as 'do not crawl')."""
        if base not in self._robots:
            rp = RobotFileParser()
            try:
                r = httpx.get(base + "/robots.txt", timeout=8, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
                if r.status_code >= 500:
                    rp = None
                    self.errors[base] = f"robots.txt returned HTTP {r.status_code}"
                elif r.status_code >= 400:
                    rp.parse([])  # no robots.txt: everything allowed
                else:
                    rp.parse(r.text.splitlines())
            except httpx.HTTPError as e:
                rp = None
                self.errors[base] = f"{type(e).__name__}: {str(e)[:160]}"
            self._robots[base] = rp
        return self._robots[base]

    def allowed(self, url: str) -> bool:
        u = urlparse(url)
        rp = self.robots(f"{u.scheme}://{u.netloc}")
        return bool(rp and rp.can_fetch(USER_AGENT, url))

    def crawl_delay(self, base: str) -> float:
        rp = self._robots.get(base)
        d = rp.crawl_delay(USER_AGENT) if rp else None
        return max(self.delay, float(d)) if d else self.delay

    def get(self, url: str, accept: str = "text/html") -> str | None:
        """Returns the body, or None if blocked/unavailable."""
        u = urlparse(url)
        base = f"{u.scheme}://{u.netloc}"
        if not is_public_url(url) or not self.allowed(url):
            return None
        wait = self.crawl_delay(base) - (time.time() - self._last.get(u.netloc, 0))
        if wait > 0:
            time.sleep(wait)
        self._last[u.netloc] = time.time()
        try:
            with httpx.stream("GET", url, timeout=12, follow_redirects=False,
                              headers={"User-Agent": USER_AGENT, "Accept": accept, "Accept-Language": "fa,en;q=0.8", "Accept-Encoding": "gzip"}) as r:
                if r.status_code != 200:
                    return None
                buf = b""
                for chunk in r.iter_raw():
                    buf += chunk
                    if len(buf) > MAX_BYTES:
                        break
                enc = r.headers.get("content-encoding", "")
        except httpx.HTTPError:
            return None
        try:
            if enc == "gzip" or buf[:2] == b"\x1f\x8b":
                buf = gzip.decompress(buf)
            elif enc == "br":
                return None
        except OSError:
            return None
        return buf.decode("utf-8", errors="replace")
