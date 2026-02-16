"""Shared fixtures for ai-lint tests."""

import json
import shutil
from pathlib import Path

import pytest


@pytest.fixture()
def config_dir(tmp_path, monkeypatch):
    """Point CONFIG_DIR and POLICY_FILE at a temp directory."""
    d = tmp_path / ".ai-lint"
    d.mkdir()
    monkeypatch.setattr("ai_lint.config.CONFIG_DIR", d)
    monkeypatch.setattr("ai_lint.config.POLICY_FILE", d / "policy.md")
    return d


@pytest.fixture()
def installed_policy(config_dir):
    """Copy the 'self' policy template into the config dir."""
    templates = Path(__file__).resolve().parent.parent / "ai_lint" / "templates"
    shutil.copy2(templates / "policy_self.md", config_dir / "policy.md")
    return config_dir / "policy.md"


@pytest.fixture()
def claude_projects_dir(tmp_path, monkeypatch):
    """Point CLAUDE_PROJECTS_DIR at a temp directory."""
    d = tmp_path / ".claude" / "projects"
    d.mkdir(parents=True)
    monkeypatch.setattr("ai_lint.sessions.CLAUDE_PROJECTS_DIR", d)
    return d


@pytest.fixture()
def claude_settings_dir(tmp_path, monkeypatch):
    """Point CLAUDE_SETTINGS at a temp file."""
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("ai_lint.setup_hook.CLAUDE_SETTINGS", settings_file)
    return settings_file


@pytest.fixture()
def sample_jsonl_session(claude_projects_dir):
    """Create a realistic session JSONL file and return its path."""
    project_dir = claude_projects_dir / "-Users-dev-myproject"
    project_dir.mkdir()
    session_file = project_dir / "abc12345-1111-2222-3333-444444444444.jsonl"

    entries = [
        {
            "type": "user",
            "cwd": "/Users/dev/myproject",
            "timestamp": "2025-06-15T10:30:00Z",
            "message": {
                "role": "user",
                "content": "Help me refactor the auth module to use JWT tokens",
            },
        },
        {
            "type": "assistant",
            "timestamp": "2025-06-15T10:30:05Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll help you refactor the auth module. Let me first look at the current code."},
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "/Users/dev/myproject/auth.py"}},
                ],
            },
        },
        {
            "type": "assistant",
            "timestamp": "2025-06-15T10:30:10Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_result", "content": "class Auth:\n    def login(self):\n        pass"},
                ],
            },
        },
        {
            "type": "user",
            "timestamp": "2025-06-15T10:31:00Z",
            "message": {
                "role": "user",
                "content": "Looks good, but can you also add refresh token support?",
            },
        },
        {
            "type": "assistant",
            "timestamp": "2025-06-15T10:31:05Z",
            "message": {
                "role": "assistant",
                "content": "Sure! I'll add refresh token rotation as well.",
            },
        },
        {
            "type": "system",
            "timestamp": "2025-06-15T10:32:00Z",
            "message": {"role": "system", "content": "Session ended."},
        },
    ]

    lines = [json.dumps(e) for e in entries]
    session_file.write_text("\n".join(lines) + "\n")
    return session_file


@pytest.fixture()
def sample_verdicts():
    """Return a dict matching the run_check output format."""
    return {
        "verdicts": [
            {"category": "Security", "rule": "No credential exposure", "verdict": "PASS", "reasoning": "No secrets found."},
            {"category": "Security", "rule": "No sensitive data in prompts", "verdict": "PASS", "reasoning": "No PII detected."},
            {"category": "Developer Engagement", "rule": "Understanding before delegation", "verdict": "PASS", "reasoning": "Developer showed understanding."},
            {"category": "Developer Engagement", "rule": "Review before acceptance", "verdict": "FAIL", "reasoning": "Developer did not review."},
            {"category": "Process Discipline", "rule": "Testing discussed or performed", "verdict": "SKIP", "reasoning": "No code written."},
        ],
        "summary": "Mostly compliant session.",
    }


@pytest.fixture()
def sample_insights():
    """Return a dict matching the extract_insights output format."""
    return {
        "what_went_well": [
            {"pattern": "Clear problem description", "evidence": "User described expected vs actual behavior"},
        ],
        "what_to_improve": [
            {"pattern": "No testing discussed", "evidence": "Files written with no test run"},
        ],
        "notable": [],
    }
