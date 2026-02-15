# Changelog

All notable changes to ai-lint will be documented in this file.

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
- Three built-in policy templates: self, team, parent
- Session discovery from `~/.claude/projects/` with subagent filtering
- JSONL transcript parsing with tool use/result extraction
- JSON verdict parsing with markdown fence stripping
- Homebrew formula for `brew install`
