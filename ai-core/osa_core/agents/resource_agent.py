"""Resource monitoring agent — watches RAM, CPU, and disk usage."""

from __future__ import annotations

import asyncio
from pathlib import Path

from osa_core.agents.base_agent import SystemAgent


class ResourceAgent(SystemAgent):
    name = "resource"
    interval_seconds = 120

    def __init__(self, router_client, thresholds: dict | None = None):
        super().__init__(router_client)
        self.thresholds = thresholds or {
            "ram_percent_warn": 85,
            "ram_percent_critical": 95,
            "disk_percent_warn": 90,
            "load_per_core_warn": 2.0,
        }

    async def collect_data(self) -> dict:
        data = {}
        try:
            with open("/proc/meminfo") as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    meminfo[parts[0].rstrip(":")] = int(parts[1])
                total = meminfo.get("MemTotal", 1)
                available = meminfo.get("MemAvailable", 0)
                data["ram_total_mb"] = total // 1024
                data["ram_available_mb"] = available // 1024
                data["ram_used_percent"] = round((1 - available / total) * 100, 1)
        except (FileNotFoundError, KeyError, ZeroDivisionError):
            data["ram_used_percent"] = 0

        try:
            with open("/proc/loadavg") as f:
                parts = f.read().split()
                data["load_1m"] = float(parts[0])
                data["load_5m"] = float(parts[1])
                data["load_15m"] = float(parts[2])
        except (FileNotFoundError, IndexError, ValueError):
            data["load_1m"] = 0

        try:
            import os
            stat = os.statvfs("/")
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            data["disk_total_gb"] = round(total / (1024**3), 1)
            data["disk_free_gb"] = round(free / (1024**3), 1)
            data["disk_used_percent"] = round((1 - free / total) * 100, 1)
        except (OSError, ZeroDivisionError):
            data["disk_used_percent"] = 0

        try:
            top_procs = []
            proc_path = Path("/proc")
            for pid_dir in sorted(proc_path.iterdir()):
                if not pid_dir.name.isdigit():
                    continue
                try:
                    status = (pid_dir / "status").read_text()
                    name = ""
                    rss = 0
                    for line in status.splitlines():
                        if line.startswith("Name:"):
                            name = line.split(":", 1)[1].strip()
                        elif line.startswith("VmRSS:"):
                            rss = int(line.split()[1]) // 1024
                    if rss > 50:
                        top_procs.append({"name": name, "pid": pid_dir.name, "rss_mb": rss})
                except (PermissionError, FileNotFoundError, ValueError):
                    continue
            top_procs.sort(key=lambda p: p["rss_mb"], reverse=True)
            data["top_processes"] = top_procs[:10]
        except (PermissionError, FileNotFoundError):
            data["top_processes"] = []

        return data

    def should_query_llm(self, data: dict) -> bool:
        if data.get("ram_used_percent", 0) >= self.thresholds["ram_percent_warn"]:
            return True
        if data.get("disk_used_percent", 0) >= self.thresholds["disk_percent_warn"]:
            return True
        import os
        cores = os.cpu_count() or 1
        if data.get("load_1m", 0) / cores >= self.thresholds["load_per_core_warn"]:
            return True
        return False

    def build_prompt(self, data: dict) -> str:
        procs = "\n".join(
            f"  {p['name']} (PID {p['pid']}): {p['rss_mb']} MB"
            for p in data.get("top_processes", [])
        )
        return (
            "You are the osAfrica resource monitoring agent. Analyze these system metrics "
            "and recommend actions if needed. Be concise.\n\n"
            f"RAM: {data.get('ram_used_percent', 0)}% used "
            f"({data.get('ram_available_mb', 0)} MB available of {data.get('ram_total_mb', 0)} MB)\n"
            f"Load average: {data.get('load_1m', 0)} / {data.get('load_5m', 0)} / {data.get('load_15m', 0)}\n"
            f"Disk: {data.get('disk_used_percent', 0)}% used "
            f"({data.get('disk_free_gb', 0)} GB free of {data.get('disk_total_gb', 0)} GB)\n\n"
            f"Top processes by memory:\n{procs}\n\n"
            "If action is needed, suggest specific commands. If everything is fine, say 'OK'."
        )

    async def act(self, llm_response: str, data: dict):
        if llm_response.strip().upper() == "OK":
            return

        self.logger.warning(
            "Resource alert (RAM: %s%%, Disk: %s%%): %s",
            data.get("ram_used_percent", 0),
            data.get("disk_used_percent", 0),
            llm_response[:200],
        )
