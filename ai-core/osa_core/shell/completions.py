"""AI-powered tab completions for osa-shell."""

from __future__ import annotations

import os
from pathlib import Path

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


BUILTIN_COMMANDS = {
    "/help": "Show help information",
    "/quit": "Exit osa-shell",
    "/bash": "Toggle bash pass-through mode",
    "/safety": "Set safety level (safe/normal/expert)",
    "/model": "Show active model info",
    "/clear": "Clear conversation context",
}

NATURAL_LANGUAGE_HINTS = [
    "list files in ",
    "find all ",
    "show me ",
    "install ",
    "delete ",
    "create a ",
    "write a script to ",
    "explain ",
    "debug this ",
    "what is ",
    "how do I ",
    "search for ",
    "open ",
    "compress ",
    "check disk space",
    "show running processes",
    "show memory usage",
    "update the system",
]


class OsaCompleter(Completer):
    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        word = document.get_word_before_cursor()

        if text.startswith("/"):
            for cmd, desc in BUILTIN_COMMANDS.items():
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display_meta=desc,
                    )
            return

        if text.startswith("!"):
            raw = text[1:]
            yield from self._complete_bash(raw, document)
            return

        if not text or len(text) < 2:
            for hint in NATURAL_LANGUAGE_HINTS[:8]:
                yield Completion(hint, start_position=-len(text))
            return

        for hint in NATURAL_LANGUAGE_HINTS:
            if hint.startswith(text.lower()):
                yield Completion(hint, start_position=-len(text))

        yield from self._complete_paths(word)

    def _complete_paths(self, word: str):
        if not word or word.startswith("-"):
            return

        try:
            if "/" in word or "\\" in word:
                parent = Path(word).parent
                prefix = Path(word).name
            else:
                parent = Path(".")
                prefix = word

            if parent.is_dir():
                for entry in sorted(parent.iterdir()):
                    name = str(entry) if "/" in word else entry.name
                    if name.lower().startswith(prefix.lower()):
                        suffix = "/" if entry.is_dir() else ""
                        yield Completion(
                            name + suffix,
                            start_position=-len(word),
                            display_meta="dir" if entry.is_dir() else "file",
                        )
        except (PermissionError, OSError):
            pass

    def _complete_bash(self, raw_text: str, document: Document):
        common_commands = [
            "ls", "cd", "pwd", "cat", "grep", "find", "mkdir", "rm", "cp", "mv",
            "chmod", "chown", "apt", "systemctl", "journalctl", "docker",
            "git", "python3", "pip", "node", "npm", "curl", "wget", "ssh",
            "tar", "gzip", "df", "du", "free", "top", "ps", "kill",
        ]
        word = raw_text.split()[-1] if raw_text.split() else raw_text
        for cmd in common_commands:
            if cmd.startswith(word):
                yield Completion(
                    cmd,
                    start_position=-len(word),
                    display_meta="command",
                )
