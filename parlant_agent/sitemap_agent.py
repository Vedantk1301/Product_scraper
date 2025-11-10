"""Main orchestration logic for extracting Shopify product data."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List, Set, Tuple
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

from .config import CrawlerConfig, ProductScraperConfig
from .excel_loader import load_sites_from_excel
from .http import SitemapFetcher
from .models import ProductRecord, SiteEntry, SitemapExtractionResult

logger = logging.getLogger(__name__)


PRODUCT_HINT_RE = re.compile(r"product", re.IGNORECASE)


class SitemapExtractionAgent:
    """Agent responsible for collecting product sitemap URLs."""

    def __init__(
        self,
        crawler_config: CrawlerConfig | None = None,
        scraper_config: ProductScraperConfig | None = None,
        progress_path: Path | str | None = None,
    ) -> None:
        self._crawler_config = crawler_config or CrawlerConfig()
        self._scraper_config = scraper_config or ProductScraperConfig()
        self._progress_path = Path(progress_path) if progress_path else None

    def run(self, excel_path: Path | str, output_path: Path | str) -> List[SitemapExtractionResult]:
        """Execute the agent on a given Excel workbook."""

        sites = load_sites_from_excel(excel_path)
        fetcher = SitemapFetcher(self._crawler_config)
        results: List[SitemapExtractionResult] = []
        try:
            for site in sites:
                result = self._process_site(site, fetcher)
                results.append(result)
                self._persist_progress(result)
        finally:
            fetcher.close()

        output_file = Path(output_path)
        output_file.write_text(
            json.dumps([result.as_dict() for result in results], indent=2),
            encoding="utf-8",
        )
        return results

    def _process_site(self, site: SiteEntry, fetcher: SitemapFetcher) -> SitemapExtractionResult:
        logger.info("Processing %s (%s)", site.brand_name, site.site_url)
        result = SitemapExtractionResult(
            brand_name=site.brand_name,
            site_url=site.site_url,
        )
        queue = []
        visited: Set[str] = set()
        product_set: Set[str] = set()
        product_urls_seen: Set[str] = set()
        for product_sitemap in site.product_sitemap_urls:
            if not product_sitemap:
                continue
            if product_sitemap not in product_set:
                product_set.add(product_sitemap)
                result.product_sitemaps.append(product_sitemap)
            if product_sitemap not in queue:
                queue.append(product_sitemap)
        if not queue:
            message = "No product sitemap URLs supplied for this store"
            logger.warning("%s: %s", site.brand_name, message)
            result.errors.append(message)
            return result
        while queue:
            current = queue.pop(0)
            if not current or current in visited:
                continue
            visited.add(current)
            fetch_result = fetcher.get(current)
            if not fetch_result.ok:
                message = f"Failed to fetch {current}: {fetch_result.error}"
                logger.error(message)
                result.errors.append(message)
                continue
            product_sitemaps, product_urls = self._parse_sitemap_document(
                current, fetch_result.response.text
            )
            for url in product_sitemaps:
                if url not in product_set:
                    product_set.add(url)
                    result.product_sitemaps.append(url)
                if url not in visited and url not in queue:
                    queue.append(url)
            for url in product_urls:
                if url not in product_urls_seen:
                    product_urls_seen.add(url)
                    result.product_urls.append(url)
        for product_url in result.product_urls:
            record = self._fetch_product_payload(product_url, fetcher)
            if record.error:
                result.errors.append(record.error)
            result.products.append(record)
        return result

    def _parse_sitemap_document(self, url: str, body: str) -> Tuple[List[str], List[str]]:
        """Inspect a sitemap document and return product sitemap and product URLs."""

        soup = BeautifulSoup(body, "xml")
        product_sitemaps: List[str] = []
        product_urls: List[str] = []

        if soup.find("sitemapindex"):
            for sitemap in soup.find_all("sitemap"):
                loc_tag = sitemap.find("loc")
                if not loc_tag or not loc_tag.text:
                    continue
                loc = loc_tag.text.strip()
                if PRODUCT_HINT_RE.search(loc):
                    product_sitemaps.append(loc)
            return product_sitemaps, product_urls

        urlset = soup.find("urlset")
        if urlset:
            for url_tag in urlset.find_all("url"):
                loc_tag = url_tag.find("loc")
                if not loc_tag or not loc_tag.text:
                    continue
                loc = loc_tag.text.strip()
                if not loc:
                    continue
                if "/products/" in loc:
                    product_urls.append(loc)
            if not product_urls and PRODUCT_HINT_RE.search(url):
                product_sitemaps.append(url)
        return product_sitemaps, product_urls

    def _build_product_json_url(self, product_url: str) -> str | None:
        parsed = urlparse(product_url)
        if not parsed.netloc:
            return None
        path = parsed.path.rstrip("/")
        if not path:
            return None
        segments = [segment for segment in path.split("/") if segment]
        if "products" not in segments:
            return None
        first_product_index = segments.index("products")
        tail = segments[first_product_index + 1 :]
        if not tail:
            return None
        handle = "/".join(tail)
        json_path = f"/products/{handle}{self._scraper_config.product_json_extension}"
        scheme = parsed.scheme or "https"
        return urlunparse((scheme, parsed.netloc, json_path, "", "", ""))

    def _fetch_product_payload(self, product_url: str, fetcher: SitemapFetcher) -> ProductRecord:
        json_url = self._build_product_json_url(product_url)
        if not json_url:
            message = f"Unable to derive Shopify JSON endpoint for {product_url}"
            logger.warning(message)
            return ProductRecord(product_url=product_url, json_url=None, error=message)
        fetch_result = fetcher.get(json_url)
        if not fetch_result.ok or not fetch_result.response:
            message = f"Failed to fetch {json_url}: {fetch_result.error or 'unknown error'}"
            logger.error(message)
            return ProductRecord(product_url=product_url, json_url=json_url, error=message)
        try:
            data = fetch_result.response.json()
        except ValueError as exc:
            message = f"Failed to decode JSON for {json_url}: {exc}"
            logger.error(message)
            return ProductRecord(product_url=product_url, json_url=json_url, error=message)
        return ProductRecord(product_url=product_url, json_url=json_url, data=data)

    def _persist_progress(self, result: SitemapExtractionResult) -> None:
        if not self._progress_path:
            return
        record = result.as_dict()
        record_path = self._progress_path
        record_path.parent.mkdir(parents=True, exist_ok=True)
        with record_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
