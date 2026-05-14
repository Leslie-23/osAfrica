"""Code and config file generation for system tasks."""

from __future__ import annotations

from osa_core.common.ipc import IPCClient


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
    def __init__(self, router_client: IPCClient):
        self.router = router_client

    async def generate(self, template_name: str, description: str) -> str:
        template = TEMPLATE_PROMPTS.get(template_name)
        if not template:
            return await self._freeform_generate(description)
        prompt = template.format(description=description)
        return await self.router.query(prompt, model_hint="code")

    async def _freeform_generate(self, description: str) -> str:
        prompt = (
            "Generate the requested code or configuration. Be precise, "
            "production-quality, and include only the output — no explanation.\n\n"
            f"Request: {description}"
        )
        return await self.router.query(prompt, model_hint="code")

    async def list_templates(self) -> dict[str, str]:
        return {name: tmpl.split("\n")[0] for name, tmpl in TEMPLATE_PROMPTS.items()}
