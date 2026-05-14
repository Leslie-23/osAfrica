"""Code review engine — analyzes diffs and files for issues."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from osa_core.common.ipc import IPCClient
    from osa_core.router.dispatch import Dispatcher


@dataclass
class ReviewResult:
    file_path: str
    issues: list[str]
    suggestions: list[str]
    severity: str
    raw_response: str


class CodeReviewer:
    def __init__(self, router_client: IPCClient | None = None, dispatcher: Dispatcher | None = None):
        self.router = router_client
        self.dispatcher = dispatcher

    async def _query(self, prompt: str) -> str:
        if self.dispatcher:
            return await self.dispatcher.complete(text=prompt, model="qwen-coder", intent_type="code")
        if self.router:
            return await self.router.query(prompt, model_hint="code")
        raise RuntimeError("No router or dispatcher configured")

    async def review_file(self, file_path: str) -> ReviewResult:
        path = Path(file_path)
        if not path.exists():
            return ReviewResult(file_path, ["File not found"], [], "error", "")

        content = path.read_text(errors="replace")
        lang = path.suffix.lstrip(".")

        prompt = (
            f"Review this {lang} file. Report:\n"
            "1. BUGS: actual bugs or logic errors\n"
            "2. SECURITY: vulnerabilities (injection, auth, data exposure)\n"
            "3. PERFORMANCE: inefficiencies or scaling issues\n"
            "4. STYLE: naming, structure, readability improvements\n\n"
            "Be specific with line references. Skip categories with no issues.\n\n"
            f"```{lang}\n{content}\n```"
        )

        response = await self._query(prompt)
        return self._parse_review(file_path, response)

    async def review_diff(self, diff: str = "") -> str:
        if not diff:
            try:
                result = subprocess.run(
                    ["git", "diff", "--cached"],
                    capture_output=True, text=True, timeout=10,
                )
                diff = result.stdout
                if not diff:
                    result = subprocess.run(
                        ["git", "diff"],
                        capture_output=True, text=True, timeout=10,
                    )
                    diff = result.stdout
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return "Could not get git diff"

        if not diff.strip():
            return "No changes to review."

        prompt = (
            "Review this git diff. Focus on:\n"
            "1. Bugs introduced by the changes\n"
            "2. Security implications\n"
            "3. Missing edge cases or error handling\n"
            "4. Whether the changes are complete and consistent\n\n"
            f"```diff\n{diff[:8000]}\n```"
        )
        return await self.router.query(prompt, model_hint="code")

    def _parse_review(self, file_path: str, response: str) -> ReviewResult:
        issues = []
        suggestions = []
        severity = "info"

        for line in response.splitlines():
            line = line.strip()
            upper = line.upper()
            if any(w in upper for w in ("BUG", "ERROR", "VULNERABILITY", "SECURITY")):
                issues.append(line)
                severity = "high" if "SECURITY" in upper else "medium"
            elif any(w in upper for w in ("SUGGEST", "IMPROVE", "CONSIDER", "STYLE")):
                suggestions.append(line)
            elif line.startswith(("-", "*", "•")) and len(line) > 3:
                suggestions.append(line)

        return ReviewResult(
            file_path=file_path,
            issues=issues,
            suggestions=suggestions,
            severity=severity,
            raw_response=response,
        )
