"""High level orchestration for crawling product sitemaps."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, List, Set
from urllib.parse import urlsplit, urlunsplit

from .config import CrawlerConfig
from .excel_loader import load_sites_from_excel
from .http import SitemapFetcher
from .models import ProductRecord, SiteEntry, SiteScrapeResult
from .sitemap import parse_sitemap_document

logger = logging.getLogger(__name__)


class ProductSitemapCrawler:
    """Crawl the provided product sitemaps and collect product data."""

    def __init__(
        self,
        crawler_config: CrawlerConfig | None = None,
        progress_path: Path | str | None = None,
        max_products: int | None = None,
    ) -> None:
        self._crawler_config = crawler_config or CrawlerConfig()
        self._progress_path = Path(progress_path) if progress_path else None
        self._max_products = max_products

    def run(self, excel_path: Path | str, output_path: Path | str) -> List[SiteScrapeResult]:
        """Execute the crawler on a given Excel workbook."""

        sites = load_sites_from_excel(excel_path)
        fetcher = SitemapFetcher(self._crawler_config)
        results: List[SiteScrapeResult] = []
        try:
            for site in sites:
                result = self._process_site(site, fetcher)
                results.append(result)
                self._persist_progress(result)
        finally:
            fetcher.close()

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps([result.as_dict() for result in results], indent=2),
            encoding="utf-8",
        )
        return results

    def _process_site(self, site: SiteEntry, fetcher: SitemapFetcher) -> SiteScrapeResult:
        logger.info("Processing %s (%s)", site.brand, site.site_url)
        result = SiteScrapeResult(
            brand=site.brand,
            site_url=site.site_url,
            primary_sitemap=site.primary_sitemap,
            product_sitemaps=list(site.product_sitemaps),
            metadata=dict(site.metadata),
        )

        queue: List[str] = list(site.product_sitemaps)
        visited: Set[str] = set()
        product_urls: List[str] = []
        seen_products: Set[str] = set()

        if not queue:
            message = "No product sitemaps provided in the Excel row."
            logger.warning("%s (%s): %s", site.brand, site.site_url, message)
            result.errors.append(message)

        while queue:
            current = queue.pop(0)
            if not current or current in visited:
                continue
            visited.add(current)
            fetch_result = fetcher.get(current)
            result.sitemap_history.append(current)
            if not fetch_result.ok or fetch_result.response is None:
                message = f"Failed to fetch sitemap {current}: {fetch_result.error or 'unknown error'}"
                logger.error(message)
                result.errors.append(message)
                continue
            products, discovered = parse_sitemap_document(current, fetch_result.response.text)
            for url in products:
                if url not in seen_products:
                    seen_products.add(url)
                    product_urls.append(url)
            for url in discovered:
                if url not in visited and url not in queue:
                    queue.append(url)

        logger.info("Collected %s product URLs for %s", len(product_urls), site.brand)
        result.product_urls = product_urls

        for product_url in self._iterate_products(product_urls):
            record = self._fetch_product(fetcher, product_url)
            result.products.append(record)
            if record.error:
                result.errors.append(record.error)
            if self._max_products is not None and len(result.products) >= self._max_products:
                logger.info(
                    "Reached max_products=%s for %s, stopping early",
                    self._max_products,
                    site.brand,
                )
                break

        return result

    def _iterate_products(self, product_urls: Iterable[str]) -> Iterable[str]:
        for url in product_urls:
            yield url

    def _fetch_product(self, fetcher: SitemapFetcher, product_url: str) -> ProductRecord:
        json_url = self._to_json_url(product_url)
        fetch_result = fetcher.get(json_url)
        if not fetch_result.ok or fetch_result.response is None:
            error = f"Failed to fetch product {json_url}: {fetch_result.error or 'unknown error'}"
            logger.error(error)
            return ProductRecord(product_url=product_url, json_url=json_url, error=error)
        try:
            data = fetch_result.response.json()
        except ValueError as exc:
            error = f"Invalid JSON from {json_url}: {exc}"
            logger.error(error)
            return ProductRecord(product_url=product_url, json_url=json_url, error=error)
        return ProductRecord(product_url=product_url, json_url=json_url, data=data)

    def _to_json_url(self, product_url: str) -> str:
        """Convert a product HTML URL into the corresponding JSON endpoint."""

        parsed = urlsplit(product_url)
        path = parsed.path.rstrip("/")
        if not path.endswith(".json"):
            path = f"{path}.json"
        return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))

    def _persist_progress(self, result: SiteScrapeResult) -> None:
        if not self._progress_path:
            return
        record = result.as_dict()
        record_path = self._progress_path
        record_path.parent.mkdir(parents=True, exist_ok=True)
        with record_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
