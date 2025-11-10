"""Data models shared across the sitemap extraction agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SiteEntry:
    """Input representation of a Shopify store.

    Attributes
    ----------
    brand_name:
        Human readable brand identifier.
    site_url:
        Public facing home page of the store. Used only for logging.
    sitemap_urls:
        List of primary sitemap URLs provided in the Excel workbook.
    metadata:
        Optional free-form dictionary with additional information from the
        spreadsheet row.
    """

    brand_name: str
    site_url: str
    sitemap_urls: List[str]
    metadata: Dict[str, Optional[str]] = field(default_factory=dict)


@dataclass
class SitemapExtractionResult:
    """Structured output of the sitemap extraction agent."""

    brand_name: str
    site_url: str
    sitemap_urls: List[str]
    product_sitemaps: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        """Serialize the result to a JSON-compatible dictionary."""

        return {
            "brand_name": self.brand_name,
            "site_url": self.site_url,
            "sitemap_urls": list(self.sitemap_urls),
            "product_sitemaps": list(self.product_sitemaps),
            "errors": list(self.errors),
        }
