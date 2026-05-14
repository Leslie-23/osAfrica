"""IPC utilities for osAfrica daemons.

Provides async Unix socket client/server with JSON-line protocol.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import AsyncIterator


@dataclass
class Request:
    text: str
    model_hint: str = "auto"
    stream: bool = True
    context_id: str = ""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "query"


@dataclass
class Response:
    request_id: str
    text: str
    model: str = ""
    done: bool = False
    error: str = ""
    type: str = "chunk"
    usage: dict = field(default_factory=dict)


def encode_message(msg: Request | Response) -> bytes:
    return json.dumps(asdict(msg)).encode("utf-8") + b"\n"


def decode_message(line: bytes, cls: type):
    data = json.loads(line.decode("utf-8").strip())
    return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class IPCServer:
    def __init__(self, socket_path: Path, handler):
        self.socket_path = socket_path
        self.handler = handler
        self._server: asyncio.Server | None = None

    async def start(self):
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self.socket_path.unlink(missing_ok=True)
        self._server = await asyncio.start_unix_server(
            self._handle_client, path=str(self.socket_path)
        )
        self.socket_path.chmod(0o660)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                request = decode_message(line, Request)
                async for response in self.handler(request):
                    writer.write(encode_message(response))
                    await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self.socket_path.unlink(missing_ok=True)


class IPCClient:
    def __init__(self, socket_path: Path):
        self.socket_path = socket_path
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self):
        self._reader, self._writer = await asyncio.open_unix_connection(
            path=str(self.socket_path)
        )

    async def send(self, request: Request) -> AsyncIterator[Response]:
        if not self._writer:
            await self.connect()
        self._writer.write(encode_message(request))
        await self._writer.drain()
        while True:
            line = await self._reader.readline()
            if not line:
                break
            response = decode_message(line, Response)
            yield response
            if response.done or response.error:
                break

    async def query(self, text: str, model_hint: str = "auto") -> str:
        request = Request(text=text, model_hint=model_hint, stream=False)
        full_response = ""
        async for resp in self.send(request):
            full_response += resp.text
            if resp.error:
                raise RuntimeError(resp.error)
        return full_response

    async def close(self):
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
