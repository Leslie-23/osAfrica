"""Interactive coding assistant powered by Qwen Coder."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from osa_core.common.ipc import IPCClient
    from osa_core.router.dispatch import Dispatcher


class CodeAssistant:
    def __init__(self, router_client: IPCClient | None = None, dispatcher: Dispatcher | None = None):
        self.router = router_client
        self.dispatcher = dispatcher

    async def _query(self, prompt: str) -> str:
        if self.dispatcher:
            return await self.dispatcher.complete(text=prompt, model="qwen-coder", intent_type="code")
        if self.router:
            return await self.router.query(prompt, model_hint="code")
        raise RuntimeError("No router or dispatcher configured")

    async def explain_file(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        if path.stat().st_size > 100_000:
            return "File too large for single-pass analysis (>100KB). Try a specific function or section."

        content = path.read_text(errors="replace")
        lang = path.suffix.lstrip(".")

        prompt = (
            f"Explain this {lang} file concisely. Cover: purpose, key functions/classes, "
            f"dependencies, and any notable patterns or issues.\n\n"
            f"File: {path.name}\n```{lang}\n{content}\n```"
        )
        return await self._query(prompt)

    async def review_code(self, code: str, language: str = "") -> str:
        prompt = (
            "Review this code for bugs, security issues, performance problems, and "
            "style improvements. Be specific and actionable.\n\n"
            f"```{language}\n{code}\n```"
        )
        return await self._query(prompt)

    async def generate_code(self, description: str, language: str = "python") -> str:
        prompt = (
            f"Generate {language} code for the following requirement. Write clean, "
            f"production-quality code with proper error handling.\n\n"
            f"Requirement: {description}"
        )
        return await self._query(prompt)

    async def debug_error(self, error_text: str, code_context: str = "") -> str:
        prompt = "Diagnose this error and provide a fix.\n\n"
        if code_context:
            prompt += f"Code:\n```\n{code_context}\n```\n\n"
        prompt += f"Error:\n```\n{error_text}\n```"
        return await self._query(prompt)

    async def explain_command(self, command: str) -> str:
        prompt = (
            f"Explain this Linux command in detail. Break down each flag and component:\n\n"
            f"```bash\n{command}\n```"
        )
        return await self._query(prompt)

    async def generate_script(self, task: str, shell: str = "bash") -> str:
        prompt = (
            f"Write a {shell} script for this task. Include error handling, "
            f"comments for complex parts, and make it idempotent where possible.\n\n"
            f"Task: {task}"
        )
        return await self._query(prompt)

    async def refactor(self, code: str, instruction: str, language: str = "") -> str:
        prompt = (
            f"Refactor this code according to the instruction. Show only the "
            f"refactored code, no explanation unless the change is non-obvious.\n\n"
            f"Instruction: {instruction}\n\n"
            f"```{language}\n{code}\n```"
        )
        return await self._query(prompt)
