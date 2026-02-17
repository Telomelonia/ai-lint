"""Install a SessionEnd hook in ~/.claude/settings.json to auto-run ai-lint."""

import json
import sys
from pathlib import Path

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"

HOOK_COMMAND = "ai-lint check --last --quiet"

# Claude Code suppresses hook stdout, so we write directly to /dev/tty.
HOOK_COMMAND_TTY = "ai-lint check --last --quiet --tty"

HOOK_ENTRY = {
    "matcher": "",
    "hooks": [
        {
            "type": "command",
            "command": HOOK_COMMAND_TTY,
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


def _is_ailint_hook(command: str) -> bool:
    """Check if a hook command belongs to ai-lint (old or new format)."""
    return "ai-lint check" in command


def is_hook_installed() -> bool:
    """Check if the ai-lint SessionEnd hook is already installed."""
    settings = read_settings()
    hooks = settings.get("hooks", {})
    session_end = hooks.get("SessionEnd", [])
    for entry in session_end:
        for hook in entry.get("hooks", []):
            if _is_ailint_hook(hook.get("command", "")):
                return True
    return False


def install_hook():
    """Add the ai-lint SessionEnd hook to Claude settings.

    If an older ai-lint hook exists, it is replaced with the current version.
    """
    settings = read_settings()
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "SessionEnd" not in settings["hooks"]:
        settings["hooks"]["SessionEnd"] = []

    # Remove any existing ai-lint hooks (old or current format) before installing
    old_count = len(settings["hooks"]["SessionEnd"])
    settings["hooks"]["SessionEnd"] = [
        entry for entry in settings["hooks"]["SessionEnd"]
        if not any(_is_ailint_hook(h.get("command", "")) for h in entry.get("hooks", []))
    ]
    replaced = old_count != len(settings["hooks"]["SessionEnd"])

    settings["hooks"]["SessionEnd"].append(HOOK_ENTRY)
    write_settings(settings)
    if replaced:
        print("Updated ai-lint SessionEnd hook in ~/.claude/settings.json")
    else:
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
        if not any(_is_ailint_hook(h.get("command", "")) for h in entry.get("hooks", []))
    ]
    write_settings(settings)
    print("Removed ai-lint SessionEnd hook.")
