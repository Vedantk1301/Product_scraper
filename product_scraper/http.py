"""HTTP helper utilities for polite sitemap fetching."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests
from requests import Response

from .config import CrawlerConfig


logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    url: str
    response: Optional[Response]
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.response is not None and self.error is None


class SitemapFetcher:
    """Wrapper around :mod:`requests` that adds retry handling."""

    def __init__(self, config: CrawlerConfig):
        self._config = config
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": config.user_agent})

    def get(self, url: str) -> FetchResult:
        """Fetch the given URL with retry and polite delays."""

        attempts = 0
        backoff = self._config.retry_backoff
        last_error: Optional[str] = None
        while attempts < self._config.max_retries:
            if attempts:
                delay = backoff**attempts
                logger.debug("Sleeping %s seconds before retry", delay)
                time.sleep(delay)
            attempts += 1
            try:
                logger.debug("Requesting %s", url)
                response = self._session.get(url, timeout=self._config.request_timeout)
                if response.status_code == 429:
                    logger.warning("Received 429 from %s, backing off", url)
                    time.sleep(backoff**attempts)
                    continue
                response.raise_for_status()
                time.sleep(self._config.delay_between_requests)
                return FetchResult(url=url, response=response)
            except requests.RequestException as exc:
                logger.warning("Attempt %s failed for %s: %s", attempts, url, exc)
                last_error = str(exc)
        return FetchResult(url=url, response=None, error=last_error)

    def close(self) -> None:
        self._session.close()
