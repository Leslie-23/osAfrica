"""Dispatch layer — sends requests to llama-swap and streams responses."""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from osa_core.router.config import RouterConfig


class Dispatcher:
    def __init__(self, config: RouterConfig):
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.llama_swap_url,
            timeout=httpx.Timeout(config.request_timeout, connect=5.0),
        )

    def _select_system_prompt(self, intent_type: str) -> str:
        if intent_type == "code":
            return self.config.system_prompt_code
        if intent_type == "command":
            return self.config.system_prompt_command
        return self.config.system_prompt_general

    def _build_payload(
        self,
        text: str,
        model: str,
        intent_type: str,
        stream: bool,
        conversation: list[dict] | None = None,
    ) -> dict:
        messages = [{"role": "system", "content": self._select_system_prompt(intent_type)}]
        if conversation:
            messages.extend(conversation)
        messages.append({"role": "user", "content": text})

        return {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": self.config.max_context_tokens,
            "temperature": 0.3 if intent_type == "command" else 0.7,
        }

    async def complete(
        self,
        text: str,
        model: str,
        intent_type: str = "general",
        conversation: list[dict] | None = None,
    ) -> str:
        payload = self._build_payload(text, model, intent_type, stream=False, conversation=conversation)
        resp = await self._client.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def stream(
        self,
        text: str,
        model: str,
        intent_type: str = "general",
        conversation: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        payload = self._build_payload(text, model, intent_type, stream=True, conversation=conversation)
        async with self._client.stream("POST", "/v1/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get("/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self):
        await self._client.aclose()
