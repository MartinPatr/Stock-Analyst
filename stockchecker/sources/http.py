"""A shared, polite HTTP session for the HTML-scraping sources.

- Browser-like headers so we are served the same page a person would see.
- A minimum delay between requests to the same host (thread-safe), so a parallel scan
  never hammers one site.
- Retries with exponential backoff on 429/5xx and connection errors.
- 403 / bot-wall responses become :class:`SourceBlocked`, 404 becomes :class:`TickerNotFound`.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from urllib.parse import urlsplit

import requests

from stockchecker.config import get_settings
from stockchecker.sources.base import SourceBlocked, SourceError, TickerNotFound

log = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

# Snippets that only appear in anti-bot interstitials, never in a real quote page.
_BOT_WALL_MARKERS = (
    "pardon our interruption",
    "awswafcookiedomainlist",
    "access denied",
    "are you a robot",
    "captcha",
)

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class PoliteSession:
    def __init__(
        self,
        delay_s: float = 1.0,
        timeout_s: float = 20.0,
        max_retries: int = 3,
        session: requests.Session | None = None,
    ) -> None:
        self.delay_s = delay_s
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._session = session or requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
        self._last_request: dict[str, float] = defaultdict(float)
        self._locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._locks_guard = threading.Lock()

    def _host_lock(self, host: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks[host]

    def _wait_turn(self, host: str) -> None:
        """Block until at least ``delay_s`` has elapsed since the last request to ``host``."""
        with self._host_lock(host):
            elapsed = time.monotonic() - self._last_request[host]
            if elapsed < self.delay_s:
                time.sleep(self.delay_s - elapsed)
            self._last_request[host] = time.monotonic()

    def get(self, url: str, **kwargs) -> requests.Response:
        host = urlsplit(url).netloc
        kwargs.setdefault("timeout", self.timeout_s)
        kwargs.setdefault("allow_redirects", True)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._wait_turn(host)
            try:
                response = self._session.get(url, **kwargs)
            except requests.RequestException as exc:
                last_error = exc
                log.debug("request error for %s (attempt %d): %s", url, attempt + 1, exc)
            else:
                if response.status_code == 404:
                    raise TickerNotFound(f"404 for {url}")
                if response.status_code in (401, 403):
                    raise SourceBlocked(f"{response.status_code} for {url}")
                if response.status_code in RETRY_STATUSES:
                    last_error = SourceError(f"{response.status_code} for {url}")
                elif response.ok:
                    if _looks_like_bot_wall(response):
                        raise SourceBlocked(f"bot challenge served for {url}")
                    return response
                else:
                    raise SourceError(f"unexpected {response.status_code} for {url}")
            if attempt < self.max_retries:
                time.sleep(min(2.0**attempt, 8.0))
        raise SourceError(f"giving up on {url}: {last_error}")


def _looks_like_bot_wall(response: requests.Response) -> bool:
    # Real quote pages are large; interstitials are tiny. Only sniff small bodies.
    if len(response.content) > 20_000:
        return False
    head = response.text[:5000].lower()
    return any(marker in head for marker in _BOT_WALL_MARKERS)


_shared: PoliteSession | None = None
_shared_lock = threading.Lock()


def get_session() -> PoliteSession:
    """Process-wide session so all sources share one per-host rate limiter."""
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = PoliteSession(delay_s=get_settings().request_delay_s)
        return _shared
