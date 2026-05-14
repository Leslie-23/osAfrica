"""AI-assisted debugging — analyzes errors, logs, and core dumps."""

from __future__ import annotations

import subprocess
from pathlib import Path

from osa_core.common.ipc import IPCClient


class AIDebugger:
    def __init__(self, router_client: IPCClient):
        self.router = router_client

    async def diagnose_error(self, error_output: str, source_file: str = "") -> str:
        context = ""
        if source_file:
            path = Path(source_file)
            if path.exists() and path.stat().st_size < 50_000:
                context = f"\nSource file ({path.name}):\n```\n{path.read_text(errors='replace')}\n```\n"

        prompt = (
            "Diagnose this error. Explain the root cause, then provide a specific fix.\n\n"
            f"Error output:\n```\n{error_output}\n```\n{context}"
        )
        return await self.router.query(prompt, model_hint="code")

    async def analyze_log(self, log_lines: str, context: str = "") -> str:
        prompt = (
            "Analyze these log entries for errors, warnings, and anomalies. "
            "Identify root causes and suggest fixes.\n\n"
        )
        if context:
            prompt += f"Context: {context}\n\n"
        prompt += f"```\n{log_lines[:6000]}\n```"
        return await self.router.query(prompt, model_hint="code")

    async def explain_exit_code(self, command: str, exit_code: int, stderr: str = "") -> str:
        prompt = (
            f"The command `{command}` exited with code {exit_code}.\n"
        )
        if stderr:
            prompt += f"stderr:\n```\n{stderr}\n```\n"
        prompt += "Explain what this exit code means and how to fix the issue."
        return await self.router.query(prompt, model_hint="code")

    async def analyze_service_failure(self, service_name: str) -> str:
        try:
            status = subprocess.run(
                ["systemctl", "status", service_name],
                capture_output=True, text=True, timeout=10,
            )
            journal = subprocess.run(
                ["journalctl", "-u", service_name, "-n", "30", "--no-pager"],
                capture_output=True, text=True, timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return f"Cannot query systemd for service: {service_name}"

        prompt = (
            f"Diagnose why the systemd service '{service_name}' has failed.\n\n"
            f"Service status:\n```\n{status.stdout}\n```\n\n"
            f"Recent journal entries:\n```\n{journal.stdout}\n```\n\n"
            "Identify the root cause and provide step-by-step recovery instructions."
        )
        return await self.router.query(prompt, model_hint="code")
