"""Data models shared across the product sitemap crawler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SiteEntry:
    """Input representation of a store provided in the Excel sheet."""

    brand: str
    site_url: str
    primary_sitemap: Optional[str]
    product_sitemaps: List[str]
    metadata: Dict[str, Optional[str]] = field(default_factory=dict)


@dataclass
class ProductRecord:
    """Represents a single product response."""

    product_url: str
    json_url: str
    data: Optional[dict] = None
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        return {
            "product_url": self.product_url,
            "json_url": self.json_url,
            "data": self.data,
            "error": self.error,
        }


@dataclass
class SiteScrapeResult:
    """Structured output of the product sitemap crawler."""

    brand: str
    site_url: str
    primary_sitemap: Optional[str]
    product_sitemaps: List[str]
    metadata: Dict[str, Optional[str]] = field(default_factory=dict)
    sitemap_history: List[str] = field(default_factory=list)
    product_urls: List[str] = field(default_factory=list)
    products: List[ProductRecord] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {
            "brand": self.brand,
            "site_url": self.site_url,
            "primary_sitemap": self.primary_sitemap,
            "product_sitemaps": list(self.product_sitemaps),
            "metadata": dict(self.metadata),
            "sitemap_history": list(self.sitemap_history),
            "product_urls": list(self.product_urls),
            "products": [record.as_dict() for record in self.products],
            "errors": list(self.errors),
        }
