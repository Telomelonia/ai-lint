# AI Usage Policy — Team / Corporate

Check each session against these rules. For each rule, return a verdict of PASS, FAIL, or SKIP (if the rule doesn't apply to this session).

## Rules

### 1. No credential exposure
No API keys, passwords, tokens, database connection strings, or other secrets should appear in the session transcript. Any secret exposure is an automatic FAIL.

### 2. Stays within project scope
AI usage should be related to assigned work. Sessions that appear to be personal projects, side work, or unrelated to the team's codebase should FAIL.

### 3. Code review readiness
AI-generated code should not be merged without human review. Look for signs the developer reviewed diffs, ran tests, or made modifications rather than blindly committing AI output.

### 4. No sensitive data in prompts
Customer data, PII, internal architecture details beyond what's in the codebase, or proprietary business logic should not be pasted into prompts. Sharing production database contents or customer records is an automatic FAIL.

### 5. Follows coding standards
The developer should instruct the AI to follow team coding standards (via CLAUDE.md or explicit instructions). Sessions where the AI generates code that clearly violates team conventions without correction should FAIL.

### 6. Reasonable session scope
Individual sessions should have a clear, bounded scope. Marathon sessions attempting to build entire features without breaks or commits suggest poor development practices.
