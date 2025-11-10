# Product Scraper

This repository provides a light-weight Parlant-powered agent that collects product
sitemap URLs for Shopify stores. The workflow is designed to operate in three
phases:

1. **Sitemap discovery (this repository)** – Read an Excel workbook containing
   brand metadata and primary sitemap URLs, crawl those sitemap indices while
   respecting rate limits, and extract product sitemap URLs.
2. **Product scraping (external agent)** – Consume the product sitemap URLs and
   collect the structured product data using Shopify-aware logic.
3. **Data normalisation (external agent)** – Store the scraped data in the
   desired format.

## Project layout

- `parlant_agent/` – Core logic for parsing the Excel workbook, fetching
  sitemaps, and interacting with Parlant.
- `run_sitemap_agent.py` – Command line entry point for the discovery agent.
- `agentic_crawler_123.ipynb` – Notebook with reference experiments on polite
  crawling (kept for historical context).

## Requirements

The agent depends on the following Python packages:

- `parlant`
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
   - `primary_sitemaps` – either a JSON list, a newline separated string, or a
     comma separated string of sitemap URLs.
2. Run the agent:

```bash
python run_sitemap_agent.py stores.xlsx output.json --progress logs/progress.jsonl --delay 2
```

The resulting JSON file will contain an entry per brand with the discovered
product sitemap URLs. Progress snapshots are written to the optional JSONL file
so that long-running sessions can be resumed or inspected.

## Respectful crawling

The agent uses a configurable delay between requests, exponential backoff on
errors, and a custom user agent. Adjust these settings using the command line
flags described above to comply with each store's crawling policy.
