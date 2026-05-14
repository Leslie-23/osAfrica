"""End-to-end shell tests.

Requires osa-routerd to be running with inference backend.
Skip with: pytest -m "not integration"
"""

import asyncio
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("OSA_INTEGRATION_TESTS"),
    reason="Set OSA_INTEGRATION_TESTS=1 to run integration tests",
)


class TestShellE2E:
    @pytest.fixture(autouse=True)
    def setup(self):
        from osa_core.common.ipc import IPCClient
        self.socket_path = Path(os.environ.get("OSA_SOCKET_PATH", "/run/osa/router.sock"))
        self.client = IPCClient(self.socket_path)

    async def test_connect_to_router(self):
        await self.client.connect()
        await self.client.close()

    async def test_general_query(self):
        await self.client.connect()
        response = await self.client.query("What is 2 + 2?")
        assert "4" in response
        await self.client.close()

    async def test_command_generation(self):
        await self.client.connect()
        response = await self.client.query("list all files in the current directory")
        assert any(cmd in response.lower() for cmd in ["ls", "dir", "find"])
        await self.client.close()

    async def test_code_generation(self):
        await self.client.connect()
        response = await self.client.query("write a Python hello world program")
        assert "print" in response.lower()
        await self.client.close()
