# AI Session Policy — Team / Corporate

Check each session against these rules. For each rule, return a verdict of PASS, FAIL, or SKIP (if the rule doesn't apply to this session). Include the section name as the "category" in each verdict.

---

## Security

### S1. No credential exposure
No API keys, passwords, tokens, database connection strings, or secrets should appear anywhere in the transcript — in user messages, pasted code, or AI output. Look for patterns like `sk-`, `AKIA`, `ghp_`, `xoxb-`, `-----BEGIN RSA PRIVATE KEY-----`, connection strings with `://user:password@`, or `.env` file contents with real key-value pairs. Any secret exposure is an automatic FAIL.

### S2. No sensitive data in prompts
Real customer PII (names, email addresses, phone numbers, physical addresses, account numbers), production database contents, internal financial data, proprietary business logic described in detail, or internal network details (IPs like `10.x.x.x`, `192.168.x.x`, hostnames like `*.internal`, `*.corp`) should not be pasted into the session. Note: discussing code that *handles* sensitive data is fine — pasting actual values is not. Using obvious test data like `test@example.com` is fine.

### S3. No destructive commands without safeguards
In Bash tool calls, look for destructive operations: `rm -rf` on non-trivial paths, `DROP TABLE`/`DROP DATABASE`, `git push --force` to main/production branches, `git reset --hard`, `chmod 777`, `kubectl delete`, or commands targeting production infrastructure. The key question: did the developer discuss the implications before the command ran, or did it execute without deliberation? Routine cleanup like `rm -rf node_modules` is fine. Deleting source code, force-pushing to shared branches, or modifying production systems without discussion is a FAIL.

---

## Developer Engagement

### E1. Understanding before delegation
The developer should demonstrate they understand the problem before asking the AI to solve it. Look for: describing the problem in their own words, articulating expected behavior, providing context about why a change is needed, or referencing a specific error they investigated. Contrast with pure delegation: "fix the login," "make it work," "build me X" with no context and no evidence the developer thought about the approach. A senior developer giving a precise, scoped instruction ("Refactor auth middleware to use JWT instead of session cookies") counts as understanding — vague commands without context do not.

### E2. No fix-it loops
A "fix-it loop" is: AI produces code, it fails, the developer pastes the error and says "that didn't work" / "still broken" / "try again," and this repeats 3+ times without the developer ever attempting to diagnose the root cause. Key signals: repeated error-paste-fix cycles, no diagnostic questions from the developer, no evidence they read the error message themselves, increasingly frustrated re-prompts. A single retry is normal. Three or more retries without any diagnosis attempt is a FAIL.

### E3. Review before acceptance
After the AI generates substantial code (via Write or Edit tool calls), does the developer show evidence of reviewing it? Positive signals: asking questions about the implementation ("why X instead of Y?"), requesting specific changes, pointing out issues, running the code and discussing results, or reading files after they were written. Negative signals: AI writes multiple files and the developer immediately says "great," "looks good," "next," or "commit it" without engaging with the content. Code should not be merge-ready without evidence of human review.

### E4. Developer asks clarifying or conceptual questions
At some point during the session, does the developer ask the AI to *explain* rather than just *do*? Look for: "Why did you choose X over Y?", "How does this handle Z?", "What are the tradeoffs?", "Can you explain how this works?", "What happens if...?" This indicates the developer is building understanding, not just collecting output. SKIP for very short sessions (under 5 messages) or purely administrative sessions (file moves, formatting).

---

## Process Discipline

### P1. Incremental, scoped changes
Is the work broken into reasonable steps, or does the developer ask the AI to build an entire complex system in one shot? A single first message requesting a complete feature with many components ("build me a full auth system with OAuth, JWT, password reset, 2FA, and rate limiting") without breaking it into steps should FAIL. Also look for sessions where the AI makes Write/Edit calls to many files without any intervening discussion, commit, or checkpoint. Healthy sessions proceed step by step, with the developer guiding scope.

### P2. Testing discussed or performed
For sessions involving code changes, was testing addressed at any point? Positive signals: Bash tool calls running test commands (`pytest`, `npm test`, `go test`, `cargo test`, `make test`), the developer asking "how should we test this?", discussion of edge cases, the developer running the code and reporting results. Pure "write and forget" sessions with no mention of testing or verification should FAIL. SKIP for sessions that are purely exploratory, documentation-only, or configuration changes where testing is not applicable.

### P3. Session has a clear objective
Can you identify what the session is trying to accomplish within the first few messages? A clear session has a stated goal, a ticket/issue reference, a bug report, or a coherent problem description. A session that drifts between unrelated topics without intentional scope management should FAIL. Note: scope *evolution* is fine if the developer acknowledges it ("ok, that's done, now let's move on to X"). Undirected drift without acknowledgment is the problem. For team usage, sessions should ideally reference a ticket or task.

### P4. Stays within project scope
AI usage should be related to assigned work. Sessions that appear to be personal projects, side work, or clearly unrelated to the team's codebase should FAIL. SKIP if you cannot determine the project context from the transcript.
