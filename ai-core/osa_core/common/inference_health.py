"""Inference server health monitor with auto-restart and performance tracking."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger("osa-inference-health")


@dataclass
class InferenceStats:
    total_requests: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0
    errors: int = 0
    restarts: int = 0
    last_health_check: float = 0
    model_load_time_ms: float = 0
    avg_tokens_per_sec: float = 0

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0
        return self.total_latency_ms / self.total_requests


@dataclass
class InferenceConfig:
    model_path: str = ""
    host: str = "127.0.0.1"
    port: int = 8081
    ctx_size: int = 2048
    threads: int = 0
    batch_size: int = 512
    flash_attn: bool = True
    cont_batching: bool = True
    n_gpu_layers: int = 0
    keepalive_timeout: int = 300

    @classmethod
    def from_hardware(cls, hw_profile: dict | None = None) -> InferenceConfig:
        config = cls()
        config.threads = os.cpu_count() or 4

        ram_gb = 8
        if hw_profile:
            ram_gb = hw_profile.get("ram_gb", 8)

        if ram_gb <= 10:
            config.ctx_size = 512
            config.batch_size = 256
        elif ram_gb <= 18:
            config.ctx_size = 2048
            config.batch_size = 512
        else:
            config.ctx_size = 4096
            config.batch_size = 1024

        if hw_profile and hw_profile.get("gpu"):
            config.n_gpu_layers = 99
            config.ctx_size = min(config.ctx_size * 2, 8192)

        return config

    def to_args(self) -> list[str]:
        args = [
            "llama-server",
            "--model", self.model_path,
            "--host", self.host,
            "--port", str(self.port),
            "--ctx-size", str(self.ctx_size),
            "--threads", str(self.threads),
            "--batch-size", str(self.batch_size),
        ]
        if self.flash_attn:
            args.append("--flash-attn")
        if self.cont_batching:
            args.append("--cont-batching")
        if self.n_gpu_layers > 0:
            args.extend(["--n-gpu-layers", str(self.n_gpu_layers)])
        return args


class InferenceHealthMonitor:
    def __init__(self, base_url: str = "http://127.0.0.1:8081", check_interval: int = 30):
        self.base_url = base_url
        self.check_interval = check_interval
        self.stats = InferenceStats()
        self._client = httpx.AsyncClient(base_url=base_url, timeout=10.0)
        self._running = False
        self._max_restarts = 5
        self._restart_cooldown = 60

    async def check_health(self) -> bool:
        try:
            resp = await self._client.get("/health")
            self.stats.last_health_check = time.time()
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def get_server_metrics(self) -> dict:
        try:
            resp = await self._client.get("/metrics")
            if resp.status_code == 200:
                return self._parse_prometheus_metrics(resp.text)
        except httpx.HTTPError:
            pass
        return {}

    def _parse_prometheus_metrics(self, text: str) -> dict:
        metrics = {}
        for line in text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    metrics[parts[0]] = float(parts[1])
                except ValueError:
                    pass
        return metrics

    def record_request(self, tokens: int, latency_ms: float, error: bool = False):
        self.stats.total_requests += 1
        self.stats.total_tokens += tokens
        self.stats.total_latency_ms += latency_ms
        if error:
            self.stats.errors += 1
        if latency_ms > 0 and tokens > 0:
            self.stats.avg_tokens_per_sec = tokens / (latency_ms / 1000)

    async def restart_server(self, config: InferenceConfig) -> bool:
        if self.stats.restarts >= self._max_restarts:
            logger.error("Max restart attempts reached (%d)", self._max_restarts)
            return False

        logger.warning("Restarting inference server (attempt %d)", self.stats.restarts + 1)

        try:
            subprocess.run(["pkill", "-f", "llama-server"], capture_output=True, timeout=10)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        await asyncio.sleep(2)

        try:
            subprocess.Popen(
                config.to_args(),
                stdout=open("/tmp/llama-server.log", "a"),
                stderr=subprocess.STDOUT,
            )
            self.stats.restarts += 1

            for _ in range(30):
                await asyncio.sleep(2)
                if await self.check_health():
                    logger.info("Inference server restarted successfully")
                    return True

            logger.error("Inference server failed to start after restart")
            return False
        except (FileNotFoundError, OSError) as e:
            logger.error("Cannot restart inference server: %s", e)
            return False

    async def run_monitor(self, config: InferenceConfig | None = None):
        self._running = True
        consecutive_failures = 0
        logger.info("Inference health monitor started (interval=%ds)", self.check_interval)

        while self._running:
            healthy = await self.check_health()
            if healthy:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                logger.warning("Health check failed (%d consecutive)", consecutive_failures)

                if consecutive_failures >= 3 and config:
                    await self.restart_server(config)
                    consecutive_failures = 0

            await asyncio.sleep(self.check_interval)

    def stop(self):
        self._running = False

    async def close(self):
        await self._client.aclose()
