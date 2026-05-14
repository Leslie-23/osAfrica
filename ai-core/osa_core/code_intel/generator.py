"""Code and config file generation for system tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from osa_core.common.ipc import IPCClient
    from osa_core.router.dispatch import Dispatcher


TEMPLATE_PROMPTS = {
    "systemd_service": (
        "Generate a systemd service unit file for: {description}\n"
        "Include proper dependencies, security hardening (NoNewPrivileges, ProtectSystem), "
        "and restart policy. Output only the unit file content."
    ),
    "nginx_config": (
        "Generate an nginx configuration for: {description}\n"
        "Include security headers, gzip, and proper logging. Output only the config."
    ),
    "dockerfile": (
        "Generate a Dockerfile for: {description}\n"
        "Use multi-stage builds where appropriate, minimize layers, run as non-root. "
        "Output only the Dockerfile."
    ),
    "cron_job": (
        "Generate a cron entry and associated script for: {description}\n"
        "Include logging, error handling, and lock file to prevent concurrent runs."
    ),
    "ufw_rules": (
        "Generate UFW firewall rules for: {description}\n"
        "Start with deny incoming, allow outgoing, then specific allows."
    ),
    "bash_script": (
        "Generate a bash script for: {description}\n"
        "Use set -euo pipefail, include error handling, make it idempotent."
    ),
    "python_script": (
        "Generate a Python script for: {description}\n"
        "Use type hints, proper error handling, and argparse for CLI arguments."
    ),
}


class CodeGenerator:
    def __init__(self, router_client: IPCClient | None = None, dispatcher: Dispatcher | None = None):
        self.router = router_client
        self.dispatcher = dispatcher

    async def _query(self, prompt: str) -> str:
        if self.dispatcher:
            return await self.dispatcher.complete(text=prompt, model="qwen-coder", intent_type="code")
        if self.router:
            return await self.router.query(prompt, model_hint="code")
        raise RuntimeError("No router or dispatcher configured")

    async def generate(self, template_name: str, description: str) -> str:
        template = TEMPLATE_PROMPTS.get(template_name)
        if not template:
            return await self._freeform_generate(description)
        prompt = template.format(description=description)
        return await self._query(prompt)

    async def _freeform_generate(self, description: str) -> str:
        prompt = (
            "Generate the requested code or configuration. Be precise, "
            "production-quality, and include only the output — no explanation.\n\n"
            f"Request: {description}"
        )
        return await self._query(prompt)

    async def list_templates(self) -> dict[str, str]:
        return {name: tmpl.split("\n")[0] for name, tmpl in TEMPLATE_PROMPTS.items()}
