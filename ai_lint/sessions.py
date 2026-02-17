"""Find and parse Claude Code session JSONL transcripts."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Prompt prefixes used by ai-lint's own claude -p calls (checker.py).
# Sessions starting with these are ai-lint internal sessions, not user work.
_AI_LINT_PROMPT_PREFIXES = (
    "You are a compliance auditor for AI coding sessions.",
    "You are a development coach reviewing an AI coding session transcript.",
)


@dataclass
class Message:
    role: str  # "user" or "assistant"
    text: str
    timestamp: str


@dataclass
class Session:
    session_id: str
    path: Path
    project: str  # derived from directory name
    cwd: str = ""
    timestamp: str = ""
    messages: list[Message] = field(default_factory=list)

    @property
    def label(self) -> str:
        """Human-readable label for session picker."""
        time_str = ""
        if self.timestamp:
            try:
                dt = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, AttributeError):
                time_str = self.timestamp[:16]
        project = self.project.replace("-", "/").lstrip("/")
        first_msg = ""
        if self.messages:
            first_msg = self.messages[0].text[:60].replace("\n", " ")
            if len(self.messages[0].text) > 60:
                first_msg += "..."
        parts = []
        if time_str:
            parts.append(time_str)
        if project:
            parts.append(project)
        if first_msg:
            parts.append(f'"{first_msg}"')
        return " | ".join(parts) if parts else self.session_id[:8]


def _is_ai_lint_session(path: Path) -> bool:
    """Check if a JSONL session file is an ai-lint internal session.

    Reads the first user message and checks if it starts with a known
    ai-lint prompt prefix (compliance check or insights extraction).
    """
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "user":
                    continue
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    # Extract text from list-of-blocks format
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            content = block["text"]
                            break
                    else:
                        return False
                if isinstance(content, str):
                    return any(content.startswith(prefix) for prefix in _AI_LINT_PROMPT_PREFIXES)
                return False
    except (OSError, ValueError):
        return False
    return False


def discover_sessions() -> list[Session]:
    """Find all session JSONL files under ~/.claude/projects/."""
    if not CLAUDE_PROJECTS_DIR.exists():
        return []

    sessions = []
    for jsonl_path in sorted(CLAUDE_PROJECTS_DIR.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        # Skip subagent transcripts
        if "subagents" in jsonl_path.parts:
            continue
        # Skip ai-lint's own claude -p sessions
        if _is_ai_lint_session(jsonl_path):
            continue
        # Project name from parent directory
        project_dir = jsonl_path.parent.name
        session_id = jsonl_path.stem
        sessions.append(Session(
            session_id=session_id,
            path=jsonl_path,
            project=project_dir,
        ))
    return sessions


def _extract_text(content) -> str:
    """Extract readable text from message content (string or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    tool = block.get("name", "unknown")
                    inp = block.get("input", {})
                    # Summarize tool use concisely
                    if tool == "Bash":
                        parts.append(f"[Tool: Bash] {inp.get('command', '')}")
                    elif tool in ("Read", "Write", "Edit"):
                        parts.append(f"[Tool: {tool}] {inp.get('file_path', '')}")
                    elif tool == "Grep":
                        parts.append(f"[Tool: Grep] pattern={inp.get('pattern', '')}")
                    elif tool == "Glob":
                        parts.append(f"[Tool: Glob] {inp.get('pattern', '')}")
                    else:
                        parts.append(f"[Tool: {tool}]")
                elif block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str) and result_content:
                        # Truncate long tool results
                        if len(result_content) > 500:
                            result_content = result_content[:500] + "... (truncated)"
                        parts.append(f"[Tool Result] {result_content}")
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def parse_session(session: Session, max_messages: int = 200) -> Session:
    """Parse a session JSONL file and populate its messages."""
    messages = []
    first_timestamp = None
    cwd = ""

    with open(session.path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")

            # Extract cwd from first relevant entry
            if not cwd and entry.get("cwd"):
                cwd = entry["cwd"]

            # Only process user and assistant message types
            if entry_type not in ("user", "assistant"):
                continue

            msg = entry.get("message", {})
            role = msg.get("role")
            content = msg.get("content")
            timestamp = entry.get("timestamp", "")

            if not role or not content:
                continue

            text = _extract_text(content)
            if not text or not text.strip():
                continue

            # Skip pure tool result messages (they're echoes)
            if isinstance(content, list) and all(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in content
            ):
                continue

            if first_timestamp is None:
                first_timestamp = timestamp

            messages.append(Message(role=role, text=text, timestamp=timestamp))

            if len(messages) >= max_messages:
                break

    session.messages = messages
    session.cwd = cwd
    session.timestamp = first_timestamp or ""
    return session


def format_transcript(session: Session) -> str:
    """Format a parsed session into a readable transcript string."""
    lines = []
    lines.append(f"# Session: {session.session_id}")
    lines.append(f"Project: {session.project}")
    if session.cwd:
        lines.append(f"Working directory: {session.cwd}")
    if session.timestamp:
        lines.append(f"Started: {session.timestamp}")
    lines.append(f"Messages: {len(session.messages)}")
    lines.append("")

    for msg in session.messages:
        role_label = "USER" if msg.role == "user" else "ASSISTANT"
        lines.append(f"--- {role_label} ---")
        lines.append(msg.text)
        lines.append("")

    return "\n".join(lines)
