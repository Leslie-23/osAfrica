"""Tests for the intent classifier."""

from osa_core.router.classifier import Intent, classify


class TestClassifier:
    def test_code_request_detected(self, sample_code_request):
        result = classify(sample_code_request)
        assert result.intent == Intent.CODE
        assert result.model_hint == "qwen-coder"

    def test_command_request_detected(self, sample_command_request):
        result = classify(sample_command_request)
        assert result.intent == Intent.COMMAND
        assert result.model_hint == "llama3-8b"

    def test_general_request_detected(self, sample_general_request):
        result = classify(sample_general_request)
        assert result.intent == Intent.GENERAL
        assert result.model_hint == "llama3-8b"

    def test_code_with_backticks(self):
        text = "fix this code:\n```python\ndef foo():\n    return bar\n```"
        result = classify(text)
        assert result.intent == Intent.CODE

    def test_code_with_file_extension(self):
        result = classify("explain what main.py does")
        assert result.intent == Intent.CODE

    def test_command_install(self):
        result = classify("install nginx")
        assert result.intent == Intent.COMMAND

    def test_command_list_files(self):
        result = classify("list files in the home directory")
        assert result.intent == Intent.COMMAND

    def test_context_boosts_code(self):
        result = classify("explain this", context={"in_code_file": True})
        assert result.intent == Intent.CODE

    def test_error_message_routes_to_code(self):
        text = "I'm getting this traceback: NameError: name 'foo' is not defined"
        result = classify(text)
        assert result.intent == Intent.CODE

    def test_classification_has_reason(self):
        result = classify("write a Python script to sort a CSV")
        assert result.reason
        assert result.confidence > 0
