"""Tests for the router daemon configuration and dispatch logic."""

from osa_core.router.config import RouterConfig
from osa_core.router.classifier import Intent, classify


class TestRouterConfig:
    def test_default_config(self):
        config = RouterConfig()
        assert config.llama3_model == "llama3-8b"
        assert config.qwen_model == "qwen-coder"
        assert config.stream_responses is True
        assert config.max_context_tokens == 4096

    def test_system_prompts_exist(self):
        config = RouterConfig()
        assert "osAfrica" in config.system_prompt_general
        assert "code" in config.system_prompt_code.lower()
        assert "command" in config.system_prompt_command.lower()

    def test_model_routing_code(self):
        classification = classify("write a Python function to parse JSON")
        assert classification.intent == Intent.CODE
        assert classification.model_hint == "qwen-coder"

    def test_model_routing_general(self):
        classification = classify("what time is it")
        assert classification.intent == Intent.GENERAL
        assert classification.model_hint == "llama3-8b"

    def test_model_routing_command(self):
        classification = classify("show me disk space usage")
        assert classification.intent == Intent.COMMAND
        assert classification.model_hint == "llama3-8b"
