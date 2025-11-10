"""Adapters for interacting with the `parlant` package."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from .config import AgentConfig

logger = logging.getLogger(__name__)


@dataclass
class ConversationLog:
    """Simple stand-in for a Parlant conversation."""

    history: List[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.history.append(message)


class ParlantBridge:
    """Small helper that delegates to an actual Parlant agent when available."""

    def __init__(self, config: AgentConfig):
        self._config = config
        self._conversation = ConversationLog()
        self._agent = None
        try:  # pragma: no cover - optional dependency
            from parlant.agents import DialogAgent

            self._agent = DialogAgent(
                name="SitemapScout",
                system_prompt=config.system_prompt,
                max_messages=config.max_messages,
            )
            logger.debug("Parlant DialogAgent initialised")
        except Exception as exc:  # pragma: no cover - best effort fallback
            logger.info("Falling back to in-memory conversation log: %s", exc)

    def log(self, message: str) -> None:
        """Append a message to the agent conversation."""

        if self._agent is not None:  # pragma: no cover - optional dependency
            try:
                self._agent.add_message("system", message)
                return
            except Exception as exc:
                logger.warning("Failed to communicate with Parlant agent: %s", exc)
        self._conversation.add(message)

    @property
    def conversation(self) -> ConversationLog:
        return self._conversation
