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
    "primary_sitemaps",
}


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
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(
            "Excel workbook is missing required columns: " + ", ".join(sorted(missing))
        )

    sites: List[SiteEntry] = []
    for record in frame.to_dict(orient="records"):
        sitemap_urls = _parse_sitemap_cell(record.get("primary_sitemaps"))
        metadata = {
            key: value
            for key, value in record.items()
            if key not in REQUIRED_COLUMNS and value == value  # filter NaN
        }
        site = SiteEntry(
            brand_name=str(record.get("brand_name", "")).strip(),
            site_url=str(record.get("site_url", "")).strip(),
            sitemap_urls=sitemap_urls,
            metadata=metadata,
        )
        sites.append(site)
    return sites
