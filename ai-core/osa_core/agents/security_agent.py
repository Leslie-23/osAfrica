"""Security monitoring agent — analyzes system logs for anomalies."""

from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime, timedelta

from osa_core.agents.base_agent import SystemAgent


class SecurityAgent(SystemAgent):
    name = "security"
    interval_seconds = 300

    def __init__(self, router_client):
        super().__init__(router_client)
        self._last_check = datetime.now()

    async def collect_data(self) -> dict:
        data = {"auth_entries": [], "suspicious_entries": [], "timestamp": datetime.now().isoformat()}

        since = (datetime.now() - timedelta(seconds=self.interval_seconds)).strftime("%Y-%m-%d %H:%M:%S")

        try:
            result = await asyncio.create_subprocess_exec(
                "journalctl", "--since", since, "-u", "ssh", "--no-pager", "-q",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=10)
            entries = stdout.decode("utf-8", errors="replace").strip().splitlines()
            data["auth_entries"] = entries[-50:]
        except (FileNotFoundError, asyncio.TimeoutError):
            pass

        try:
            result = await asyncio.create_subprocess_exec(
                "journalctl", "--since", since, "--priority", "warning", "--no-pager", "-q",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=10)
            entries = stdout.decode("utf-8", errors="replace").strip().splitlines()
            data["suspicious_entries"] = entries[-50:]
        except (FileNotFoundError, asyncio.TimeoutError):
            pass

        try:
            result = await asyncio.create_subprocess_exec(
                "ss", "-tunap",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=5)
            data["open_connections"] = stdout.decode("utf-8", errors="replace").strip().splitlines()[:30]
        except (FileNotFoundError, asyncio.TimeoutError):
            data["open_connections"] = []

        self._last_check = datetime.now()
        return data

    def should_query_llm(self, data: dict) -> bool:
        return bool(data.get("auth_entries") or data.get("suspicious_entries"))

    def build_prompt(self, data: dict) -> str:
        auth = "\n".join(data.get("auth_entries", [])[-20:]) or "(none)"
        suspicious = "\n".join(data.get("suspicious_entries", [])[-20:]) or "(none)"
        connections = "\n".join(data.get("open_connections", [])[:15]) or "(none)"

        return (
            "You are the osAfrica security monitoring agent. Analyze these recent system logs "
            "for security concerns. Report only genuine threats, not routine activity.\n\n"
            f"SSH/Auth log entries (last {self.interval_seconds}s):\n{auth}\n\n"
            f"Warning/Error entries:\n{suspicious}\n\n"
            f"Active network connections:\n{connections}\n\n"
            "If you find security concerns, describe them briefly and suggest mitigations. "
            "If everything looks normal, respond with 'OK'."
        )

    async def act(self, llm_response: str, data: dict):
        if llm_response.strip().upper() == "OK":
            return

        self.logger.warning("Security alert: %s", llm_response[:300])
