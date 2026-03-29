from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from supply_chain_intel.config import settings
from supply_chain_intel.utils.cache import FileCache


class SECClient:
    BASE_URL = "https://www.sec.gov"

    def __init__(self) -> None:
        self.cache = FileCache("sec")
        self._last_request_ts = 0.0
        self._http = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": settings.sec_user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            follow_redirects=True,
        )

    def _throttle(self) -> None:
        min_interval = 1 / max(settings.sec_rate_limit_per_second, 0.1)
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_ts = time.monotonic()

    def _request_with_backoff(self, url: str) -> httpx.Response:
        attempts = 5
        wait_seconds = 1.5
        last_error: Exception | None = None

        for attempt in range(attempts):
            self._throttle()
            response = self._http.get(url)
            if response.status_code != 429:
                response.raise_for_status()
                return response

            retry_after = response.headers.get("Retry-After")
            sleep_for = float(retry_after) if retry_after else wait_seconds
            time.sleep(sleep_for)
            wait_seconds *= 2
            last_error = httpx.HTTPStatusError(
                "Too Many Requests. Rate limited. Try after a while.",
                request=response.request,
                response=response,
            )

        assert last_error is not None
        raise last_error

    def fetch_text(self, url: str, force_refresh: bool = False) -> str:
        cached = None if force_refresh else self.cache.get_text(url, suffix="txt")
        if cached is not None:
            return cached
        response = self._request_with_backoff(url)
        return self.cache.set_text(url, response.text, suffix="txt").read_text(encoding="utf-8")

    def fetch_json(self, url: str, force_refresh: bool = False) -> dict:
        cached = None if force_refresh else self.cache.get_text(url, suffix="json")
        if cached is not None:
            return json.loads(cached)
        response = self._request_with_backoff(url)
        payload = response.text
        self.cache.set_text(url, payload, suffix="json")
        return response.json()

    def download_filing(self, url: str, target_name: str) -> Path:
        content = self.fetch_text(url)
        target = settings.cache_dir / "filings"
        target.mkdir(parents=True, exist_ok=True)
        path = target / target_name
        path.write_text(content, encoding="utf-8")
        return path
