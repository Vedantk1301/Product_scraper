# Product Scraper

This repository provides a light-weight Shopify scraper that reads a workbook of
store metadata, crawls the product sitemap feeds supplied for each store, and
then fetches the structured product payload from Shopify's public JSON
endpoints. The workflow operates in two phases:

1. **Product sitemap collection** – Read an Excel workbook containing brand
   metadata and pre-specified product sitemap URLs, crawl those feeds while
   respecting rate limits, and extract every product URL exposed by Shopify.
2. **Product collection** – Convert each product URL into the corresponding
   Shopify JSON endpoint, fetch the structured payload, and persist the result
   alongside any failures.

## Project layout

- `parlant_agent/` – Core logic for parsing the Excel workbook, crawling
  sitemaps, and collecting product JSON payloads.
- `run_sitemap_agent.py` – Command line entry point for the scraper.
- `agentic_crawler_123.ipynb` – Notebook with reference experiments on polite
  crawling (kept for historical context).

## Requirements

The agent depends on the following Python packages:

- `pandas`
- `requests`
- `beautifulsoup4`

Install them with pip:

```bash
pip install -r requirements.txt
```

## Usage

1. Prepare an Excel workbook with the following columns:
   - `brand_name`
   - `site_url`
   - `product_sitemap_urls` – provide one or more product sitemap URLs (as a
     JSON array, newline separated string, or comma separated string). The agent
     does not attempt to discover primary sitemap indices, so this field is the
     sole entry point for crawling each store. The loader also accepts legacy
     column names (`product_sitemap_url` or `product_sitemaps`) but
     `product_sitemap_urls` is the standardized option.
2. Run the agent:

```bash
python run_sitemap_agent.py stores.xlsx output.json --progress logs/progress.jsonl --delay 2
```

The resulting JSON file will contain an entry per brand with the discovered
product sitemap URLs, product page URLs, and the structured JSON payload for
each product. Progress snapshots are written to the optional JSONL file so that
long-running sessions can be resumed or inspected. Any product URLs that fail to
resolve to a JSON endpoint or return invalid data are logged in the `errors`
field while still being associated with the originating store.

## Respectful crawling

The agent uses a configurable delay between requests, exponential backoff on
errors, and a custom user agent. Adjust these settings using the command line
flags described above to comply with each store's crawling policy.
