"""Tests for the command permission policy."""

from osa_core.common.permissions import CommandPolicy, CommandVerdict, SafetyLevel


class TestCommandPolicy:
    def setup_method(self):
        self.policy = CommandPolicy(SafetyLevel.NORMAL)

    def test_block_rm_rf_root(self):
        result = self.policy.evaluate("rm -rf /")
        assert result.verdict == CommandVerdict.BLOCK

    def test_block_dd_to_disk(self):
        result = self.policy.evaluate("dd if=/dev/zero of=/dev/sda")
        assert result.verdict == CommandVerdict.BLOCK

    def test_block_fork_bomb(self):
        result = self.policy.evaluate(":(){ :|:& };:")
        assert result.verdict == CommandVerdict.BLOCK

    def test_allow_ls(self):
        result = self.policy.evaluate("ls -la")
        assert result.verdict == CommandVerdict.ALLOW

    def test_allow_grep(self):
        result = self.policy.evaluate("grep -r pattern .")
        assert result.verdict == CommandVerdict.ALLOW

    def test_allow_ps(self):
        result = self.policy.evaluate("ps aux")
        assert result.verdict == CommandVerdict.ALLOW

    def test_confirm_rm_rf(self):
        result = self.policy.evaluate("rm -rf ./build")
        assert result.verdict == CommandVerdict.CONFIRM

    def test_confirm_systemctl_stop(self):
        result = self.policy.evaluate("systemctl stop nginx")
        assert result.verdict == CommandVerdict.CONFIRM

    def test_confirm_reboot(self):
        result = self.policy.evaluate("reboot")
        assert result.verdict == CommandVerdict.CONFIRM

    def test_safe_mode_confirms_everything(self):
        policy = CommandPolicy(SafetyLevel.SAFE)
        result = policy.evaluate("ls -la")
        assert result.verdict == CommandVerdict.CONFIRM

    def test_expert_mode_allows_unknown(self):
        policy = CommandPolicy(SafetyLevel.EXPERT)
        result = policy.evaluate("some-custom-tool --flag")
        assert result.verdict == CommandVerdict.ALLOW

    def test_expert_mode_still_confirms_destructive(self):
        policy = CommandPolicy(SafetyLevel.EXPERT)
        result = policy.evaluate("rm -rf /tmp/build")
        assert result.verdict == CommandVerdict.CONFIRM

    def test_unknown_command_confirms_in_normal(self):
        result = self.policy.evaluate("mysterious-command --do-stuff")
        assert result.verdict == CommandVerdict.CONFIRM
