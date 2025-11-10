"""Command line entry point for the product sitemap crawler."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from product_scraper import CrawlerConfig, ProductSitemapCrawler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("excel", type=Path, help="Path to the Excel workbook provided by the user")
    parser.add_argument("output", type=Path, help="Path to the JSON output file")
    parser.add_argument(
        "--progress",
        type=Path,
        default=None,
        help="Optional path to a JSONL file where per-site snapshots will be written.",
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
        "--retry-backoff",
        type=float,
        default=2.0,
        help="Exponential backoff factor between retries.",
    )
    parser.add_argument(
        "--max-products",
        type=int,
        default=None,
        help="Optional cap on the number of products to fetch per site.",
    )
    parser.add_argument(
        "--product-url-output",
        type=Path,
        default=None,
        help="Optional path to a JSONL file where collected product URLs will be stored.",
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
        retry_backoff=args.retry_backoff,
        delay_between_requests=args.delay,
    )

    crawler = ProductSitemapCrawler(
        crawler_config=crawler_config,
        progress_path=args.progress,
        max_products=args.max_products,
        product_url_output=args.product_url_output,
    )
    results = crawler.run(args.excel, args.output)
    total_products = sum(len(result.products) for result in results)
    logging.info(
        "Collected %s product payloads across %s store(s)",
        total_products,
        len(results),
    )


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
