"""Tests for ai_lint.sessions."""

import json
import time
from pathlib import Path

import pytest

from ai_lint.sessions import (
    Message,
    Session,
    _extract_text,
    _is_ai_lint_session,
    discover_sessions,
    format_transcript,
    parse_session,
)


# -- _extract_text --


class TestExtractText:
    def test_string_input(self):
        assert _extract_text("hello") == "hello"

    def test_text_block(self):
        blocks = [{"type": "text", "text": "Hello world"}]
        assert _extract_text(blocks) == "Hello world"

    def test_multiple_text_blocks(self):
        blocks = [
            {"type": "text", "text": "Line 1"},
            {"type": "text", "text": "Line 2"},
        ]
        assert _extract_text(blocks) == "Line 1\nLine 2"

    def test_tool_use_bash(self):
        blocks = [{"type": "tool_use", "name": "Bash", "input": {"command": "ls -la"}}]
        result = _extract_text(blocks)
        assert "[Tool: Bash]" in result
        assert "ls -la" in result

    def test_tool_use_read(self):
        blocks = [{"type": "tool_use", "name": "Read", "input": {"file_path": "/foo/bar.py"}}]
        result = _extract_text(blocks)
        assert "[Tool: Read]" in result
        assert "/foo/bar.py" in result

    def test_tool_use_write(self):
        blocks = [{"type": "tool_use", "name": "Write", "input": {"file_path": "/a/b.py"}}]
        result = _extract_text(blocks)
        assert "[Tool: Write]" in result

    def test_tool_use_edit(self):
        blocks = [{"type": "tool_use", "name": "Edit", "input": {"file_path": "/x.py"}}]
        result = _extract_text(blocks)
        assert "[Tool: Edit]" in result

    def test_tool_use_grep(self):
        blocks = [{"type": "tool_use", "name": "Grep", "input": {"pattern": "foo.*bar"}}]
        result = _extract_text(blocks)
        assert "[Tool: Grep]" in result
        assert "foo.*bar" in result

    def test_tool_use_glob(self):
        blocks = [{"type": "tool_use", "name": "Glob", "input": {"pattern": "**/*.py"}}]
        result = _extract_text(blocks)
        assert "[Tool: Glob]" in result
        assert "**/*.py" in result

    def test_tool_use_unknown(self):
        blocks = [{"type": "tool_use", "name": "CustomTool", "input": {}}]
        result = _extract_text(blocks)
        assert "[Tool: CustomTool]" in result

    def test_tool_result_string(self):
        blocks = [{"type": "tool_result", "content": "output here"}]
        result = _extract_text(blocks)
        assert "[Tool Result]" in result
        assert "output here" in result

    def test_tool_result_truncation(self):
        long_content = "x" * 600
        blocks = [{"type": "tool_result", "content": long_content}]
        result = _extract_text(blocks)
        assert "(truncated)" in result
        assert len(result) < 600

    def test_tool_result_empty(self):
        blocks = [{"type": "tool_result", "content": ""}]
        result = _extract_text(blocks)
        assert "[Tool Result]" not in result

    def test_string_in_list(self):
        blocks = ["just a string"]
        assert _extract_text(blocks) == "just a string"

    def test_mixed_content(self):
        blocks = [
            {"type": "text", "text": "Starting"},
            {"type": "tool_use", "name": "Bash", "input": {"command": "echo hi"}},
            {"type": "tool_result", "content": "hi"},
        ]
        result = _extract_text(blocks)
        assert "Starting" in result
        assert "[Tool: Bash]" in result
        assert "[Tool Result]" in result

    def test_non_list_non_string(self):
        assert _extract_text(42) == "42"


# -- discover_sessions --


class TestDiscoverSessions:
    def test_empty_dir(self, claude_projects_dir):
        assert discover_sessions() == []

    def test_finds_sessions(self, sample_jsonl_session, claude_projects_dir):
        sessions = discover_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == "abc12345-1111-2222-3333-444444444444"

    def test_skips_subagents(self, claude_projects_dir):
        sub = claude_projects_dir / "project" / "subagents"
        sub.mkdir(parents=True)
        (sub / "session.jsonl").write_text("{}\n")
        # Also add a regular session
        proj = claude_projects_dir / "project"
        (proj / "main.jsonl").write_text("{}\n")
        sessions = discover_sessions()
        ids = [s.session_id for s in sessions]
        assert "session" not in ids
        assert "main" in ids

    def test_sorted_by_mtime(self, claude_projects_dir):
        proj = claude_projects_dir / "project"
        proj.mkdir()
        (proj / "old.jsonl").write_text("{}\n")
        time.sleep(0.05)
        (proj / "new.jsonl").write_text("{}\n")
        sessions = discover_sessions()
        assert sessions[0].session_id == "new"
        assert sessions[1].session_id == "old"

    def test_project_name_from_parent(self, sample_jsonl_session, claude_projects_dir):
        sessions = discover_sessions()
        assert sessions[0].project == "-Users-dev-myproject"

    def test_nonexistent_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ai_lint.sessions.CLAUDE_PROJECTS_DIR", tmp_path / "nope")
        assert discover_sessions() == []

    def test_multiple_projects(self, claude_projects_dir):
        for name in ["proj-a", "proj-b"]:
            d = claude_projects_dir / name
            d.mkdir()
            (d / "s.jsonl").write_text("{}\n")
        sessions = discover_sessions()
        assert len(sessions) == 2


# -- _is_ai_lint_session / filtering --


class TestIsAiLintSession:
    def _write_session(self, directory, filename, content):
        """Helper to write a JSONL session with a single user message."""
        entry = {
            "type": "user",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {"role": "user", "content": content},
        }
        path = directory / filename
        path.write_text(json.dumps(entry) + "\n")
        return path

    def test_checker_prompt_detected(self, tmp_path):
        path = self._write_session(
            tmp_path, "s.jsonl",
            "You are a compliance auditor for AI coding sessions. Evaluate...",
        )
        assert _is_ai_lint_session(path) is True

    def test_insight_prompt_detected(self, tmp_path):
        path = self._write_session(
            tmp_path, "s.jsonl",
            "You are a development coach reviewing an AI coding session transcript. Focus on...",
        )
        assert _is_ai_lint_session(path) is True

    def test_normal_session_not_filtered(self, tmp_path):
        path = self._write_session(
            tmp_path, "s.jsonl",
            "Help me refactor the auth module",
        )
        assert _is_ai_lint_session(path) is False

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        assert _is_ai_lint_session(path) is False

    def test_no_user_message(self, tmp_path):
        entry = {
            "type": "system",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {"role": "system", "content": "Session started"},
        }
        path = tmp_path / "s.jsonl"
        path.write_text(json.dumps(entry) + "\n")
        assert _is_ai_lint_session(path) is False

    def test_list_content_format(self, tmp_path):
        entry = {
            "type": "user",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {
                "role": "user",
                "content": [
                    {"type": "text", "text": "You are a compliance auditor for AI coding sessions. Evaluate..."},
                ],
            },
        }
        path = tmp_path / "s.jsonl"
        path.write_text(json.dumps(entry) + "\n")
        assert _is_ai_lint_session(path) is True

    def test_nonexistent_file(self, tmp_path):
        path = tmp_path / "does_not_exist.jsonl"
        assert _is_ai_lint_session(path) is False


class TestDiscoverSessionsFiltersAiLint:
    def test_checker_sessions_filtered(self, claude_projects_dir):
        proj = claude_projects_dir / "project"
        proj.mkdir()
        # ai-lint checker session
        checker_entry = {
            "type": "user",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {
                "role": "user",
                "content": "You are a compliance auditor for AI coding sessions. Evaluate...",
            },
        }
        (proj / "checker.jsonl").write_text(json.dumps(checker_entry) + "\n")
        # Normal session
        normal_entry = {
            "type": "user",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {"role": "user", "content": "Help me fix a bug"},
        }
        (proj / "normal.jsonl").write_text(json.dumps(normal_entry) + "\n")
        sessions = discover_sessions()
        ids = [s.session_id for s in sessions]
        assert "checker" not in ids
        assert "normal" in ids

    def test_insight_sessions_filtered(self, claude_projects_dir):
        proj = claude_projects_dir / "project"
        proj.mkdir()
        insight_entry = {
            "type": "user",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {
                "role": "user",
                "content": "You are a development coach reviewing an AI coding session transcript. Focus on...",
            },
        }
        (proj / "insight.jsonl").write_text(json.dumps(insight_entry) + "\n")
        sessions = discover_sessions()
        assert len(sessions) == 0

    def test_normal_sessions_not_filtered(self, claude_projects_dir):
        proj = claude_projects_dir / "project"
        proj.mkdir()
        normal_entry = {
            "type": "user",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {"role": "user", "content": "Help me refactor the auth module"},
        }
        (proj / "normal.jsonl").write_text(json.dumps(normal_entry) + "\n")
        sessions = discover_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == "normal"


# -- parse_session --


class TestParseSession:
    def test_basic_parse(self, sample_jsonl_session, claude_projects_dir):
        sessions = discover_sessions()
        s = parse_session(sessions[0])
        assert len(s.messages) >= 3
        assert s.cwd == "/Users/dev/myproject"
        assert s.timestamp == "2025-06-15T10:30:00Z"

    def test_skips_system_messages(self, sample_jsonl_session, claude_projects_dir):
        sessions = discover_sessions()
        s = parse_session(sessions[0])
        for msg in s.messages:
            assert msg.role in ("user", "assistant")

    def test_max_messages(self, sample_jsonl_session, claude_projects_dir):
        sessions = discover_sessions()
        s = parse_session(sessions[0], max_messages=2)
        assert len(s.messages) == 2

    def test_bad_json_lines_skipped(self, claude_projects_dir):
        proj = claude_projects_dir / "proj"
        proj.mkdir()
        f = proj / "bad.jsonl"
        f.write_text("not json\n{bad\n")
        sessions = discover_sessions()
        s = parse_session(sessions[0])
        assert len(s.messages) == 0

    def test_empty_lines_skipped(self, claude_projects_dir):
        proj = claude_projects_dir / "proj"
        proj.mkdir()
        f = proj / "empty.jsonl"
        f.write_text("\n\n\n")
        sessions = discover_sessions()
        s = parse_session(sessions[0])
        assert len(s.messages) == 0

    def test_pure_tool_result_skipped(self, claude_projects_dir):
        proj = claude_projects_dir / "proj"
        proj.mkdir()
        entry = {
            "type": "assistant",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_result", "content": "some output"},
                ],
            },
        }
        f = proj / "tr.jsonl"
        f.write_text(json.dumps(entry) + "\n")
        sessions = discover_sessions()
        s = parse_session(sessions[0])
        assert len(s.messages) == 0

    def test_no_content_skipped(self, claude_projects_dir):
        proj = claude_projects_dir / "proj"
        proj.mkdir()
        entry = {
            "type": "user",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {"role": "user"},
        }
        f = proj / "nc.jsonl"
        f.write_text(json.dumps(entry) + "\n")
        sessions = discover_sessions()
        s = parse_session(sessions[0])
        assert len(s.messages) == 0

    def test_empty_text_skipped(self, claude_projects_dir):
        proj = claude_projects_dir / "proj"
        proj.mkdir()
        entry = {
            "type": "user",
            "timestamp": "2025-01-01T00:00:00Z",
            "message": {"role": "user", "content": "   "},
        }
        f = proj / "ws.jsonl"
        f.write_text(json.dumps(entry) + "\n")
        sessions = discover_sessions()
        s = parse_session(sessions[0])
        assert len(s.messages) == 0

    def test_first_timestamp_captured(self, sample_jsonl_session, claude_projects_dir):
        sessions = discover_sessions()
        s = parse_session(sessions[0])
        assert s.timestamp.startswith("2025-06-15")

    def test_message_roles(self, sample_jsonl_session, claude_projects_dir):
        sessions = discover_sessions()
        s = parse_session(sessions[0])
        roles = [m.role for m in s.messages]
        assert "user" in roles
        assert "assistant" in roles


# -- Session.label --


class TestSessionLabel:
    def test_label_with_all_parts(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="-Users-dev-project",
            timestamp="2025-06-15T10:30:00Z",
            messages=[Message(role="user", text="Help me refactor auth", timestamp="")],
        )
        label = s.label
        assert "2025-06-15" in label
        assert "Users/dev/project" in label
        assert "Help me refactor auth" in label

    def test_label_no_messages(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="-Users-dev-project",
            timestamp="2025-06-15T10:30:00Z",
        )
        label = s.label
        assert "Users/dev/project" in label
        assert '"' not in label

    def test_label_no_timestamp(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="-Users-dev-project",
            messages=[Message(role="user", text="Hello", timestamp="")],
        )
        label = s.label
        assert "Hello" in label

    def test_label_truncates_long_message(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="proj",
            messages=[Message(role="user", text="x" * 100, timestamp="")],
        )
        label = s.label
        assert "..." in label

    def test_label_fallback_to_id(self):
        s = Session(
            session_id="abc12345-long-id",
            path=Path("/tmp/s.jsonl"),
            project="",
        )
        label = s.label
        assert label == "abc12345"

    def test_label_bad_timestamp(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="proj",
            timestamp="not-a-date",
        )
        label = s.label
        assert "not-a-date" in label

    def test_label_newlines_removed(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="proj",
            messages=[Message(role="user", text="line1\nline2\nline3", timestamp="")],
        )
        assert "\n" not in s.label


# -- format_transcript --


class TestFormatTranscript:
    def test_includes_header(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="myproject",
            cwd="/home/user/proj",
            timestamp="2025-06-15T10:30:00Z",
            messages=[],
        )
        text = format_transcript(s)
        assert "# Session: abc12345" in text
        assert "myproject" in text
        assert "/home/user/proj" in text
        assert "Messages: 0" in text

    def test_includes_messages(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="proj",
            messages=[
                Message(role="user", text="Hello", timestamp=""),
                Message(role="assistant", text="Hi there", timestamp=""),
            ],
        )
        text = format_transcript(s)
        assert "--- USER ---" in text
        assert "Hello" in text
        assert "--- ASSISTANT ---" in text
        assert "Hi there" in text

    def test_no_cwd(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="proj",
        )
        text = format_transcript(s)
        assert "Working directory" not in text

    def test_no_timestamp(self):
        s = Session(
            session_id="abc12345",
            path=Path("/tmp/s.jsonl"),
            project="proj",
        )
        text = format_transcript(s)
        assert "Started:" not in text
