from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class RouterConfig(BaseSettings):
    model_config = {"env_prefix": "OSA_"}

    socket_path: Path = Path("/run/osa/router.sock")
    llama_swap_url: str = "http://127.0.0.1:8080"
    llama3_model: str = "llama3-8b"
    qwen_model: str = "qwen-coder"
    default_model: str = "llama3-8b"
    max_context_tokens: int = 4096
    stream_responses: bool = True
    code_confidence_threshold: float = 0.6
    request_timeout: float = 120.0

    system_prompt_general: str = (
        "You are osAfrica, an AI-native Linux operating system assistant. "
        "You help users manage their system through natural language. "
        "When asked to perform system operations, output the exact Linux command. "
        "Be concise and precise."
    )
    system_prompt_code: str = (
        "You are osAfrica Code, an expert programming assistant built into the "
        "osAfrica operating system. You write clean, correct, well-structured code. "
        "When generating scripts or programs, include proper error handling and "
        "follow language best practices."
    )
    system_prompt_command: str = (
        "You are a Linux command translator. Convert the user's natural language "
        "request into a single bash command or short pipeline. Output ONLY the "
        "command, no explanation. Target: Debian Linux with standard GNU coreutils."
    )
