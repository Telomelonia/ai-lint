# AI Usage Policy — Individual Developer

Check each session against these rules. For each rule, return a verdict of PASS, FAIL, or SKIP (if the rule doesn't apply to this session).

## Rules

### 1. Understanding before action
The developer should demonstrate understanding of the problem before asking the AI to write code. Sessions where the first message is "just build it" without context or thought should FAIL.

### 2. Review AI output
The developer should review, question, or modify AI-generated code — not blindly accept everything. Look for signs the developer read and engaged with the output (asking follow-up questions, requesting changes, pointing out issues).

### 3. No credential exposure
No API keys, passwords, tokens, or other secrets should appear in the session transcript. Any secret exposure is an automatic FAIL.

### 4. Incremental progress
Work should proceed in reasonable steps rather than asking the AI to build an entire complex system in one shot. Single massive "build everything" prompts should FAIL.

### 5. Testing mentioned
For code changes, testing should be discussed or performed at some point — running tests, asking about edge cases, or verifying behavior. Pure "write and forget" sessions should FAIL.
