"""Structured logging and audit trail for AI actions."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path


AUDIT_LOG_PATH = Path("/var/log/osa/ai-actions.log")


class AuditLogger:
    def __init__(self, log_path: Path = AUDIT_LOG_PATH):
        self.log_path = log_path
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass

    def log_action(
        self,
        user: str,
        action_type: str,
        prompt: str,
        model: str,
        generated_command: str = "",
        result: str = "",
        exit_code: int | None = None,
        sandboxed: bool = False,
    ):
        entry = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "user": user,
            "action": action_type,
            "prompt": prompt[:500],
            "model": model,
            "command": generated_command,
            "result": result[:500],
            "exit_code": exit_code,
            "sandboxed": sandboxed,
        }

        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except (PermissionError, OSError):
            logging.getLogger("osa-audit").warning(
                "Cannot write audit log to %s", self.log_path
            )

    def recent_actions(self, limit: int = 50) -> list[dict]:
        if not self.log_path.exists():
            return []
        try:
            lines = self.log_path.read_text().strip().splitlines()
            entries = []
            for line in lines[-limit:]:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return entries
        except (PermissionError, OSError):
            return []
