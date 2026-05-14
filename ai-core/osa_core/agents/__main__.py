"""Agent supervisor daemon — runs all system AI agents."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

from osa_core.agents.resource_agent import ResourceAgent
from osa_core.agents.security_agent import SecurityAgent
from osa_core.agents.selfheal_agent import SelfHealAgent
from osa_core.common.ipc import IPCClient

logger = logging.getLogger("osa-agentd")


async def run_supervisor():
    socket_path = Path("/run/osa/router.sock")
    client = IPCClient(socket_path)

    try:
        await client.connect()
        logger.info("Connected to osa-routerd at %s", socket_path)
    except (ConnectionRefusedError, FileNotFoundError):
        logger.error("Cannot connect to osa-routerd at %s", socket_path)
        sys.exit(1)

    agents = [
        ResourceAgent(client),
        SecurityAgent(client),
        SelfHealAgent(client),
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
    await client.close()


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
