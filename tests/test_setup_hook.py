"""Tests for ai_lint.setup_hook."""

import json

import pytest

from ai_lint.setup_hook import (
    HOOK_COMMAND_TTY,
    HOOK_ENTRY,
    install_hook,
    is_hook_installed,
    read_settings,
    uninstall_hook,
    write_settings,
)


class TestReadSettings:
    def test_no_file(self, claude_settings_dir):
        assert read_settings() == {}

    def test_reads_json(self, claude_settings_dir):
        claude_settings_dir.write_text(json.dumps({"foo": "bar"}))
        assert read_settings() == {"foo": "bar"}


class TestWriteSettings:
    def test_creates_file(self, claude_settings_dir):
        write_settings({"hello": "world"})
        assert claude_settings_dir.exists()
        data = json.loads(claude_settings_dir.read_text())
        assert data["hello"] == "world"

    def test_creates_parent_dirs(self, tmp_path, monkeypatch):
        f = tmp_path / "deep" / "nested" / "settings.json"
        monkeypatch.setattr("ai_lint.setup_hook.CLAUDE_SETTINGS", f)
        write_settings({"ok": True})
        assert f.exists()


class TestIsHookInstalled:
    def test_not_installed(self, claude_settings_dir):
        assert is_hook_installed() is False

    def test_empty_settings(self, claude_settings_dir):
        claude_settings_dir.write_text("{}")
        assert is_hook_installed() is False

    def test_installed(self, claude_settings_dir):
        settings = {"hooks": {"SessionEnd": [HOOK_ENTRY]}}
        claude_settings_dir.write_text(json.dumps(settings))
        assert is_hook_installed() is True

    def test_other_hooks_only(self, claude_settings_dir):
        settings = {
            "hooks": {
                "SessionEnd": [
                    {"matcher": "", "hooks": [{"type": "command", "command": "other-tool run"}]}
                ]
            }
        }
        claude_settings_dir.write_text(json.dumps(settings))
        assert is_hook_installed() is False


class TestInstallHook:
    def test_installs_to_empty(self, claude_settings_dir, capsys):
        install_hook()
        data = json.loads(claude_settings_dir.read_text())
        assert len(data["hooks"]["SessionEnd"]) == 1
        assert data["hooks"]["SessionEnd"][0]["hooks"][0]["command"] == HOOK_COMMAND_TTY

    def test_idempotent(self, claude_settings_dir, capsys):
        install_hook()
        install_hook()
        data = json.loads(claude_settings_dir.read_text())
        assert len(data["hooks"]["SessionEnd"]) == 1
        captured = capsys.readouterr()
        assert "Updated" in captured.out

    def test_preserves_other_hooks(self, claude_settings_dir):
        other_hook = {"matcher": "", "hooks": [{"type": "command", "command": "echo done"}]}
        settings = {"hooks": {"SessionEnd": [other_hook], "PreTool": [{"matcher": "Bash"}]}}
        claude_settings_dir.write_text(json.dumps(settings))
        install_hook()
        data = json.loads(claude_settings_dir.read_text())
        assert len(data["hooks"]["SessionEnd"]) == 2
        assert "PreTool" in data["hooks"]


class TestUninstallHook:
    def test_removes_hook(self, claude_settings_dir, capsys):
        install_hook()
        uninstall_hook()
        data = json.loads(claude_settings_dir.read_text())
        assert len(data["hooks"]["SessionEnd"]) == 0
        captured = capsys.readouterr()
        assert "Removed" in captured.out

    def test_not_installed(self, claude_settings_dir, capsys):
        uninstall_hook()
        captured = capsys.readouterr()
        assert "not installed" in captured.out

    def test_preserves_other_hooks_on_uninstall(self, claude_settings_dir):
        other_hook = {"matcher": "", "hooks": [{"type": "command", "command": "echo done"}]}
        settings = {"hooks": {"SessionEnd": [other_hook, HOOK_ENTRY]}}
        claude_settings_dir.write_text(json.dumps(settings))
        uninstall_hook()
        data = json.loads(claude_settings_dir.read_text())
        assert len(data["hooks"]["SessionEnd"]) == 1
        assert data["hooks"]["SessionEnd"][0]["hooks"][0]["command"] == "echo done"
