"""Self-healing agent — monitors and restarts failed services."""

from __future__ import annotations

import asyncio

from osa_core.agents.base_agent import SystemAgent

WATCHED_SERVICES = [
    "osa-llama-swap",
    "osa-routerd",
    "osa-agentd",
    "NetworkManager",
    "systemd-resolved",
]


class SelfHealAgent(SystemAgent):
    name = "selfheal"
    interval_seconds = 60

    async def collect_data(self) -> dict:
        failed_services = []
        service_logs = {}

        for svc in WATCHED_SERVICES:
            try:
                result = await asyncio.create_subprocess_exec(
                    "systemctl", "is-active", svc,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(result.communicate(), timeout=5)
                status = stdout.decode().strip()
                if status != "active":
                    failed_services.append({"name": svc, "status": status})

                    log_result = await asyncio.create_subprocess_exec(
                        "journalctl", "-u", svc, "--no-pager", "-n", "20", "-q",
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                    )
                    log_stdout, _ = await asyncio.wait_for(log_result.communicate(), timeout=5)
                    service_logs[svc] = log_stdout.decode("utf-8", errors="replace").strip()
            except (FileNotFoundError, asyncio.TimeoutError):
                continue

        return {"failed_services": failed_services, "logs": service_logs}

    def should_query_llm(self, data: dict) -> bool:
        return bool(data.get("failed_services"))

    def build_prompt(self, data: dict) -> str:
        services_info = ""
        for svc in data.get("failed_services", []):
            name = svc["name"]
            logs = data.get("logs", {}).get(name, "(no logs)")
            services_info += f"\nService: {name} (status: {svc['status']})\nRecent logs:\n{logs}\n"

        return (
            "You are the osAfrica self-healing agent. These system services have failed. "
            "Analyze the logs and suggest recovery actions.\n"
            f"{services_info}\n"
            "For each service, respond with one of:\n"
            "- RESTART <service> — if a simple restart should fix it\n"
            "- SKIP <service> — if it's not critical or needs manual intervention\n"
            "- INVESTIGATE <service> <reason> — if the issue needs human attention\n"
        )

    async def act(self, llm_response: str, data: dict):
        for line in llm_response.strip().splitlines():
            line = line.strip()
            if line.startswith("RESTART "):
                service = line.split(None, 1)[1].strip()
                if service in WATCHED_SERVICES:
                    self.logger.info("Attempting restart of %s", service)
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            "systemctl", "restart", service,
                            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                        )
                        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                        if proc.returncode == 0:
                            self.logger.info("Successfully restarted %s", service)
                        else:
                            self.logger.error("Failed to restart %s: %s", service, stderr.decode())
                    except (asyncio.TimeoutError, FileNotFoundError) as e:
                        self.logger.error("Restart failed for %s: %s", service, e)
            elif line.startswith("INVESTIGATE "):
                parts = line.split(None, 2)
                service = parts[1] if len(parts) > 1 else "unknown"
                reason = parts[2] if len(parts) > 2 else "unknown reason"
                self.logger.warning("Service %s needs investigation: %s", service, reason)
