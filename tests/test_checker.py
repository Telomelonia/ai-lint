"""Tests for ai_lint.checker."""

import json

import pytest

from ai_lint.checker import (
    _validate_insights,
    check_claude_installed,
    extract_insights,
    format_insights,
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


class TestExtractInsights:
    def test_valid_response(self, monkeypatch, sample_insights):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        inner = sample_insights

        class FakeResult:
            returncode = 0
            stdout = json.dumps(inner)
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        result = extract_insights("transcript", "policy")
        assert result["what_went_well"][0]["pattern"] == "Clear problem description"

    def test_wrapper_extraction(self, monkeypatch, sample_insights):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        wrapper = {"result": json.dumps(sample_insights)}

        class FakeResult:
            returncode = 0
            stdout = json.dumps(wrapper)
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        result = extract_insights("transcript", "policy")
        assert len(result["what_went_well"]) == 1

    def test_fence_stripping(self, monkeypatch, sample_insights):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        fenced = "```json\n" + json.dumps(sample_insights) + "\n```"

        class FakeResult:
            returncode = 0
            stdout = fenced
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        result = extract_insights("transcript", "policy")
        assert len(result["what_to_improve"]) == 1

    def test_invalid_json_raises(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)

        class FakeResult:
            returncode = 0
            stdout = "not json at all"
            stderr = ""

        monkeypatch.setattr("subprocess.run", lambda *a, **kw: FakeResult())
        with pytest.raises(RuntimeError, match="Failed to parse"):
            extract_insights("transcript", "policy")

    def test_missing_claude_exits(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: False)
        with pytest.raises(SystemExit):
            extract_insights("transcript", "policy")


class TestValidateInsights:
    def test_valid_data_passthrough(self, sample_insights):
        result = _validate_insights(sample_insights)
        assert result == sample_insights

    def test_missing_keys_filled(self):
        result = _validate_insights({})
        assert result == {"what_went_well": [], "what_to_improve": [], "notable": []}

    def test_malformed_items_filtered(self):
        raw = {
            "what_went_well": [
                {"pattern": "Good", "evidence": "Proof"},
                {"pattern": "Missing evidence"},  # no evidence key
                "not a dict",
            ],
            "what_to_improve": [],
            "notable": [
                {"observation": "Interesting", "evidence": "Proof"},
                {"wrong_key": "Bad"},
            ],
        }
        result = _validate_insights(raw)
        assert len(result["what_went_well"]) == 1
        assert result["what_went_well"][0]["pattern"] == "Good"
        assert len(result["notable"]) == 1

    def test_non_dict_returns_defaults(self):
        result = _validate_insights("not a dict")
        assert result == {"what_went_well": [], "what_to_improve": [], "notable": []}


class TestFormatInsights:
    def test_full_output(self, sample_insights):
        output = format_insights(sample_insights)
        assert "What went well:" in output
        assert "Clear problem description" in output
        assert "What to improve:" in output
        assert "No testing discussed" in output

    def test_empty_insights(self):
        output = format_insights({"what_went_well": [], "what_to_improve": [], "notable": []})
        assert "What went well:" not in output
        assert "What to improve:" not in output

    def test_header_present(self, sample_insights):
        output = format_insights(sample_insights)
        assert "--- Session Insights ---" in output

    def test_notable_section(self):
        insights = {
            "what_went_well": [],
            "what_to_improve": [],
            "notable": [{"observation": "Used unusual pattern", "evidence": "Line 42"}],
        }
        output = format_insights(insights)
        assert "Notable:" in output
        assert "Used unusual pattern" in output
