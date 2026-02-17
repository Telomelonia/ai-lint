# Changelog

All notable changes to ai-lint will be documented in this file.

## [Unreleased]

### Fixed
- ai-lint's own `claude -p` sessions no longer pollute the session list — `--no-session-persistence` prevents session file creation, and a defensive filter skips any existing ai-lint sessions
- JSON parsing failure when LLM returns fenced JSON without trailing newline — fence regex now handles missing newlines, and a `{...}` extraction fallback catches remaining edge cases
- Hook no longer spams "Your report is getting ready..." repeatedly in the terminal — quiet mode now runs silently with no spinner or status messages until results are ready

### Changed
- SessionEnd hook now writes output directly to `/dev/tty` via `--tty` flag, bypassing Claude Code's stdout suppression — report is visible in the terminal after session ends
- `ai-lint hook install` now auto-upgrades older hook formats instead of skipping with "already installed"

## [0.3.0] - 2026-02-17

### Changed
- Compact `check` output: dropped category headers, suppressed reasoning for PASS/SKIP verdicts, show FAIL reasoning inline after dash, replaced verbose results line with `X/Y passed` tally, removed summary paragraph

### Fixed
- JSON parsing failure when `claude -p` wraps response in `{"result": "\n\n```json...```"}` — inner result now `.strip()`ed before fence extraction
- JSON parsing failure when LLM adds prose before the fenced JSON block — fence extraction now uses regex to find fenced JSON anywhere in the response
- Large transcripts failing silently — prompt now sent via stdin instead of CLI argument to avoid OS argument length limits

### Added
- Loading spinner animation while `claude -p` runs (braille dot frames on stderr)
- **Per-session insights** alongside compliance verdicts — a parallel `claude -p` call surfaces what went well, what to improve, and notable observations with transcript evidence
- `--no-insights` flag on `check` to skip insights for speed
- `--quiet` now implies `--no-insights` (no extra LLM call in hook mode)

## [0.2.0] - 2026-02-15 (`12e688d`)

### Changed
- Policy templates restructured into three sections: Security, Developer Engagement, Process Discipline
- Each verdict now includes a `category` field matching its section
- Terminal and markdown report output grouped by category
- System prompt updated with section-independent evaluation and guidance for pattern-based vs behavioral rules
- Renamed policy headers from "AI Usage Policy" to "AI Session Policy"

### Added
- **Security rules**: credential exposure (S1), sensitive data in prompts (S2), destructive commands without safeguards (S3)
- **Developer Engagement rules**: understanding before delegation (E1), no fix-it loops (E2), review before acceptance (E3), clarifying questions (E4)
- **Process Discipline rules**: incremental scoped changes (P1), testing discussed or performed (P2), clear session objective (P3)
- Team template adds P4 (stays within project scope) — 11 rules total
- Backwards-compatible `"General"` fallback when `category` field is missing from verdicts

## [0.1.0] - 2025-06-15 (`ecc3cec`)

### Added
- `ai-lint init` — setup wizard with persona selection (self, team, parent)
- `ai-lint check` — check a session transcript against your policy
  - `--last` flag to auto-select most recent session
  - `--quiet` flag for hook usage
  - Interactive session picker for manual selection
- `ai-lint report` — batch-check recent sessions and generate markdown report
  - `-n` flag to set number of sessions
  - `-o` flag to specify output file
- `ai-lint policy` — open policy file in your default editor
- `ai-lint hook install` / `ai-lint hook uninstall` — manage SessionEnd hook
- Two built-in policy templates: self, team
- Session discovery from `~/.claude/projects/` with subagent filtering
- JSONL transcript parsing with tool use/result extraction
- JSON verdict parsing with markdown fence stripping
- Homebrew formula for `brew install`
