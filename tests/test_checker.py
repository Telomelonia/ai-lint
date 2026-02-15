"""Tests for ai_lint.checker."""

import json

import pytest

from ai_lint.checker import (
    check_claude_installed,
    format_report_markdown,
    format_verdicts,
    run_check,
)


class TestCheckClaudeInstalled:
    def test_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: "/usr/local/bin/claude")
        assert check_claude_installed() is True

    def test_not_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda x: None)
        assert check_claude_installed() is False


class TestRunCheck:
    def test_missing_claude_exits(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: False)
        with pytest.raises(SystemExit):
            run_check("transcript", "policy")

    def test_subprocess_failure_raises(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)

        class FakeResult:
            returncode = 1
            stderr = "something went wrong"

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        with pytest.raises(RuntimeError, match="claude -p failed"):
            run_check("transcript", "policy")

    def test_json_wrapper_extraction(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        inner = {"verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}], "summary": "good"}
        wrapper = {"result": json.dumps(inner)}

        class FakeResult:
            returncode = 0
            stdout = json.dumps(wrapper)
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        result = run_check("transcript", "policy")
        assert result["verdicts"][0]["verdict"] == "PASS"

    def test_direct_json(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        data = {"verdicts": [{"rule": "R1", "verdict": "FAIL", "reasoning": "bad"}], "summary": "fail"}

        class FakeResult:
            returncode = 0
            stdout = json.dumps(data)
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        result = run_check("transcript", "policy")
        assert result["verdicts"][0]["verdict"] == "FAIL"

    def test_fence_stripping(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        data = {"verdicts": [], "summary": "ok"}
        fenced = "```json\n" + json.dumps(data) + "\n```"

        class FakeResult:
            returncode = 0
            stdout = fenced
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        result = run_check("transcript", "policy")
        assert result["summary"] == "ok"

    def test_fence_stripping_after_wrapper_extraction(self, monkeypatch):
        """Fence stripping works when wrapper result has leading whitespace."""
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        inner = {"verdicts": [], "summary": "ok"}
        fenced = "\n\n```json\n" + json.dumps(inner) + "\n```"
        wrapper = {"result": fenced}

        class FakeResult:
            returncode = 0
            stdout = json.dumps(wrapper)
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        result = run_check("transcript", "policy")
        assert result["summary"] == "ok"

    def test_fence_stripping_with_prose_before(self, monkeypatch):
        """Fence extraction works when LLM adds commentary before the JSON block."""
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        inner = {"verdicts": [], "summary": "ok"}
        raw_text = "Let me analyze this session.\n\n```json\n" + json.dumps(inner) + "\n```"
        wrapper = {"result": raw_text}

        class FakeResult:
            returncode = 0
            stdout = json.dumps(wrapper)
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        result = run_check("transcript", "policy")
        assert result["summary"] == "ok"

    def test_invalid_json_raises(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)

        class FakeResult:
            returncode = 0
            stdout = "not json at all"
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        with pytest.raises(RuntimeError, match="Failed to parse"):
            run_check("transcript", "policy")


class TestFormatVerdicts:
    def test_icons_and_counts(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        assert "[+] PASS" in output
        assert "[x] FAIL" in output
        assert "[-] SKIP" in output
        assert "3 passed" in output
        assert "1 failed" in output
        assert "1 skipped" in output

    def test_category_headers(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        assert "Security" in output
        assert "Developer Engagement" in output
        assert "Process Discipline" in output

    def test_includes_summary(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        assert "Mostly compliant" in output

    def test_includes_reasoning(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        assert "Developer showed understanding" in output
        assert "No secrets found" in output

    def test_empty_verdicts(self):
        output = format_verdicts({"verdicts": [], "summary": ""})
        assert "0 passed" in output

    def test_no_summary(self):
        output = format_verdicts({"verdicts": [], "summary": ""})
        assert "Summary:" not in output

    def test_missing_category_falls_back(self):
        result = {
            "verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}],
            "summary": "",
        }
        output = format_verdicts(result)
        assert "General" in output
        assert "[+] PASS" in output


class TestFormatReportMarkdown:
    def test_header(self, sample_verdicts):
        report = format_report_markdown([{"session_label": "Session A", "result": sample_verdicts}])
        assert "# ai-lint Compliance Report" in report

    def test_emojis(self, sample_verdicts):
        report = format_report_markdown([{"session_label": "Session A", "result": sample_verdicts}])
        assert "\u2705" in report  # checkmark
        assert "\u274c" in report  # X

    def test_category_sections_in_report(self, sample_verdicts):
        report = format_report_markdown([{"session_label": "Session A", "result": sample_verdicts}])
        assert "### Security" in report
        assert "### Developer Engagement" in report
        assert "### Process Discipline" in report

    def test_multi_session_totals(self, sample_verdicts):
        entries = [
            {"session_label": "A", "result": sample_verdicts},
            {"session_label": "B", "result": sample_verdicts},
        ]
        report = format_report_markdown(entries)
        assert "Sessions checked: 2" in report
        assert "6 passed" in report  # 3 per session
        assert "2 failed" in report

    def test_per_session_score(self, sample_verdicts):
        report = format_report_markdown([{"session_label": "S1", "result": sample_verdicts}])
        assert "3 passed, 1 failed, 1 skipped" in report

    def test_session_summary_quoted(self, sample_verdicts):
        report = format_report_markdown([{"session_label": "S1", "result": sample_verdicts}])
        assert "> Mostly compliant" in report

    def test_empty_sessions(self):
        report = format_report_markdown([])
        assert "Sessions checked: 0" in report
