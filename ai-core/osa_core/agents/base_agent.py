"""Base class for osAfrica system AI agents."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from osa_core.common.ipc import IPCClient, Request


class SystemAgent(ABC):
    name: str = "base"
    interval_seconds: int = 60

    def __init__(self, router_client: IPCClient):
        self.router = router_client
        self.logger = logging.getLogger(f"osa-agent.{self.name}")
        self._running = False
        self._last_run: datetime | None = None
        self._consecutive_errors = 0

    @abstractmethod
    async def collect_data(self) -> dict:
        """Gather system metrics/logs relevant to this agent."""

    @abstractmethod
    def build_prompt(self, data: dict) -> str:
        """Construct LLM prompt from collected data."""

    @abstractmethod
    async def act(self, llm_response: str, data: dict):
        """Take action based on LLM analysis."""

    async def run_cycle(self):
        try:
            data = await self.collect_data()
            if not self.should_query_llm(data):
                self._consecutive_errors = 0
                return

            prompt = self.build_prompt(data)
            response = await self.router.query(prompt, model_hint="general")
            await self.act(response, data)
            self._consecutive_errors = 0
            self._last_run = datetime.now()
        except Exception as e:
            self._consecutive_errors += 1
            self.logger.error("Agent cycle failed (%d consecutive): %s", self._consecutive_errors, e)
            if self._consecutive_errors >= 5:
                self.logger.warning("Too many consecutive errors, backing off")

    def should_query_llm(self, data: dict) -> bool:
        return True

    @property
    def effective_interval(self) -> int:
        if self._consecutive_errors >= 5:
            return self.interval_seconds * 4
        if self._consecutive_errors >= 3:
            return self.interval_seconds * 2
        return self.interval_seconds

    async def run_loop(self):
        self._running = True
        self.logger.info("Agent %s started (interval=%ds)", self.name, self.interval_seconds)
        while self._running:
            await self.run_cycle()
            await asyncio.sleep(self.effective_interval)

    def stop(self):
        self._running = False
