---
name: test
description: Install project dependencies and run the pytest test suite. Use when tests need to be run after code changes.
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash
---

Run the ai-lint test suite.

Use `python3` (not `python`) and `python3 -m pip` (not `pip`) — this machine only has `python3` on PATH.

Steps:
1. Install: `python3 -m pip install -e "/Users/aryanshukla/ai-lint[test]"`
2. Run: `python3 -m pytest -v`
3. Report results — show pass/fail counts and any failures
