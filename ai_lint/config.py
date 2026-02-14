"""Manage ~/.ai-lint/ configuration directory and policy.md file."""

import os
import shutil
from pathlib import Path

CONFIG_DIR = Path.home() / ".ai-lint"
POLICY_FILE = CONFIG_DIR / "policy.md"
TEMPLATES_DIR = Path(__file__).parent / "templates"

PERSONAS = {
    "self": "policy_self.md",
    "team": "policy_team.md",
    "parent": "policy_parent.md",
}


def ensure_config_dir():
    """Create ~/.ai-lint/ if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def policy_exists() -> bool:
    return POLICY_FILE.exists()


def install_policy(persona: str):
    """Copy the template policy for the given persona to ~/.ai-lint/policy.md."""
    if persona not in PERSONAS:
        raise ValueError(f"Unknown persona: {persona}. Choose from: {list(PERSONAS.keys())}")
    ensure_config_dir()
    template = TEMPLATES_DIR / PERSONAS[persona]
    shutil.copy2(template, POLICY_FILE)


def read_policy() -> str:
    """Read and return the current policy text."""
    if not policy_exists():
        raise FileNotFoundError(
            "No policy found. Run 'ai-lint init' to create one."
        )
    return POLICY_FILE.read_text()


def open_policy_in_editor():
    """Open policy.md in the user's default editor."""
    if not policy_exists():
        raise FileNotFoundError(
            "No policy found. Run 'ai-lint init' to create one."
        )
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
    os.execvp(editor, [editor, str(POLICY_FILE)])
