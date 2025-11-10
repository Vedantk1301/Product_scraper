"""Core modules for the product sitemap scraping pipeline."""

from .config import CrawlerConfig
from .excel_loader import load_sites_from_excel
from .models import ProductRecord, SiteEntry, SiteScrapeResult
from .scraper import ProductSitemapCrawler

__all__ = [
    "CrawlerConfig",
    "ProductRecord",
    "ProductSitemapCrawler",
    "SiteEntry",
    "SiteScrapeResult",
    "load_sites_from_excel",
]
