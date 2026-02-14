"""Install a SessionEnd hook in ~/.claude/settings.json to auto-run ai-lint."""

import json
import sys
from pathlib import Path

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"

HOOK_COMMAND = "ai-lint check --last --quiet"

HOOK_ENTRY = {
    "matcher": "",
    "hooks": [
        {
            "type": "command",
            "command": HOOK_COMMAND,
        }
    ],
}


def read_settings() -> dict:
    if not CLAUDE_SETTINGS.exists():
        return {}
    return json.loads(CLAUDE_SETTINGS.read_text())


def write_settings(settings: dict):
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2) + "\n")


def is_hook_installed() -> bool:
    """Check if the ai-lint SessionEnd hook is already installed."""
    settings = read_settings()
    hooks = settings.get("hooks", {})
    session_end = hooks.get("SessionEnd", [])
    for entry in session_end:
        for hook in entry.get("hooks", []):
            if HOOK_COMMAND in hook.get("command", ""):
                return True
    return False


def install_hook():
    """Add the ai-lint SessionEnd hook to Claude settings."""
    if is_hook_installed():
        print("ai-lint hook is already installed.")
        return

    settings = read_settings()
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "SessionEnd" not in settings["hooks"]:
        settings["hooks"]["SessionEnd"] = []

    settings["hooks"]["SessionEnd"].append(HOOK_ENTRY)
    write_settings(settings)
    print("Installed SessionEnd hook in ~/.claude/settings.json")


def uninstall_hook():
    """Remove the ai-lint SessionEnd hook from Claude settings."""
    if not is_hook_installed():
        print("ai-lint hook is not installed.")
        return

    settings = read_settings()
    session_end = settings.get("hooks", {}).get("SessionEnd", [])
    settings["hooks"]["SessionEnd"] = [
        entry for entry in session_end
        if not any(HOOK_COMMAND in h.get("command", "") for h in entry.get("hooks", []))
    ]
    write_settings(settings)
    print("Removed ai-lint SessionEnd hook.")
