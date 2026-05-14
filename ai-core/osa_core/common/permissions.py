"""Command permission and sandboxing policy for AI-generated commands."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import json


class SafetyLevel(Enum):
    SAFE = "safe"
    NORMAL = "normal"
    EXPERT = "expert"


class CommandVerdict(Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    BLOCK = "block"


@dataclass(frozen=True)
class PolicyResult:
    verdict: CommandVerdict
    reason: str
    command: str


ALWAYS_BLOCK = [
    re.compile(r"rm\s+-rf\s+/\s*$"),
    re.compile(r"rm\s+-rf\s+/\*"),
    re.compile(r"dd\s+.*of=/dev/sd[a-z]\b"),
    re.compile(r"dd\s+.*of=/dev/nvme"),
    re.compile(r"mkfs\.\w+\s+/dev/sd[a-z]"),
    re.compile(r">\s*/dev/sd[a-z]"),
    re.compile(r":\(\)\s*\{"),  # fork bomb
    re.compile(r"chmod\s+-R\s+777\s+/\s*$"),
]

REQUIRE_CONFIRM = [
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\brm\s+-r\b"),
    re.compile(r"\brm\b.*\*"),
    re.compile(r"\bsystemctl\s+(stop|disable|mask)\b"),
    re.compile(r"\bapt\s+(remove|purge|autoremove)\b"),
    re.compile(r"\bdpkg\s+--remove\b"),
    re.compile(r"\bchmod\s+777\b"),
    re.compile(r"\bchown\s+-R\b"),
    re.compile(r"\bdd\b"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bshutdown\b"),
    re.compile(r"\breboot\b"),
    re.compile(r"\bkill\s+-9\b"),
    re.compile(r"\bkillall\b"),
    re.compile(r"\biptables\b"),
    re.compile(r"\bufw\b"),
    re.compile(r"\bpasswd\b"),
    re.compile(r"\buseradd\b"),
    re.compile(r"\buserdel\b"),
]

AUTO_ALLOW = [
    re.compile(r"^(ls|dir|cat|head|tail|less|more)\b"),
    re.compile(r"^(grep|rg|find|locate|which|whereis)\b"),
    re.compile(r"^(ps|top|htop|free|df|du|uptime|uname)\b"),
    re.compile(r"^(echo|printf|date|cal|wc|sort|uniq|cut)\b"),
    re.compile(r"^(pwd|whoami|id|hostname|env|printenv)\b"),
    re.compile(r"^(file|stat|md5sum|sha256sum)\b"),
    re.compile(r"^(man|info|help|apropos)\b"),
    re.compile(r"^(python3?|node|ruby|perl)\s+-c\b"),
]


DEFAULT_POLICY_PATH = Path("/etc/osa/command-policy.json")


class CommandPolicy:
    def __init__(self, safety_level: SafetyLevel = SafetyLevel.NORMAL):
        self.safety_level = safety_level
        self._custom_blocks: list[re.Pattern] = []
        self._custom_allows: list[re.Pattern] = []

    def load_custom_policy(self, path: Path = DEFAULT_POLICY_PATH):
        if not path.exists():
            return
        with open(path) as f:
            data = json.load(f)
        for pattern in data.get("block", []):
            self._custom_blocks.append(re.compile(pattern))
        for pattern in data.get("allow", []):
            self._custom_allows.append(re.compile(pattern))

    def evaluate(self, command: str) -> PolicyResult:
        command = command.strip()

        for pattern in ALWAYS_BLOCK:
            if pattern.search(command):
                return PolicyResult(CommandVerdict.BLOCK, "Blocked: catastrophic command", command)

        for pattern in self._custom_blocks:
            if pattern.search(command):
                return PolicyResult(CommandVerdict.BLOCK, "Blocked: custom policy", command)

        if self.safety_level == SafetyLevel.SAFE:
            return PolicyResult(CommandVerdict.CONFIRM, "Safe mode: all commands require confirmation", command)

        for pattern in self._custom_allows:
            if pattern.search(command):
                return PolicyResult(CommandVerdict.ALLOW, "Allowed: custom policy", command)

        for pattern in AUTO_ALLOW:
            if pattern.search(command):
                return PolicyResult(CommandVerdict.ALLOW, "Allowed: safe read-only command", command)

        if self.safety_level == SafetyLevel.EXPERT:
            for pattern in REQUIRE_CONFIRM:
                if pattern.search(command):
                    return PolicyResult(CommandVerdict.CONFIRM, "Expert mode: destructive command needs confirmation", command)
            return PolicyResult(CommandVerdict.ALLOW, "Expert mode: auto-allow", command)

        for pattern in REQUIRE_CONFIRM:
            if pattern.search(command):
                return PolicyResult(CommandVerdict.CONFIRM, "Destructive command requires confirmation", command)

        return PolicyResult(CommandVerdict.CONFIRM, "Unknown command: requires confirmation", command)
