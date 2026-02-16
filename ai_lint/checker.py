"""Send transcript + policy to claude -p and parse compliance verdicts."""

import json
import re
import shutil
import subprocess
import sys


SYSTEM_PROMPT = """You are a compliance auditor for AI coding sessions. You will receive a session transcript and a policy document organized into sections (e.g., Security, Developer Engagement, Process Discipline).

Evaluate each section INDEPENDENTLY. A violation in one section must not influence your judgment in another. For each rule, base your verdict only on what is visible in the transcript.

Evaluation guidance:
- For pattern-based rules (credential exposure, destructive commands): scan for specific indicators in user messages, assistant messages, and tool_use blocks (Bash, Write, Edit, Read).
- For behavioral rules (engagement, review discipline): assess the overall conversational pattern across the session — who drives the work, how the developer responds to AI output, and whether the developer demonstrates understanding.
- For process rules (scope, testing): look at the session arc — does it have structure, does it stay focused, are there checkpoints?

Return ONLY valid JSON — no markdown fences, no commentary outside the JSON.

Response format:
{
  "verdicts": [
    {
      "category": "Section name",
      "rule": "Rule name",
      "verdict": "PASS" | "FAIL" | "SKIP",
      "reasoning": "One sentence explanation"
    }
  ],
  "summary": "One paragraph overall assessment"
}

Verdict meanings:
- PASS: The session clearly complies with this rule.
- FAIL: The session clearly violates this rule.
- SKIP: The rule is not applicable to this session (e.g., no code was written, so testing rules don't apply).

You MUST evaluate every rule in the policy. Be fair but firm."""


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
            ["claude", "-p", "--output-format", "json"],
            input=prompt,
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
            raw = wrapper["result"].strip()
    except json.JSONDecodeError:
        pass

    # Extract JSON from markdown code fences anywhere in the response
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1)

    try:
        verdicts = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"Failed to parse LLM response as JSON.\nRaw output:\n{raw}"
        )

    return verdicts


INSIGHT_SYSTEM_PROMPT = """You are a development coach reviewing an AI coding session transcript. Your goal is to provide actionable, evidence-based feedback on how the session went.

Focus on:
- Interaction patterns: How did the developer and AI collaborate?
- Decision quality: Were good choices made about scope, approach, and delegation?
- Efficiency: Was time spent well? Were there unnecessary detours?
- Process: Was there testing, review, or structured thinking?

Every insight MUST cite specific evidence from the transcript.

Return ONLY valid JSON — no markdown fences, no commentary outside the JSON.

Response format:
{
  "what_went_well": [
    {"pattern": "Short description of positive pattern", "evidence": "Specific quote or reference from transcript"}
  ],
  "what_to_improve": [
    {"pattern": "Short description of improvement area", "evidence": "Specific quote or reference from transcript"}
  ],
  "notable": [
    {"observation": "Interesting observation", "evidence": "Specific quote or reference from transcript"}
  ]
}

Guidelines:
- Provide 1-3 items per section. Empty sections are fine if nothing applies.
- Be specific and constructive, not generic.
- Base everything on what actually happened in the transcript."""


def extract_insights(transcript: str, policy: str) -> dict:
    """Send transcript + policy to claude -p and return parsed insights.

    Raises RuntimeError if claude CLI fails or response is unparseable.
    Returns dict with 'what_went_well', 'what_to_improve', 'notable' keys.
    """
    if not check_claude_installed():
        print(
            "Error: 'claude' CLI not found.\n"
            "Install Claude Code: https://claude.ai/install.sh",
            file=sys.stderr,
        )
        sys.exit(1)

    prompt = f"""{INSIGHT_SYSTEM_PROMPT}

---
POLICY (for context on what the team values):
{policy}

---
TRANSCRIPT:
{transcript}"""

    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("claude -p timed out after 120 seconds")

    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed:\n{result.stderr}")

    raw = result.stdout.strip()
    try:
        wrapper = json.loads(raw)
        if isinstance(wrapper, dict) and "result" in wrapper:
            raw = wrapper["result"].strip()
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1)

    try:
        insights = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"Failed to parse insights response as JSON.\nRaw output:\n{raw}"
        )

    return _validate_insights(insights)


def _validate_insights(raw: dict) -> dict:
    """Validate and normalize insights structure, filling defaults for missing fields."""
    result = {
        "what_went_well": [],
        "what_to_improve": [],
        "notable": [],
    }

    if not isinstance(raw, dict):
        return result

    for item in raw.get("what_went_well", []):
        if isinstance(item, dict) and "pattern" in item and "evidence" in item:
            result["what_went_well"].append(item)

    for item in raw.get("what_to_improve", []):
        if isinstance(item, dict) and "pattern" in item and "evidence" in item:
            result["what_to_improve"].append(item)

    for item in raw.get("notable", []):
        if isinstance(item, dict) and "observation" in item and "evidence" in item:
            result["notable"].append(item)

    return result


def format_insights(insights: dict) -> str:
    """Format insights dict into a readable terminal string."""
    lines = ["\n--- Session Insights ---\n"]

    well = insights.get("what_went_well", [])
    if well:
        lines.append("What went well:")
        for item in well:
            lines.append(f"  - {item['pattern']}")
            lines.append(f"    Evidence: {item['evidence']}")
        lines.append("")

    improve = insights.get("what_to_improve", [])
    if improve:
        lines.append("What to improve:")
        for item in improve:
            lines.append(f"  - {item['pattern']}")
            lines.append(f"    Evidence: {item['evidence']}")
        lines.append("")

    notable = insights.get("notable", [])
    if notable:
        lines.append("Notable:")
        for item in notable:
            lines.append(f"  - {item['observation']}")
            lines.append(f"    Evidence: {item['evidence']}")
        lines.append("")

    return "\n".join(lines)


def _group_by_category(verdicts: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group verdicts by category, preserving order of first appearance."""
    groups: dict[str, list[dict]] = {}
    for v in verdicts:
        cat = v.get("category", "General")
        groups.setdefault(cat, []).append(v)
    return list(groups.items())


def format_verdicts(result: dict) -> str:
    """Format verdicts dict into a readable terminal string."""
    lines = []
    verdicts = result.get("verdicts", [])

    pass_count = sum(1 for v in verdicts if v["verdict"] == "PASS")
    fail_count = sum(1 for v in verdicts if v["verdict"] == "FAIL")
    skip_count = sum(1 for v in verdicts if v["verdict"] == "SKIP")

    for category, group in _group_by_category(verdicts):
        lines.append(f"  {category}")
        for v in group:
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

        for category, group in _group_by_category(verdicts):
            lines.append(f"### {category}")
            lines.append("")
            for v in group:
                icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(v["verdict"], "❓")
                lines.append(f"- {icon} **{v['verdict']}**: {v['rule']}")
                lines.append(f"  - {v['reasoning']}")
            lines.append("")

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
