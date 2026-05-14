"""Agent supervisor daemon — runs all system AI agents."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from osa_core.agents.resource_agent import ResourceAgent
from osa_core.agents.security_agent import SecurityAgent
from osa_core.agents.selfheal_agent import SelfHealAgent
from osa_core.common.ipc import IPCClient
from osa_core.router.config import RouterConfig
from osa_core.router.dispatch import Dispatcher

logger = logging.getLogger("osa-agentd")


async def run_supervisor():
    socket_path = Path("/run/osa/router.sock")
    client = None
    dispatcher = None

    try:
        client = IPCClient(socket_path)
        await client.connect()
        logger.info("Connected to osa-routerd at %s", socket_path)
    except (ConnectionRefusedError, FileNotFoundError):
        logger.warning("Router not available at %s, using direct mode", socket_path)
        client = None
        llama_url = os.environ.get("OSA_LLAMA_SWAP_URL", "http://127.0.0.1:8080")
        config = RouterConfig(llama_swap_url=llama_url)
        dispatcher = Dispatcher(config)
        if not await dispatcher.health_check():
            logger.error("Cannot reach inference server at %s", llama_url)
            sys.exit(1)
        logger.info("Direct mode: connected to %s", llama_url)

    agents = [
        ResourceAgent(router_client=client, dispatcher=dispatcher),
        SecurityAgent(router_client=client, dispatcher=dispatcher),
        SelfHealAgent(router_client=client, dispatcher=dispatcher),
    ]

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    tasks = [asyncio.create_task(agent.run_loop()) for agent in agents]
    logger.info("Started %d agents: %s", len(agents), [a.name for a in agents])

    await stop.wait()
    logger.info("Shutting down agents...")
    for agent in agents:
        agent.stop()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    if client:
        await client.close()
    if dispatcher:
        await dispatcher.close()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    try:
        asyncio.run(run_supervisor())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
