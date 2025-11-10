"""Main orchestration logic for the sitemap extraction agent."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List, Set

from bs4 import BeautifulSoup

from .config import AgentConfig, CrawlerConfig
from .excel_loader import load_sites_from_excel
from .http import SitemapFetcher
from .models import SiteEntry, SitemapExtractionResult
from .parlant_adapter import ParlantBridge

logger = logging.getLogger(__name__)


PRODUCT_HINT_RE = re.compile(r"product", re.IGNORECASE)


class SitemapExtractionAgent:
    """Agent responsible for collecting product sitemap URLs."""

    def __init__(
        self,
        crawler_config: CrawlerConfig | None = None,
        agent_config: AgentConfig | None = None,
        progress_path: Path | str | None = None,
    ) -> None:
        self._crawler_config = crawler_config or CrawlerConfig()
        self._agent_config = agent_config or AgentConfig()
        self._progress_path = Path(progress_path) if progress_path else None
        self._bridge = ParlantBridge(self._agent_config)

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
        self._bridge.log(f"Processing {site.brand_name} ({site.site_url})")
        result = SitemapExtractionResult(
            brand_name=site.brand_name,
            site_url=site.site_url,
            sitemap_urls=site.sitemap_urls,
        )
        queue = list(site.sitemap_urls)
        visited: Set[str] = set()
        product_set: Set[str] = set()
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
            product_sitemaps, discovered = self._parse_sitemap_document(
                current, fetch_result.response.text
            )
            for url in product_sitemaps:
                if url not in product_set:
                    product_set.add(url)
                    result.product_sitemaps.append(url)
            for url in discovered:
                if url not in visited and url not in queue:
                    queue.append(url)
        return result

    def _parse_sitemap_document(self, url: str, body: str) -> tuple[List[str], List[str]]:
        """Inspect the sitemap document and return product entries and new sitemap links."""

        soup = BeautifulSoup(body, "xml")
        product_sitemaps: List[str] = []
        discovered: List[str] = []

        if soup.find("sitemapindex"):
            for sitemap in soup.find_all("sitemap"):
                loc_tag = sitemap.find("loc")
                if not loc_tag or not loc_tag.text:
                    continue
                loc = loc_tag.text.strip()
                if PRODUCT_HINT_RE.search(loc):
                    product_sitemaps.append(loc)
                else:
                    discovered.append(loc)
            return product_sitemaps, discovered

        urlset = soup.find("urlset")
        if urlset:
            loc_tags = urlset.find_all("loc")
            if any("/products/" in (loc_tag.text or "") for loc_tag in loc_tags):
                product_sitemaps.append(url)
            elif PRODUCT_HINT_RE.search(url):
                product_sitemaps.append(url)
        return product_sitemaps, discovered

    def _persist_progress(self, result: SitemapExtractionResult) -> None:
        if not self._progress_path:
            return
        record = result.as_dict()
        record_path = self._progress_path
        record_path.parent.mkdir(parents=True, exist_ok=True)
        with record_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
