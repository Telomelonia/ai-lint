# ai-lint

**A linter for your AI coding sessions.**

<p align="center">
  <img width="400" height="400" alt="Gemini_Generated_Image_voazlcvoazlcvoaz (1) (1)" src="https://github.com/user-attachments/assets/a1ba87c8-10dc-4097-ab9e-2d7825b8d66f" />
</p>

ai-lint checks how you use AI — not the code it writes. Define your rules, and ai-lint reads your Claude Code sessions, evaluates them, and tells you what passed and what didn't.

No API keys. No dashboards. Runs locally.

---

## It catches this

<p align="center">
  <img width="1498" height="757" alt="Screenshot 2026-02-17 at 19 23 43" src="https://github.com/user-attachments/assets/d74e2ed5-a0fb-474b-8aa5-b0dbc97f8fd3" />
</p>

*ai-lint flagged a session where an API key was exposed in the conversation.*

---

## And gives you this

<p align="center">
  <img width="1512" height="604" alt="Screenshot 2026-02-17 at 19 24 33" src="https://github.com/user-attachments/assets/73fb95df-f936-458b-a9c1-a95657a0a498" />
</p>

*Every session gets a clear verdict — what passed, what failed, and why.*

---

## Why

You lint your code. You lint your commits. But nobody lints how they work with AI.

- Are you leaking credentials in prompts?
- Are you blindly accepting AI output without reviewing?
- Are you stuck in error → paste → fix loops?
- Are your team members following the AI usage guidelines you wrote?

ai-lint answers these questions automatically.

---

## Install

```bash
pip install ai-lint
```

Requires: Python 3.10+ and [Claude Code CLI](https://code.claude.com) installed.

---

## 30-Second Setup

```bash
ai-lint init
```

This asks you one question — pick a persona:

- **self** — 10 rules for individual developers
- **team** — 11 rules for teams with AI usage policies

Creates your policy at `~/.ai-lint/policy.md`.

_If you don't like the default policies... you can edit them anytime._

---

## Usage

**Check your last session:**

```bash
ai-lint check --last
```

**Output:**

```
[+] PASS  No credential exposure
[+] PASS  No sensitive data in prompts
[x] FAIL  Review before acceptance — Developer accepted output without review
[-] SKIP  Testing discussed or performed

8/10 passed
```

**Check interactively (pick a session):**

```bash
ai-lint check
```

**Batch report (last 5 sessions → markdown):**

```bash
ai-lint report -n 5
```

**Auto-check after every session:**

```bash
ai-lint hook install
```

**Edit your policy:**

```bash
ai-lint policy
```

---

## What It Checks

### Security

| Rule | What it catches |
|------|----------------|
| No credential exposure | API keys, private keys, connection strings in prompts |
| No sensitive data | Real customer PII, production DB contents, internal IPs |
| No destructive commands | `rm -rf`, `DROP TABLE`, `git push --force` to main without safeguards |

### Developer Engagement

| Rule | What it catches |
|------|----------------|
| Understanding before delegation | "fix login" with zero context |
| No fix-it loops | 3+ error-paste-fix cycles without root cause analysis |
| Review before acceptance | Accepting AI output without reading or questioning it |
| Clarifying questions | Never asking "why X over Y?" or "what are the tradeoffs?" |

### Process Discipline

| Rule | What it catches |
|------|----------------|
| Incremental changes | One massive "build everything" request with no checkpoints |
| Testing discussed | No mention of tests, edge cases, or verification |
| Clear objective | Undirected drift with no stated goal |
| Stays on scope | AI usage outside assigned work *(team only)* |

---

## Who It's For

**Individual developers** — Check your own AI habits. Get better at working with AI. Catch credential leaks before they become incidents.

**Engineering managers** — You wrote an AI usage policy. Now what? Give your team ai-lint. Each developer installs it, runs it locally, and self-checks against your policy. No surveillance dashboards, no monitoring infrastructure — just a shared `policy.md` that everyone checks against. Drop your AI usage guidelines into the policy file and your team has a compliance tool in 30 seconds.

**Anyone with a policy** — Edit `~/.ai-lint/policy.md` with any rules you want, in plain English. ai-lint evaluates against whatever you write.

---

## Custom Policies

The templates are starting points. Write your own rules:

```bash
ai-lint policy
```

```markdown
# My AI Policy

1. Never use AI for authentication or payment code without explicit approval
2. Always run the test suite before ending a session
3. Reference a JIRA ticket in every session
4. Don't generate client-facing emails without human review
5. Keep sessions under 30 minutes
```

ai-lint sends your rules + the session transcript to Claude and gets back verdicts. Plain English rules just work.

---

## How It Works

```
~/.claude/projects/*.jsonl    →    ai-lint    →    verdicts
   (session transcripts)        + policy.md      (PASS/FAIL/SKIP)
```

1. Reads Claude Code session transcripts (JSONL files stored locally)
2. Pairs them with your policy (`~/.ai-lint/policy.md`)
3. Sends both to `claude -p` (Claude Code CLI) — no API keys, runs locally
4. Returns structured verdicts with reasoning

---

## Commands

| Command | What it does |
|---------|-------------|
| `ai-lint init` | Setup wizard — pick persona, create policy |
| `ai-lint check` | Check a session against your policy |
| `ai-lint check --last` | Check most recent session |
| `ai-lint report -n 5` | Batch-check last 5 sessions → markdown report |
| `ai-lint policy` | Open your policy in your editor |
| `ai-lint hook install` | Auto-check after every Claude Code session |
| `ai-lint hook uninstall` | Remove the auto-check hook |

---

## Uninstall

```bash
ai-lint hook uninstall
rm -rf ~/.ai-lint
pip uninstall ai-lint
```

---

## Contributing

There's a wide range of ways to contribute — from small additions to major features:

- **New flags** — `--format json`, `--since` date filter, `--severity` threshold, custom `--policy` path
- **Report formats** — PDF export, HTML reports, SARIF for IDE integration, JUnit XML for CI/CD
- **New session sources** — Cursor, GitHub Copilot, OpenAI Codex, Gemini CLI, Windsurf, OpenCode, Entire CLI
- **LLM providers** — OpenAI, Gemini, Ollama (fully offline), any OpenAI-compatible endpoint
- **Policy templates** — industry-specific rules, new personas, community-contributed policies
- **Bug fixes, docs, better output formatting**

Every new session source just needs a parser that returns the same `Session` format — the checker doesn't care where the transcript came from.

## License

MIT
