"""Parse AI responses to extract executable commands and structured output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ResponseType(Enum):
    COMMAND = "command"
    CODE_BLOCK = "code_block"
    EXPLANATION = "explanation"
    MIXED = "mixed"


@dataclass
class ParsedResponse:
    response_type: ResponseType
    raw_text: str
    commands: list[str]
    code_blocks: list[CodeBlock]
    explanation: str


@dataclass
class CodeBlock:
    language: str
    code: str


_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_COMMAND_PREFIX_RE = re.compile(r"^\$\s+(.+)$", re.MULTILINE)


def parse_response(text: str) -> ParsedResponse:
    commands: list[str] = []
    code_blocks: list[CodeBlock] = []
    explanation_parts: list[str] = []

    for match in _CODE_BLOCK_RE.finditer(text):
        lang = match.group(1).lower() or "text"
        code = match.group(2).strip()
        code_blocks.append(CodeBlock(language=lang, code=code))

        if lang in ("bash", "sh", "shell", "zsh", ""):
            for line in code.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    commands.append(line)

    remaining = _CODE_BLOCK_RE.sub("", text).strip()

    for match in _COMMAND_PREFIX_RE.finditer(remaining):
        commands.append(match.group(1).strip())

    for line in remaining.splitlines():
        stripped = line.strip()
        if stripped and not _COMMAND_PREFIX_RE.match(stripped):
            explanation_parts.append(stripped)

    explanation = "\n".join(explanation_parts).strip()

    if not remaining and code_blocks:
        rtype = ResponseType.CODE_BLOCK
    elif commands and not explanation:
        rtype = ResponseType.COMMAND
    elif commands and explanation:
        rtype = ResponseType.MIXED
    else:
        rtype = ResponseType.EXPLANATION

    return ParsedResponse(
        response_type=rtype,
        raw_text=text,
        commands=commands,
        code_blocks=code_blocks,
        explanation=explanation,
    )


def extract_single_command(text: str) -> str | None:
    """Extract a single command from a response that should be just a command."""
    text = text.strip()

    for match in _CODE_BLOCK_RE.finditer(text):
        code = match.group(2).strip()
        lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
        if lines:
            return "\n".join(lines)

    lines = text.splitlines()
    if len(lines) == 1:
        cmd = lines[0].strip().strip("`")
        if cmd.startswith("$ "):
            cmd = cmd[2:]
        return cmd

    for line in lines:
        line = line.strip()
        if line.startswith("$ "):
            return line[2:]

    for line in lines:
        line = line.strip().strip("`")
        if line and not any(line.startswith(w) for w in ("This", "The", "You", "Here", "Note")):
            return line

    return None
