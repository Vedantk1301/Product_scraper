"""Command line entry point for the Shopify product scraper."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from parlant_agent import SitemapExtractionAgent
from parlant_agent.config import CrawlerConfig, ProductScraperConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("excel", type=Path, help="Path to the Excel workbook provided by the user")
    parser.add_argument("output", type=Path, help="Path to the JSON output file")
    parser.add_argument(
        "--progress",
        type=Path,
        default=None,
        help="Optional path to a JSONL file where progress snapshots will be written.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between HTTP requests.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum number of retries per URL.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Increase logging verbosity.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    crawler_config = CrawlerConfig(
        max_retries=args.retries,
        request_timeout=args.timeout,
        delay_between_requests=args.delay,
    )
    scraper_config = ProductScraperConfig()

    agent = SitemapExtractionAgent(
        crawler_config=crawler_config,
        scraper_config=scraper_config,
        progress_path=args.progress,
    )
    results = agent.run(args.excel, args.output)
    logging.info("Collected product data for %s stores", len(results))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
