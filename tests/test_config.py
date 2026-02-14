"""Tests for ai_lint.config."""

import os
from pathlib import Path

import pytest

from ai_lint.config import (
    PERSONAS,
    ensure_config_dir,
    install_policy,
    open_policy_in_editor,
    policy_exists,
    read_policy,
)


class TestEnsureConfigDir:
    def test_creates_directory(self, tmp_path, monkeypatch):
        d = tmp_path / ".ai-lint"
        monkeypatch.setattr("ai_lint.config.CONFIG_DIR", d)
        assert not d.exists()
        ensure_config_dir()
        assert d.is_dir()

    def test_idempotent(self, config_dir):
        ensure_config_dir()
        ensure_config_dir()
        assert config_dir.is_dir()


class TestPolicyExists:
    def test_no_policy(self, config_dir):
        assert not policy_exists()

    def test_with_policy(self, installed_policy):
        assert policy_exists()


class TestInstallPolicy:
    @pytest.mark.parametrize("persona", ["self", "team", "parent"])
    def test_installs_all_personas(self, config_dir, persona, monkeypatch):
        install_policy(persona)
        policy_file = config_dir / "policy.md"
        assert policy_file.exists()
        content = policy_file.read_text()
        assert len(content) > 50

    def test_invalid_persona_raises(self, config_dir):
        with pytest.raises(ValueError, match="Unknown persona"):
            install_policy("hacker")

    def test_overwrites_existing(self, installed_policy, config_dir):
        original = installed_policy.read_text()
        install_policy("team")
        assert installed_policy.read_text() != original

    def test_creates_dir_if_missing(self, tmp_path, monkeypatch):
        d = tmp_path / "new" / ".ai-lint"
        monkeypatch.setattr("ai_lint.config.CONFIG_DIR", d)
        monkeypatch.setattr("ai_lint.config.POLICY_FILE", d / "policy.md")
        install_policy("self")
        assert (d / "policy.md").exists()


class TestReadPolicy:
    def test_reads_content(self, installed_policy):
        text = read_policy()
        assert "AI Usage Policy" in text

    def test_no_policy_raises(self, config_dir):
        with pytest.raises(FileNotFoundError, match="No policy found"):
            read_policy()


class TestOpenPolicyInEditor:
    def test_no_policy_raises(self, config_dir):
        with pytest.raises(FileNotFoundError, match="No policy found"):
            open_policy_in_editor()

    def test_uses_editor_env(self, installed_policy, monkeypatch):
        calls = []
        monkeypatch.setenv("EDITOR", "/usr/bin/vim")
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.setattr("os.execvp", lambda prog, args: calls.append((prog, args)))
        open_policy_in_editor()
        assert calls[0][0] == "/usr/bin/vim"

    def test_uses_visual_fallback(self, installed_policy, monkeypatch):
        calls = []
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.setenv("VISUAL", "/usr/bin/code")
        monkeypatch.setattr("os.execvp", lambda prog, args: calls.append((prog, args)))
        open_policy_in_editor()
        assert calls[0][0] == "/usr/bin/code"

    def test_defaults_to_nano(self, installed_policy, monkeypatch):
        calls = []
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.setattr("os.execvp", lambda prog, args: calls.append((prog, args)))
        open_policy_in_editor()
        assert calls[0][0] == "nano"


class TestPersonas:
    def test_all_personas_have_templates(self):
        templates_dir = Path(__file__).resolve().parent.parent / "ai_lint" / "templates"
        for persona, filename in PERSONAS.items():
            assert (templates_dir / filename).exists(), f"Missing template for {persona}"

    def test_persona_count(self):
        assert len(PERSONAS) == 3
