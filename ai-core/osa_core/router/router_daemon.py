"""osa-routerd — Central AI router daemon.

Listens on a Unix socket, classifies incoming requests, dispatches them
to the appropriate model via llama-swap, and streams responses back.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import AsyncIterator

from osa_core.common.ipc import IPCServer, Request, Response
from osa_core.router.classifier import Intent, classify
from osa_core.router.config import RouterConfig
from osa_core.router.dispatch import Dispatcher

logger = logging.getLogger("osa-routerd")


class Router:
    def __init__(self, config: RouterConfig | None = None):
        self.config = config or RouterConfig()
        self.dispatcher = Dispatcher(self.config)
        self.server = IPCServer(self.config.socket_path, self.handle_request)
        self._conversations: dict[str, list[dict]] = {}

    def _resolve_model(self, classification) -> str:
        if classification.intent == Intent.CODE:
            return self.config.qwen_model
        return self.config.llama3_model

    def _get_conversation(self, context_id: str) -> list[dict]:
        if not context_id:
            return []
        return self._conversations.setdefault(context_id, [])

    def _append_to_conversation(self, context_id: str, role: str, content: str):
        if not context_id:
            return
        conv = self._conversations.setdefault(context_id, [])
        conv.append({"role": role, "content": content})
        if len(conv) > 20:
            self._conversations[context_id] = conv[-20:]

    async def handle_request(self, request: Request) -> AsyncIterator[Response]:
        classification = classify(request.text)
        model = self._resolve_model(classification)
        intent_type = classification.intent.value
        conversation = self._get_conversation(request.context_id)

        logger.info(
            "request=%s model=%s intent=%s confidence=%.2f reason=%s",
            request.request_id[:8],
            model,
            intent_type,
            classification.confidence,
            classification.reason,
        )

        try:
            if request.stream:
                full_response = ""
                async for chunk in self.dispatcher.stream(
                    request.text, model, intent_type, conversation
                ):
                    full_response += chunk
                    yield Response(
                        request_id=request.request_id,
                        text=chunk,
                        model=model,
                        done=False,
                    )
                self._append_to_conversation(request.context_id, "user", request.text)
                self._append_to_conversation(request.context_id, "assistant", full_response)
                yield Response(
                    request_id=request.request_id,
                    text="",
                    model=model,
                    done=True,
                )
            else:
                result = await self.dispatcher.complete(
                    request.text, model, intent_type, conversation
                )
                self._append_to_conversation(request.context_id, "user", request.text)
                self._append_to_conversation(request.context_id, "assistant", result)
                yield Response(
                    request_id=request.request_id,
                    text=result,
                    model=model,
                    done=True,
                )
        except Exception as e:
            logger.exception("Inference error: %s", e)
            yield Response(
                request_id=request.request_id,
                text="",
                model=model,
                done=True,
                error=str(e),
            )

    async def run(self):
        await self.server.start()
        logger.info("osa-routerd listening on %s", self.config.socket_path)

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)

        await stop.wait()
        logger.info("Shutting down...")
        await self.server.stop()
        await self.dispatcher.close()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    config = RouterConfig()
    router = Router(config)
    try:
        asyncio.run(router.run())
    except KeyboardInterrupt:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
