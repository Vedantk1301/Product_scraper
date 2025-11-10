"""Utilities for reading the incoming Excel workbook."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pandas as pd

from .models import SiteEntry


REQUIRED_COLUMNS = {
    "brand_name",
    "site_url",
}

PRODUCT_SITEMAP_COLUMNS = [
    "product_sitemap_urls",
    "product_sitemap_url",
    "product_sitemaps",
]


def _parse_sitemap_cell(value) -> List[str]:
    """Parse a cell that contains one or more sitemap URLs."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            separators = [",", "\n", "|"]
            for sep in separators:
                if sep in stripped:
                    return [item.strip() for item in stripped.split(sep) if item.strip()]
            return [stripped]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(parsed, str):
            return [parsed.strip()]
    return [str(value).strip()]


def load_sites_from_excel(path: Path | str) -> List[SiteEntry]:
    """Load Shopify site entries from an Excel workbook."""

    workbook_path = Path(path)
    if not workbook_path.exists():
        raise FileNotFoundError(workbook_path)

    frame = pd.read_excel(workbook_path)
    columns = set(frame.columns)
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(
            "Excel workbook is missing required columns: " + ", ".join(sorted(missing))
        )

    if PRODUCT_SITEMAP_COLUMNS[0] not in columns:
        # Fall back to legacy column names if provided.
        if not any(column in columns for column in PRODUCT_SITEMAP_COLUMNS[1:]):
            raise ValueError(
                "Excel workbook must include a 'product_sitemap_urls' column (or the "
                "legacy 'product_sitemaps' column)."
            )

    sites: List[SiteEntry] = []
    for record in frame.to_dict(orient="records"):
        product_sitemaps: List[str] = []
        for column in PRODUCT_SITEMAP_COLUMNS:
            if column not in record:
                continue
            product_sitemaps = _parse_sitemap_cell(record.get(column))
            if product_sitemaps:
                break
        metadata = {
            key: value
            for key, value in record.items()
            if key not in REQUIRED_COLUMNS
            and key not in PRODUCT_SITEMAP_COLUMNS
            and value == value  # filter NaN
        }
        site = SiteEntry(
            brand_name=str(record.get("brand_name", "")).strip(),
            site_url=str(record.get("site_url", "")).strip(),
            product_sitemap_urls=product_sitemaps,
            metadata=metadata,
        )
        sites.append(site)
    return sites
