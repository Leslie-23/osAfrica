"""Tests for the AI shell components."""

from osa_core.shell.intent_parser import (
    CodeBlock,
    ResponseType,
    extract_single_command,
    parse_response,
)
from osa_core.shell.history import ShellHistory
from pathlib import Path
import tempfile


class TestIntentParser:
    def test_parse_single_command(self):
        result = parse_response("ls -la /home")
        assert result.response_type in (ResponseType.COMMAND, ResponseType.EXPLANATION)

    def test_parse_code_block(self):
        text = '```python\ndef hello():\n    print("world")\n```'
        result = parse_response(text)
        assert result.response_type == ResponseType.CODE_BLOCK
        assert len(result.code_blocks) == 1
        assert result.code_blocks[0].language == "python"

    def test_parse_bash_code_block(self):
        text = "```bash\nfind . -name '*.py' -mtime 0\n```"
        result = parse_response(text)
        assert len(result.commands) >= 1
        assert "find" in result.commands[0]

    def test_parse_mixed_response(self):
        text = "Here's how to do it:\n```bash\nls -la\n```\nThis lists all files."
        result = parse_response(text)
        assert result.response_type == ResponseType.MIXED

    def test_extract_single_command_basic(self):
        assert extract_single_command("ls -la") == "ls -la"

    def test_extract_single_command_backticks(self):
        assert extract_single_command("`ls -la`") == "ls -la"

    def test_extract_single_command_dollar(self):
        assert extract_single_command("$ ls -la") == "ls -la"

    def test_extract_single_command_code_block(self):
        text = "```bash\nfind . -name '*.py'\n```"
        cmd = extract_single_command(text)
        assert cmd is not None
        assert "find" in cmd


class TestShellHistory:
    def test_add_and_search(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            history = ShellHistory(db_path)
            history.add("find all python files", command_executed="find . -name '*.py'")
            history.add("list files", command_executed="ls -la")

            results = history.search("python")
            assert len(results) >= 1
            assert "python" in results[0].user_input.lower()

            history.close()

    def test_recent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            history = ShellHistory(db_path)
            for i in range(5):
                history.add(f"command {i}")

            recent = history.recent(3)
            assert len(recent) == 3
            history.close()

    def test_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            history = ShellHistory(db_path)
            history.add("test", intent="code")
            history.add("test2", intent="command")

            stats = history.stats()
            assert stats["total"] == 2
            history.close()
