"""Data models shared across the sitemap extraction agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SiteEntry:
    """Input representation of a Shopify store.

    Attributes
    ----------
    brand_name:
        Human readable brand identifier.
    site_url:
        Public facing home page of the store. Used only for logging.
    product_sitemap_urls:
        Standardized list of product sitemap URLs supplied by the operator.
    metadata:
        Optional free-form dictionary with additional information from the
        spreadsheet row.
    """

    brand_name: str
    site_url: str
    product_sitemap_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Optional[str]] = field(default_factory=dict)


@dataclass
class SitemapExtractionResult:
    """Structured output of the sitemap extraction agent."""

    brand_name: str
    site_url: str
    product_sitemaps: List[str] = field(default_factory=list)
    product_urls: List[str] = field(default_factory=list)
    products: List["ProductRecord"] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        """Serialize the result to a JSON-compatible dictionary."""

        return {
            "brand_name": self.brand_name,
            "site_url": self.site_url,
            "product_sitemaps": list(self.product_sitemaps),
            "product_urls": list(self.product_urls),
            "products": [product.as_dict() for product in self.products],
            "errors": list(self.errors),
        }


@dataclass
class ProductRecord:
    """Structured representation of an individual Shopify product payload."""

    product_url: str
    json_url: Optional[str]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "product_url": self.product_url,
            "json_url": self.json_url,
            "data": self.data,
            "error": self.error,
        }
