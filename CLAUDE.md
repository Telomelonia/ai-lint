# CLAUDE.md — ai-lint

## What is this?
ai-lint checks AI coding session transcripts against user-defined policies. It reads Claude Code JSONL session files, sends them to `claude -p` for compliance analysis, and reports verdicts.

## Tech stack
- Python 3.10+
- Click for CLI
- No API keys — uses `claude -p` (Claude Code CLI) as the LLM backend
- setuptools for packaging

## Project structure
```
ai_lint/
  config.py       — ~/.ai-lint/ dir management, policy CRUD
  sessions.py     — discover + parse Claude Code JSONL transcripts
  checker.py      — send transcript+policy to claude -p, parse verdicts
  setup_hook.py   — install/uninstall SessionEnd hook in ~/.claude/settings.json
  cli.py          — Click CLI (init, check, report, policy, hook)
  templates/      — policy_self.md, policy_team.md, policy_parent.md
tests/            — pytest test suite
homebrew/         — Homebrew formula
```

## Architecture flow
`config` → `sessions` → `checker` → `cli`
- `config` manages the policy file in `~/.ai-lint/`
- `sessions` discovers and parses JSONL files from `~/.claude/projects/`
- `checker` formats transcript+policy, calls `claude -p`, parses JSON verdicts
- `cli` wires everything together with Click commands

## Running tests
```bash
pip install -e ".[test]"
pytest -v
```

## Code style
- Keep it simple — no over-engineering
- Real file I/O in tests (use `tmp_path`), mock only external calls (`subprocess.run`, `shutil.which`, `os.execvp`)
- Monkeypatch module-level constants (`CONFIG_DIR`, `CLAUDE_PROJECTS_DIR`, etc.) to temp dirs in tests
- Use Click's `CliRunner` for CLI tests

## Key conventions
- `PERSONAS` dict maps persona names to template filenames
- Session discovery skips `subagents/` directories
- `_extract_text()` handles both string and list-of-blocks content formats
- `run_check()` handles claude JSON wrapper extraction and markdown fence stripping
- All CLI commands use `sys.exit(1)` for errors, `sys.exit(0)` for graceful no-op
