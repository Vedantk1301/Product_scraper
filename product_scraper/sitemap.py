"""Helpers for parsing XML sitemap documents."""

from __future__ import annotations

import logging
from typing import List, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_sitemap_document(url: str, body: str) -> Tuple[List[str], List[str]]:
    """Inspect the sitemap document and return product URLs and nested sitemap links."""

    soup = BeautifulSoup(body, "xml")
    product_urls: List[str] = []
    discovered_sitemaps: List[str] = []

    if soup.find("sitemapindex"):
        for sitemap in soup.find_all("sitemap"):
            loc_tag = sitemap.find("loc")
            if not loc_tag or not loc_tag.text:
                continue
            loc = loc_tag.text.strip()
            if loc:
                discovered_sitemaps.append(loc)
        return product_urls, discovered_sitemaps

    urlset = soup.find("urlset")
    if not urlset:
        logger.debug("Sitemap %s does not contain <urlset> or <sitemapindex>", url)
        return product_urls, discovered_sitemaps

    for loc_tag in urlset.find_all("loc"):
        if loc_tag.text:
            loc = loc_tag.text.strip()
            if loc:
                product_urls.append(loc)
    return product_urls, discovered_sitemaps
