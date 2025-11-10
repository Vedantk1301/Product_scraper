"""Configuration primitives for the Shopify product scraper."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CrawlerConfig:
    """Settings that control polite crawling behaviour."""

    max_retries: int = 3
    request_timeout: int = 30
    retry_backoff: float = 2.0
    delay_between_requests: float = 1.0
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0 Safari/537.36"
    )


@dataclass
class ProductScraperConfig:
    """Settings that control Shopify specific behaviour."""

    product_json_extension: str = ".json"
