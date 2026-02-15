"""Tests for ai_lint.cli via Click's CliRunner."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from ai_lint.cli import cli


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def full_setup(config_dir, installed_policy, claude_projects_dir, sample_jsonl_session, claude_settings_dir):
    """Set up config, policy, sessions, and settings for CLI tests."""
    return {
        "config_dir": config_dir,
        "policy": installed_policy,
        "projects": claude_projects_dir,
        "session": sample_jsonl_session,
        "settings": claude_settings_dir,
    }


# -- init --


class TestInit:
    @pytest.mark.parametrize("choice", ["1", "2", "self", "team"])
    def test_all_persona_choices(self, runner, config_dir, claude_settings_dir, monkeypatch, choice):
        monkeypatch.setattr("ai_lint.cli.check_claude_installed", lambda: True)
        monkeypatch.setattr("ai_lint.cli.is_hook_installed", lambda: False)
        monkeypatch.setattr("ai_lint.setup_hook.CLAUDE_SETTINGS", claude_settings_dir)
        result = runner.invoke(cli, ["init"], input=f"{choice}\nn\n")
        assert result.exit_code == 0
        assert "Done!" in result.output

    def test_claude_not_found_warning(self, runner, config_dir, claude_settings_dir, monkeypatch):
        monkeypatch.setattr("ai_lint.cli.check_claude_installed", lambda: False)
        monkeypatch.setattr("ai_lint.cli.is_hook_installed", lambda: False)
        monkeypatch.setattr("ai_lint.setup_hook.CLAUDE_SETTINGS", claude_settings_dir)
        result = runner.invoke(cli, ["init"], input="1\nn\n")
        assert "[!!] claude CLI not found" in result.output

    def test_overwrite_existing_policy(self, runner, installed_policy, config_dir, claude_settings_dir, monkeypatch):
        monkeypatch.setattr("ai_lint.cli.check_claude_installed", lambda: True)
        monkeypatch.setattr("ai_lint.cli.is_hook_installed", lambda: True)
        result = runner.invoke(cli, ["init"], input="2\ny\n")
        assert result.exit_code == 0
        assert "Installed 'team' policy" in result.output

    def test_keep_existing_policy(self, runner, installed_policy, config_dir, claude_settings_dir, monkeypatch):
        monkeypatch.setattr("ai_lint.cli.check_claude_installed", lambda: True)
        monkeypatch.setattr("ai_lint.cli.is_hook_installed", lambda: True)
        result = runner.invoke(cli, ["init"], input="1\nn\n")
        assert "Keeping existing policy" in result.output

    def test_install_hook_yes(self, runner, config_dir, claude_settings_dir, monkeypatch):
        monkeypatch.setattr("ai_lint.cli.check_claude_installed", lambda: True)
        monkeypatch.setattr("ai_lint.cli.is_hook_installed", lambda: False)
        monkeypatch.setattr("ai_lint.setup_hook.CLAUDE_SETTINGS", claude_settings_dir)
        result = runner.invoke(cli, ["init"], input="1\ny\n")
        assert result.exit_code == 0
        assert "Installed SessionEnd hook" in result.output

    def test_skip_hook(self, runner, config_dir, claude_settings_dir, monkeypatch):
        monkeypatch.setattr("ai_lint.cli.check_claude_installed", lambda: True)
        monkeypatch.setattr("ai_lint.cli.is_hook_installed", lambda: False)
        monkeypatch.setattr("ai_lint.setup_hook.CLAUDE_SETTINGS", claude_settings_dir)
        result = runner.invoke(cli, ["init"], input="1\nn\n")
        assert "Skipped hook installation" in result.output


# -- check --


class TestCheck:
    def test_no_policy_error(self, runner, config_dir):
        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 1
        assert "No policy found" in result.output

    def test_no_sessions_error(self, runner, installed_policy, claude_projects_dir):
        result = runner.invoke(cli, ["check", "--last"])
        assert result.exit_code == 1
        assert "No sessions found" in result.output

    def test_last_flag(self, runner, full_setup, monkeypatch):
        fake_result = {
            "verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}],
            "summary": "good",
        }
        monkeypatch.setattr("ai_lint.cli.run_check", lambda t, p: fake_result)
        result = runner.invoke(cli, ["check", "--last"])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_quiet_flag(self, runner, full_setup, monkeypatch):
        fake_result = {
            "verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}],
            "summary": "good",
        }
        monkeypatch.setattr("ai_lint.cli.run_check", lambda t, p: fake_result)
        result = runner.invoke(cli, ["check", "--last", "--quiet"])
        assert result.exit_code == 0
        assert "Parsing session" not in result.output

    def test_session_picker(self, runner, full_setup, monkeypatch):
        fake_result = {
            "verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}],
            "summary": "good",
        }
        monkeypatch.setattr("ai_lint.cli.run_check", lambda t, p: fake_result)
        result = runner.invoke(cli, ["check"], input="1\n")
        assert result.exit_code == 0
        assert "Recent sessions" in result.output

    def test_runtime_error(self, runner, full_setup, monkeypatch):
        def fail_check(t, p):
            raise RuntimeError("LLM exploded")

        monkeypatch.setattr("ai_lint.cli.run_check", fail_check)
        result = runner.invoke(cli, ["check", "--last"])
        assert result.exit_code == 1
        assert "LLM exploded" in result.output

    def test_empty_session(self, runner, installed_policy, claude_projects_dir):
        proj = claude_projects_dir / "proj"
        proj.mkdir()
        (proj / "empty.jsonl").write_text("{}\n")
        result = runner.invoke(cli, ["check", "--last"])
        assert result.exit_code == 0
        assert "no messages" in result.output


# -- report --


class TestReport:
    def test_no_policy_error(self, runner, config_dir):
        result = runner.invoke(cli, ["report"])
        assert result.exit_code == 1
        assert "No policy found" in result.output

    def test_no_sessions_error(self, runner, installed_policy, claude_projects_dir):
        result = runner.invoke(cli, ["report"])
        assert result.exit_code == 1
        assert "No sessions found" in result.output

    def test_count_flag(self, runner, full_setup, monkeypatch):
        fake_result = {
            "verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}],
            "summary": "good",
        }
        monkeypatch.setattr("ai_lint.cli.run_check", lambda t, p: fake_result)
        result = runner.invoke(cli, ["report", "-n", "1"])
        assert result.exit_code == 0
        assert "Checked 1 sessions" in result.output

    def test_output_flag(self, runner, full_setup, monkeypatch, tmp_path):
        fake_result = {
            "verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}],
            "summary": "good",
        }
        monkeypatch.setattr("ai_lint.cli.run_check", lambda t, p: fake_result)
        outfile = tmp_path / "report.md"
        result = runner.invoke(cli, ["report", "-n", "1", "-o", str(outfile)])
        assert result.exit_code == 0
        assert outfile.exists()
        assert "ai-lint Compliance Report" in outfile.read_text()

    def test_default_filename(self, runner, full_setup, monkeypatch, tmp_path, monkeypatch_cwd=None):
        fake_result = {
            "verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}],
            "summary": "good",
        }
        monkeypatch.setattr("ai_lint.cli.run_check", lambda t, p: fake_result)
        result = runner.invoke(cli, ["report", "-n", "1"])
        assert result.exit_code == 0
        assert "Report saved to ai-lint-report-" in result.output

    def test_runtime_error_continues(self, runner, full_setup, monkeypatch):
        call_count = [0]

        def flaky_check(t, p):
            call_count[0] += 1
            raise RuntimeError("oops")

        monkeypatch.setattr("ai_lint.cli.run_check", flaky_check)
        result = runner.invoke(cli, ["report", "-n", "1"])
        assert result.exit_code == 0
        assert "No sessions had messages" in result.output


# -- policy --


class TestPolicy:
    def test_no_policy_error(self, runner, config_dir):
        result = runner.invoke(cli, ["policy"])
        assert result.exit_code == 1
        assert "No policy found" in result.output

    def test_opens_editor(self, runner, installed_policy, monkeypatch):
        monkeypatch.setattr("os.execvp", lambda prog, args: None)
        result = runner.invoke(cli, ["policy"])
        assert result.exit_code == 0


# -- hook --


class TestHook:
    def test_install(self, runner, claude_settings_dir):
        result = runner.invoke(cli, ["hook", "install"])
        assert result.exit_code == 0
        assert "Installed" in result.output

    def test_uninstall(self, runner, claude_settings_dir):
        runner.invoke(cli, ["hook", "install"])
        result = runner.invoke(cli, ["hook", "uninstall"])
        assert result.exit_code == 0
        assert "Removed" in result.output


# -- version --


class TestVersion:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert "0.2.0" in result.output


# -- help --


class TestHelp:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert "ai-lint" in result.output
        assert result.exit_code == 0
