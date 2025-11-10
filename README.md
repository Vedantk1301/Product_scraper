# Product Scraper

This repository provides a light-weight command line tool that consumes an Excel
workbook describing Shopify stores and crawls the provided product sitemap
URLs. The crawler respects rate limits, expands sitemap indexes, and downloads
the associated product JSON payloads for each product URL.

## Project layout

- `product_scraper/` – Core logic for parsing the Excel workbook, fetching
  sitemaps, and collecting product JSON responses.
- `run_product_scraper.py` – Command line entry point for the crawler.
- `agentic_crawler_123.ipynb` – Notebook with reference experiments on polite
  crawling (kept for historical context).

## Requirements

The crawler depends on the following Python packages:

- `pandas`
- `requests`
- `beautifulsoup4`

Install them with pip:

```bash
pip install -r requirements.txt
```

## Excel format

Prepare an Excel workbook with the following columns:

- `brand` – Human readable brand identifier.
- `url` – Public facing home page of the store.
- `primary_sitemap` – Optional reference to the primary sitemap. If multiple
  values are provided use JSON, comma, pipe, or newline separators; the first
  value will be used.
- `product_sitemaps` – One or more product sitemap URLs. Accepts JSON arrays,
  comma separated strings, newline separated strings, or Excel array values.

Additional columns are preserved and emitted in the output metadata field.

## Usage

```bash
python run_product_scraper.py stores.xlsx output.json --progress logs/progress.jsonl --delay 2
```

The resulting JSON file will contain an entry per brand with the collected
product URLs, the downloaded product payloads, and any errors encountered during
crawling. Progress snapshots are written to the optional JSONL file so that
long-running sessions can be resumed or inspected.

## Respectful crawling

The crawler uses a configurable delay between requests, exponential backoff on
errors, and a custom user agent. Adjust these settings using the command line
flags described above to comply with each store's crawling policy.
