"""osa-shell — AI-native shell for osAfrica.

A natural language terminal that translates user intent into system commands
via Llama 3 and provides code intelligence via Qwen Coder.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
import sys
import uuid
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from osa_core.common.ipc import IPCClient, Request
from osa_core.common.permissions import CommandPolicy, CommandVerdict, SafetyLevel
from osa_core.router.classifier import Intent, classify
from osa_core.router.config import RouterConfig
from osa_core.router.dispatch import Dispatcher
from osa_core.shell.history import ShellHistory

SHELL_STYLE = Style.from_dict({
    "prompt": "#00cc66 bold",
    "model": "#6688cc",
    "command": "#cccc00",
    "error": "#cc3333 bold",
    "info": "#888888",
})

BANNER = """\
\033[1;32m╔═══════════════════════════════════════════╗
║          osAfrica AI Shell v0.1.0         ║
║   Type naturally. Prefix ! for raw bash.  ║
║   /help for commands. /quit to exit.      ║
╚═══════════════════════════════════════════╝\033[0m"""

HELP_TEXT = """
\033[1mBuilt-in commands:\033[0m
  /help          Show this help
  /quit          Exit osa-shell
  /bash          Toggle bash pass-through mode
  /safety <lvl>  Set safety level: safe, normal, expert
  /model         Show active model info
  /history       Show query statistics
  /clear         Clear conversation context
  !<command>     Run a bash command directly

\033[1mExamples:\033[0m
  list all python files larger than 1MB
  write a script to parse this CSV file
  install nginx and configure it for static files
  what was the command you just gave me?  (multi-turn context)
  !ls -la
"""


class OsaShell:
    def __init__(self, router_socket: Path | None = None):
        self.socket_path = router_socket or Path("/run/osa/router.sock")
        self.client: IPCClient | None = None
        self.dispatcher: Dispatcher | None = None
        self.direct_mode = False
        self.context_id = str(uuid.uuid4())
        self.conversation: list[dict] = []
        self.max_context_turns = 10
        self.policy = CommandPolicy(SafetyLevel.NORMAL)
        self.bash_mode = False
        self.history = ShellHistory()
        self.cwd = Path.cwd()
        history_dir = Path.home() / ".osa"
        history_dir.mkdir(exist_ok=True)
        self.session = PromptSession(
            history=FileHistory(str(history_dir / "shell_history")),
            style=SHELL_STYLE,
        )

    def _prompt_text(self) -> HTML:
        cwd_short = str(self.cwd).replace(str(Path.home()), "~")
        mode = "bash" if self.bash_mode else "ai"
        return HTML(f"<prompt>osa</prompt>:<info>{cwd_short}</info> [{mode}]$ ")

    async def connect(self):
        self.client = IPCClient(self.socket_path)
        try:
            await self.client.connect()
            return True
        except (ConnectionRefusedError, FileNotFoundError):
            return False

    def _handle_builtin(self, text: str) -> bool:
        cmd = text.strip().lower()
        if cmd == "/quit":
            raise EOFError
        if cmd == "/help":
            print(HELP_TEXT)
            return True
        if cmd == "/bash":
            self.bash_mode = not self.bash_mode
            state = "ON" if self.bash_mode else "OFF"
            print(f"Bash pass-through mode: {state}")
            return True
        if cmd.startswith("/safety "):
            level = cmd.split(None, 1)[1]
            try:
                self.policy.safety_level = SafetyLevel(level)
                print(f"Safety level set to: {level}")
            except ValueError:
                print(f"Unknown safety level: {level}. Use: safe, normal, expert")
            return True
        if cmd == "/model":
            print("Models: Llama 3 8B (general) + Qwen Coder (code)")
            mode = "direct" if self.direct_mode else f"router ({self.socket_path})"
            print(f"Mode: {mode}")
            print(f"Context: {len(self.conversation) // 2} turns")
            return True
        if cmd == "/clear":
            self.context_id = str(uuid.uuid4())
            self.conversation.clear()
            print("Conversation context cleared.")
            return True
        if cmd == "/history":
            stats = self.history.stats()
            print(f"Total queries: {stats['total']}")
            if stats["by_intent"]:
                print("By intent:", ", ".join(f"{k}={v}" for k, v in stats["by_intent"].items()))
            if stats["by_model"]:
                print("By model:", ", ".join(f"{k}={v}" for k, v in stats["by_model"].items()))
            return True
        return False

    def _run_bash(self, command: str) -> int:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.cwd),
                env={**os.environ, "OSA_SHELL": "1"},
            )
            return result.returncode
        except KeyboardInterrupt:
            print("\n^C")
            return 130

    def _confirm_command(self, command: str) -> bool:
        try:
            resp = input(f"\033[33m  Execute: {command}\033[0m\n  [y]es / [n]o / [e]dit > ").strip().lower()
            if resp in ("y", "yes"):
                return True
            if resp in ("e", "edit"):
                edited = input(f"  Edit command: ") or command
                return self._confirm_command(edited)
            return False
        except (EOFError, KeyboardInterrupt):
            return False

    async def _init_direct_mode(self):
        llama_url = os.environ.get("OSA_LLAMA_SWAP_URL", "http://127.0.0.1:8080")
        config = RouterConfig(llama_swap_url=llama_url)
        self.dispatcher = Dispatcher(config)
        healthy = await self.dispatcher.health_check()
        if not healthy:
            print(f"\033[31mError: Cannot reach inference server at {llama_url}\033[0m")
            print("  Start llama-server first.")
            self.dispatcher = None
            return False
        self.direct_mode = True
        return True

    async def _query_ai(self, text: str):
        classification = classify(text)
        model_tag = "qwen" if classification.intent == Intent.CODE else "llama3"
        print(f"\033[90m[{model_tag}]\033[0m ", end="", flush=True)

        if self.direct_mode or not self.client:
            if not self.dispatcher:
                ready = await self._init_direct_mode()
                if not ready:
                    return
            try:
                full_response = ""
                async for chunk in self.dispatcher.stream(
                    text=text,
                    model=classification.model_hint,
                    intent_type=classification.intent.value,
                    conversation=self.conversation[-self.max_context_turns * 2:],
                ):
                    print(chunk, end="", flush=True)
                    full_response += chunk
                print()
            except Exception as e:
                print(f"\n\033[31mError: {e}\033[0m")
                return
        else:
            request = Request(
                text=text,
                model_hint="auto",
                stream=True,
                context_id=self.context_id,
            )
            try:
                full_response = ""
                async for response in self.client.send(request):
                    if response.error:
                        print(f"\n\033[31mError: {response.error}\033[0m")
                        return
                    print(response.text, end="", flush=True)
                    full_response += response.text
                print()
            except (ConnectionResetError, BrokenPipeError):
                print("\n\033[31mConnection to router lost. Reconnecting...\033[0m")
                self.client = None
                return

        self.conversation.append({"role": "user", "content": text})
        self.conversation.append({"role": "assistant", "content": full_response})

        self.history.add(
            user_input=text,
            ai_response=full_response[:2000],
            model_used=model_tag,
            intent=classification.intent.value,
            context_id=self.context_id,
        )

        if classification.intent == Intent.COMMAND and full_response.strip():
            command = full_response.strip().strip("`").strip()
            if command.startswith("```"):
                command = command.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            policy_result = self.policy.evaluate(command)
            if policy_result.verdict == CommandVerdict.BLOCK:
                print(f"\033[31mBlocked: {policy_result.reason}\033[0m")
            elif policy_result.verdict == CommandVerdict.ALLOW:
                self._run_bash(command)
            elif self._confirm_command(command):
                self._run_bash(command)

    async def run(self):
        print(BANNER)

        connected = await self.connect()
        if not connected:
            self.direct_mode = True
            llama_url = os.environ.get("OSA_LLAMA_SWAP_URL", "http://127.0.0.1:8080")
            print(f"\033[33mRouter not available. Using direct mode → {llama_url}\033[0m\n")

        try:
            self.policy.load_custom_policy()
        except Exception:
            pass

        while True:
            try:
                text = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.session.prompt(self._prompt_text())
                )
                text = text.strip()
                if not text:
                    continue

                if self._handle_builtin(text):
                    continue

                if text.startswith("!"):
                    self._run_bash(text[1:])
                    continue

                if self.bash_mode:
                    self._run_bash(text)
                    continue

                if self._looks_like_bash(text):
                    self._run_bash(text)
                    continue

                await self._query_ai(text)

            except EOFError:
                print("\nGoodbye!")
                break
            except KeyboardInterrupt:
                print()
                continue

        if self.client:
            await self.client.close()
        if self.dispatcher:
            await self.dispatcher.close()
        self.history.close()

    @staticmethod
    def _looks_like_bash(text: str) -> bool:
        first_word = text.split()[0] if text.split() else ""
        bash_builtins = {
            "ls", "cd", "pwd", "cat", "grep", "find", "echo", "mkdir",
            "touch", "cp", "mv", "head", "tail", "wc", "sort", "uniq",
            "cut", "awk", "sed", "tar", "gzip", "curl", "wget", "ssh",
            "git", "docker", "python3", "python", "pip", "node", "npm",
        }
        return first_word in bash_builtins


def main():
    shell = OsaShell()
    try:
        asyncio.run(shell.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
