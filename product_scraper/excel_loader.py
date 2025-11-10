"""Utilities for reading the incoming Excel workbook."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pandas as pd

from .models import SiteEntry


REQUIRED_COLUMNS = {
    "brand",
    "url",
    "primary_sitemap",
    "product_sitemaps",
}


def _parse_list_cell(value) -> List[str]:
    """Parse a cell that contains one or more URLs."""

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
            separators = ["\n", ",", "|"]
            for sep in separators:
                if sep in stripped:
                    return [item.strip() for item in stripped.split(sep) if item.strip()]
            return [stripped]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(parsed, str):
            return [parsed.strip()]
    return [str(value).strip()]


def _normalise_metadata(value):
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value)


def load_sites_from_excel(path: Path | str) -> List[SiteEntry]:
    """Load site entries from an Excel workbook."""

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
        product_sitemaps = _parse_list_cell(record.get("product_sitemaps"))
        primary_candidates = _parse_list_cell(record.get("primary_sitemap"))
        primary_sitemap = primary_candidates[0] if primary_candidates else None
        metadata = {
            key: _normalise_metadata(value)
            for key, value in record.items()
            if key not in REQUIRED_COLUMNS and value == value  # filter NaN
        }
        site = SiteEntry(
            brand=str(record.get("brand", "")).strip(),
            site_url=str(record.get("url", "")).strip(),
            primary_sitemap=primary_sitemap,
            product_sitemaps=product_sitemaps,
            metadata=metadata,
        )
        sites.append(site)
    return sites
