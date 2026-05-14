"""Sandboxed command execution for AI-generated commands."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecutionResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    sandboxed: bool


BWRAP_AVAILABLE = shutil.which("bwrap") is not None


def _build_bwrap_command(
    command: str,
    cwd: str,
    allow_network: bool = False,
    writable_paths: list[str] | None = None,
) -> list[str]:
    writable = writable_paths or [str(Path.home()), "/tmp"]

    args = [
        "bwrap",
        "--ro-bind", "/", "/",
        "--dev", "/dev",
        "--proc", "/proc",
        "--tmpfs", "/tmp",
    ]

    for path in writable:
        if os.path.exists(path):
            args.extend(["--bind", path, path])

    if not allow_network:
        args.append("--unshare-net")

    args.extend([
        "--unshare-pid",
        "--die-with-parent",
        "--chdir", cwd,
        "--",
        "/bin/bash", "-c", command,
    ])

    return args


def execute_sandboxed(
    command: str,
    cwd: str | None = None,
    timeout: int = 60,
    allow_network: bool = False,
    sandbox: bool = True,
) -> ExecutionResult:
    work_dir = cwd or str(Path.cwd())
    use_sandbox = sandbox and BWRAP_AVAILABLE

    if use_sandbox:
        full_cmd = _build_bwrap_command(command, work_dir, allow_network)
    else:
        full_cmd = ["/bin/bash", "-c", command]

    start = time.monotonic()
    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=work_dir if not use_sandbox else None,
            env={**os.environ, "OSA_SHELL": "1", "TERM": "xterm-256color"},
        )
        duration = int((time.monotonic() - start) * 1000)
        return ExecutionResult(
            command=command,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration,
            sandboxed=use_sandbox,
        )
    except subprocess.TimeoutExpired:
        duration = int((time.monotonic() - start) * 1000)
        return ExecutionResult(
            command=command,
            exit_code=124,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            duration_ms=duration,
            sandboxed=use_sandbox,
        )


async def execute_sandboxed_async(
    command: str,
    cwd: str | None = None,
    timeout: int = 60,
    allow_network: bool = False,
    sandbox: bool = True,
) -> ExecutionResult:
    work_dir = cwd or str(Path.cwd())
    use_sandbox = sandbox and BWRAP_AVAILABLE

    if use_sandbox:
        full_cmd = _build_bwrap_command(command, work_dir, allow_network)
        shell_cmd = " ".join(full_cmd)
    else:
        shell_cmd = command

    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_shell(
            shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir if not use_sandbox else None,
            env={**os.environ, "OSA_SHELL": "1"},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        duration = int((time.monotonic() - start) * 1000)
        return ExecutionResult(
            command=command,
            exit_code=proc.returncode or 0,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            duration_ms=duration,
            sandboxed=use_sandbox,
        )
    except asyncio.TimeoutError:
        duration = int((time.monotonic() - start) * 1000)
        proc.kill()
        return ExecutionResult(
            command=command,
            exit_code=124,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            duration_ms=duration,
            sandboxed=use_sandbox,
        )
