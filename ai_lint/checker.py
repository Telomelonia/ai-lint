"""Send transcript + policy to claude -p and parse compliance verdicts."""

import json
import shutil
import subprocess
import sys


SYSTEM_PROMPT = """You are a compliance auditor. You will receive a session transcript from an AI coding session and a policy document with numbered rules.

For each rule in the policy, evaluate whether the session complies. Return ONLY valid JSON — no markdown fences, no commentary outside the JSON.

Response format:
{
  "verdicts": [
    {
      "rule": "Rule name",
      "verdict": "PASS" | "FAIL" | "SKIP",
      "reasoning": "One sentence explanation"
    }
  ],
  "summary": "One paragraph overall assessment"
}

Rules:
- PASS: The session clearly complies with this rule.
- FAIL: The session clearly violates this rule.
- SKIP: The rule is not applicable to this session (e.g., no code was written, so testing rules don't apply).

Be fair but firm. Base verdicts only on what's visible in the transcript."""


def check_claude_installed() -> bool:
    """Check if the claude CLI is available."""
    return shutil.which("claude") is not None


def run_check(transcript: str, policy: str) -> dict:
    """Send transcript + policy to claude -p and return parsed verdicts.

    Raises RuntimeError if claude CLI fails.
    Returns dict with 'verdicts' and 'summary' keys.
    """
    if not check_claude_installed():
        print(
            "Error: 'claude' CLI not found.\n"
            "Install Claude Code: https://claude.ai/install.sh",
            file=sys.stderr,
        )
        sys.exit(1)

    prompt = f"""{SYSTEM_PROMPT}

---
POLICY:
{policy}

---
TRANSCRIPT:
{transcript}"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("claude -p timed out after 120 seconds")

    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed:\n{result.stderr}")

    # claude --output-format json wraps the response in a JSON object
    # with a "result" field containing the text response
    raw = result.stdout.strip()
    try:
        wrapper = json.loads(raw)
        # If claude returned structured output, extract the text result
        if isinstance(wrapper, dict) and "result" in wrapper:
            raw = wrapper["result"]
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences if the LLM added them anyway
    if raw.startswith("```"):
        lines = raw.split("\n")
        if len(lines) >= 2 and lines[-1].startswith("```"):
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        raw = "\n".join(lines)

    try:
        verdicts = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"Failed to parse LLM response as JSON.\nRaw output:\n{raw}"
        )

    return verdicts


def format_verdicts(result: dict) -> str:
    """Format verdicts dict into a readable terminal string."""
    lines = []
    verdicts = result.get("verdicts", [])

    pass_count = sum(1 for v in verdicts if v["verdict"] == "PASS")
    fail_count = sum(1 for v in verdicts if v["verdict"] == "FAIL")
    skip_count = sum(1 for v in verdicts if v["verdict"] == "SKIP")

    for v in verdicts:
        icon = {"PASS": "+", "FAIL": "x", "SKIP": "-"}.get(v["verdict"], "?")
        lines.append(f"  [{icon}] {v['verdict']}: {v['rule']}")
        lines.append(f"      {v['reasoning']}")
        lines.append("")

    lines.append(f"Results: {pass_count} passed, {fail_count} failed, {skip_count} skipped")
    lines.append("")

    summary = result.get("summary", "")
    if summary:
        lines.append(f"Summary: {summary}")

    return "\n".join(lines)


def format_report_markdown(session_results: list[dict]) -> str:
    """Format multiple session results into a markdown report.

    Each entry in session_results should have:
      - session_label: str
      - result: dict (the verdicts dict from run_check)
    """
    lines = ["# ai-lint Compliance Report", ""]

    total_pass = 0
    total_fail = 0
    total_skip = 0

    for entry in session_results:
        label = entry["session_label"]
        result = entry["result"]
        verdicts = result.get("verdicts", [])

        lines.append(f"## {label}")
        lines.append("")

        for v in verdicts:
            icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(v["verdict"], "❓")
            lines.append(f"- {icon} **{v['verdict']}**: {v['rule']}")
            lines.append(f"  - {v['reasoning']}")

        p = sum(1 for v in verdicts if v["verdict"] == "PASS")
        f_ = sum(1 for v in verdicts if v["verdict"] == "FAIL")
        s = sum(1 for v in verdicts if v["verdict"] == "SKIP")
        total_pass += p
        total_fail += f_
        total_skip += s

        lines.append("")
        lines.append(f"**Score: {p} passed, {f_} failed, {s} skipped**")
        lines.append("")

        summary = result.get("summary", "")
        if summary:
            lines.append(f"> {summary}")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("## Overall")
    lines.append(f"- Sessions checked: {len(session_results)}")
    lines.append(f"- Total: {total_pass} passed, {total_fail} failed, {total_skip} skipped")
    lines.append("")

    return "\n".join(lines)
