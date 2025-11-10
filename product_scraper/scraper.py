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
        product_url_output: Path | str | None = None,
    ) -> None:
        self._crawler_config = crawler_config or CrawlerConfig()
        self._progress_path = Path(progress_path) if progress_path else None
        self._max_products = max_products
        self._product_url_output = Path(product_url_output) if product_url_output else None

    def run(self, excel_path: Path | str, output_path: Path | str) -> List[SiteScrapeResult]:
        """Execute the crawler on a given Excel workbook."""

        sites = load_sites_from_excel(excel_path)
        fetcher = SitemapFetcher(self._crawler_config)
        results: List[SiteScrapeResult] = []
        if self._product_url_output:
            output_path = self._product_url_output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                output_path.unlink()
            except FileNotFoundError:
                pass
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
        self._persist_product_urls(result)

        total_products = len(product_urls)
        if total_products:
            logger.info("Fetching product details for %s items from %s", total_products, site.brand)

        for index, product_url in enumerate(self._iterate_products(product_urls), start=1):
            logger.debug("[%s] Fetching product %s/%s: %s", site.brand, index, total_products, product_url)
            if index == 1 or index == total_products or index % 50 == 0:
                logger.info(
                    "[%s] Progress: %s/%s products", site.brand, index, total_products
                )
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
            parsed = urlsplit(url)
            if not parsed.path or parsed.path == "/":
                logger.debug("Skipping URL with empty path: %s", url)
                continue
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

    def _persist_product_urls(self, result: SiteScrapeResult) -> None:
        if not self._product_url_output:
            return
        payload = {
            "brand": result.brand,
            "site_url": result.site_url,
            "product_urls": list(result.product_urls),
        }
        output_path = self._product_url_output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
