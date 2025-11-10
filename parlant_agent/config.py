"""Configuration primitives for the sitemap extraction agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CrawlerConfig:
    """Settings that control polite crawling behaviour."""

    max_retries: int = 3
    request_timeout: int = 30
    retry_backoff: float = 2.0
    delay_between_requests: float = 1.0
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0 Safari/537.36"
    )


@dataclass
class AgentConfig:
    """Runtime configuration for the Parlant agent."""

    system_prompt: str = (
        "You are a data collection specialist. Your mission is to respect robots "
        "policies, remain polite, and only fetch sitemap documents that are "
        "explicitly provided."
    )
    max_messages: int = 25
