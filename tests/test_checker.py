"""Tests for ai_lint.checker."""

import json

import pytest

from ai_lint.checker import (
    ClaudeNotFoundError,
    _call_claude,
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


class TestCallClaude:
    def test_missing_claude_raises(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: False)
        with pytest.raises(ClaudeNotFoundError):
            _call_claude("prompt")

    def test_subprocess_failure_raises(self, monkeypatch, make_fake_result):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        fake = make_fake_result(returncode=1, stderr="something went wrong")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake)
        with pytest.raises(RuntimeError, match="claude -p failed"):
            _call_claude("prompt")

    def test_json_wrapper_extraction(self, monkeypatch, make_fake_result):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        inner = {"key": "value"}
        wrapper = {"result": json.dumps(inner)}
        fake = make_fake_result(stdout=json.dumps(wrapper))
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake)
        assert _call_claude("prompt") == inner

    def test_direct_json(self, monkeypatch, make_fake_result):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        data = {"key": "value"}
        fake = make_fake_result(stdout=json.dumps(data))
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake)
        assert _call_claude("prompt") == data

    def test_fence_stripping(self, monkeypatch, make_fake_result):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        data = {"key": "value"}
        fenced = "```json\n" + json.dumps(data) + "\n```"
        fake = make_fake_result(stdout=fenced)
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake)
        assert _call_claude("prompt") == data

    def test_fence_stripping_after_wrapper_extraction(self, monkeypatch, make_fake_result):
        """Fence stripping works when wrapper result has leading whitespace."""
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        inner = {"key": "value"}
        fenced = "\n\n```json\n" + json.dumps(inner) + "\n```"
        wrapper = {"result": fenced}
        fake = make_fake_result(stdout=json.dumps(wrapper))
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake)
        assert _call_claude("prompt") == inner

    def test_fence_stripping_with_prose_before(self, monkeypatch, make_fake_result):
        """Fence extraction works when LLM adds commentary before the JSON block."""
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        inner = {"key": "value"}
        raw_text = "Let me analyze this.\n\n```json\n" + json.dumps(inner) + "\n```"
        wrapper = {"result": raw_text}
        fake = make_fake_result(stdout=json.dumps(wrapper))
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake)
        assert _call_claude("prompt") == inner

    def test_invalid_json_raises(self, monkeypatch, make_fake_result):
        monkeypatch.setattr("ai_lint.checker.check_claude_installed", lambda: True)
        fake = make_fake_result(stdout="not json at all")
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: fake)
        with pytest.raises(RuntimeError, match="Failed to parse"):
            _call_claude("prompt")


class TestRunCheck:
    def test_returns_call_claude_result(self, monkeypatch):
        expected = {"verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}], "summary": "good"}
        monkeypatch.setattr("ai_lint.checker._call_claude", lambda prompt: expected)
        assert run_check("transcript", "policy") == expected

    def test_prompt_includes_transcript_and_policy(self, monkeypatch):
        captured = {}
        def fake_call(prompt):
            captured["prompt"] = prompt
            return {"verdicts": [], "summary": ""}
        monkeypatch.setattr("ai_lint.checker._call_claude", fake_call)
        run_check("my transcript", "my policy")
        assert "my transcript" in captured["prompt"]
        assert "my policy" in captured["prompt"]

    def test_propagates_claude_not_found(self, monkeypatch):
        def raise_not_found(prompt):
            raise ClaudeNotFoundError("not found")
        monkeypatch.setattr("ai_lint.checker._call_claude", raise_not_found)
        with pytest.raises(ClaudeNotFoundError):
            run_check("transcript", "policy")


class TestExtractInsights:
    def test_returns_validated_result(self, monkeypatch, sample_insights):
        monkeypatch.setattr("ai_lint.checker._call_claude", lambda prompt: sample_insights)
        result = extract_insights("transcript", "policy")
        assert result["what_went_well"][0]["pattern"] == "Clear problem description"

    def test_prompt_includes_transcript_and_policy(self, monkeypatch):
        captured = {}
        def fake_call(prompt):
            captured["prompt"] = prompt
            return {"what_went_well": [], "what_to_improve": [], "notable": []}
        monkeypatch.setattr("ai_lint.checker._call_claude", fake_call)
        extract_insights("my transcript", "my policy")
        assert "my transcript" in captured["prompt"]
        assert "my policy" in captured["prompt"]

    def test_validates_malformed_response(self, monkeypatch):
        monkeypatch.setattr("ai_lint.checker._call_claude", lambda prompt: {"bad_key": 123})
        result = extract_insights("transcript", "policy")
        assert result == {"what_went_well": [], "what_to_improve": [], "notable": []}

    def test_propagates_claude_not_found(self, monkeypatch):
        def raise_not_found(prompt):
            raise ClaudeNotFoundError("not found")
        monkeypatch.setattr("ai_lint.checker._call_claude", raise_not_found)
        with pytest.raises(ClaudeNotFoundError):
            extract_insights("transcript", "policy")


class TestFormatVerdicts:
    def test_icons(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        assert "[+] PASS" in output
        assert "[x] FAIL" in output
        assert "[-] SKIP" in output

    def test_compact_tally(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        assert "3/5 passed" in output

    def test_no_category_headers(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        lines = output.split("\n")
        # Category names should not appear as standalone header lines
        header_lines = [l.strip() for l in lines if l.strip() in ("Security", "Developer Engagement", "Process Discipline")]
        assert header_lines == []

    def test_no_summary(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        assert "Summary:" not in output
        assert "Mostly compliant" not in output

    def test_pass_no_reasoning(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        assert "No secrets found" not in output
        assert "Developer showed understanding" not in output

    def test_fail_includes_reasoning(self, sample_verdicts):
        output = format_verdicts(sample_verdicts)
        assert "Developer did not review" in output
        assert "[x] FAIL: Review before acceptance — Developer did not review." in output

    def test_empty_verdicts(self):
        output = format_verdicts({"verdicts": [], "summary": ""})
        assert "0/0 passed" in output

    def test_missing_category_no_header(self):
        result = {
            "verdicts": [{"rule": "R1", "verdict": "PASS", "reasoning": "ok"}],
            "summary": "",
        }
        output = format_verdicts(result)
        assert "[+] PASS: R1" in output
        assert "1/1 passed" in output


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
