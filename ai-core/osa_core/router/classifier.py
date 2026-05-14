"""Intent classifier — routes requests to the appropriate AI model.

Uses fast keyword/regex heuristics (no LLM inference) to classify whether
a request is code-related (→ Qwen Coder) or general (→ Llama 3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Intent(Enum):
    GENERAL = "general"
    CODE = "code"
    COMMAND = "command"


@dataclass(frozen=True)
class Classification:
    intent: Intent
    confidence: float
    model_hint: str
    reason: str


CODE_KEYWORDS_PHRASE = frozenset({
    "optimize this code", "write a program", "fix this code",
    "explain this code", "generate a script", "code review", "pull request",
    "test case",
})

CODE_KEYWORDS_WORD = frozenset({
    "code", "script", "function", "debug", "compile", "refactor", "review",
    "implement", "algorithm", "class", "method", "variable", "loop",
    "recursion", "api", "endpoint", "unittest", "regex",
    "parse", "serialize", "deserialize",
})

COMMAND_KEYWORDS_PHRASE = frozenset({
    "list files", "show files", "find files", "start service",
    "stop service", "disk space", "memory usage", "running processes",
    "kill process", "search for",
})

COMMAND_KEYWORDS_WORD = frozenset({
    "delete", "remove", "move", "copy", "rename", "install", "uninstall",
    "update", "upgrade", "restart", "reboot", "shutdown", "network", "wifi",
    "bluetooth", "mount", "unmount", "permissions", "open", "close",
    "compress", "extract", "download",
})

_WORD_BOUNDARY_CACHE: dict[str, re.Pattern] = {}


def _word_match(keyword: str, text: str) -> bool:
    if keyword not in _WORD_BOUNDARY_CACHE:
        _WORD_BOUNDARY_CACHE[keyword] = re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
    return _WORD_BOUNDARY_CACHE[keyword].search(text) is not None

CODE_PATTERNS = [
    re.compile(r"```"),
    re.compile(r"\b(def|class|import|from|function|const|let|var|struct|enum)\b"),
    re.compile(r"\.(py|js|ts|cpp|c|h|rs|go|java|rb|sh|sql|html|css)\b"),
    re.compile(r"(error|traceback|exception|segfault|stack trace|panic)", re.IGNORECASE),
    re.compile(r"(syntax error|type error|name error|runtime error)", re.IGNORECASE),
    re.compile(r"#include|using namespace|fn main|func main|public static void"),
]

COMMAND_PATTERNS = [
    re.compile(r"^(ls|cd|pwd|cat|grep|find|rm|cp|mv|mkdir|chmod|chown|apt|systemctl)\b"),
    re.compile(r"^(show|list|find|get|check|display)\s+(me\s+)?(the\s+)?"),
    re.compile(r"(how much|how many)\s+(disk|memory|ram|cpu|space)"),
]


def classify(text: str, context: dict | None = None) -> Classification:
    text_lower = text.lower().strip()
    code_score = 0.0
    command_score = 0.0
    general_score = 0.1
    reasons: list[str] = []

    for kw in CODE_KEYWORDS_PHRASE:
        if kw in text_lower:
            code_score += 0.3
            reasons.append(f"keyword:{kw}")
            break

    if not reasons:
        for kw in CODE_KEYWORDS_WORD:
            if _word_match(kw, text_lower):
                code_score += 0.3
                reasons.append(f"keyword:{kw}")
                break

    for pattern in CODE_PATTERNS:
        if pattern.search(text):
            code_score += 0.25
            reasons.append(f"pattern:{pattern.pattern[:30]}")
            break

    for kw in COMMAND_KEYWORDS_PHRASE:
        if kw in text_lower:
            command_score += 0.3
            reasons.append(f"cmd_keyword:{kw}")
            break

    if not any(r.startswith("cmd_keyword:") for r in reasons):
        for kw in COMMAND_KEYWORDS_WORD:
            if _word_match(kw, text_lower):
                command_score += 0.3
                reasons.append(f"cmd_keyword:{kw}")
                break

    for pattern in COMMAND_PATTERNS:
        if pattern.search(text_lower):
            command_score += 0.25
            reasons.append(f"cmd_pattern:{pattern.pattern[:30]}")
            break

    if context:
        if context.get("in_code_file"):
            code_score += 0.2
            reasons.append("context:in_code_file")
        if context.get("in_project_dir"):
            code_score += 0.1
            reasons.append("context:in_project_dir")

    multiline = text.count("\n") > 3
    if multiline and any(p.search(text) for p in CODE_PATTERNS):
        code_score += 0.2
        reasons.append("multiline_code_block")

    if code_score >= command_score and code_score >= general_score:
        confidence = min(code_score, 1.0)
        return Classification(
            intent=Intent.CODE,
            confidence=confidence,
            model_hint="qwen-coder",
            reason="; ".join(reasons) or "default",
        )

    if command_score >= code_score and command_score >= general_score:
        confidence = min(command_score, 1.0)
        return Classification(
            intent=Intent.COMMAND,
            confidence=confidence,
            model_hint="llama3-8b",
            reason="; ".join(reasons) or "default",
        )

    return Classification(
        intent=Intent.GENERAL,
        confidence=min(general_score, 1.0),
        model_hint="llama3-8b",
        reason="no strong signals",
    )
