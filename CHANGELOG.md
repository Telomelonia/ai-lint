# Changelog

All notable changes to ai-lint will be documented in this file.

## [0.1.0] - 2025-06-15

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
